"""RAG Ingestion PoC - Document to Vector Pipeline.

This script reads documents from app/data/, chunks them, generates embeddings
via Ollama's nomic-embed-text model, and stores vectors in PostgreSQL + pgvector.

Usage:
    python poc/rag_ingest.py

Prerequisites:
    1. PostgreSQL with pgvector running (docker compose up -d)
    2. Ollama running with nomic-embed-text model pulled
    3. pip install pgvector PyPDF2
"""

import os
import sys
from pathlib import Path

import httpx
import psycopg2
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIMENSION = 768  # nomic-embed-text produces 768-dim vectors

# Chunking settings
CHUNK_SIZE = 500  # characters per chunk
CHUNK_OVERLAP = 50  # overlap between chunks

# Data directory (relative to project root)
DATA_DIR = Path(__file__).parent.parent / "app" / "data"

# Supported file extensions
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


# ──────────────────────────────────────────────
# Database Setup
# ──────────────────────────────────────────────


def setup_database(conn) -> None:
    """Enable pgvector extension and create document_chunks table."""
    with conn.cursor() as cur:
        # Enable pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # Create document_chunks table
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                source TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector({EMBEDDING_DIMENSION}),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Create index on source for faster lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_source
            ON document_chunks (source)
        """)

        conn.commit()
        print("[DB] pgvector extension enabled and document_chunks table ready.")


def clear_source(conn, source: str) -> None:
    """Remove existing chunks for a source file (for re-ingestion)."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM document_chunks WHERE source = %s", (source,))
        conn.commit()


def insert_chunks(conn, source: str, chunks: list[tuple[int, str, list[float]]]) -> None:
    """Insert chunks with their embeddings into the database.

    Args:
        conn: Database connection.
        source: Source filename.
        chunks: List of (chunk_index, content, embedding) tuples.
    """
    with conn.cursor() as cur:
        for chunk_index, content, embedding in chunks:
            cur.execute(
                """
                INSERT INTO document_chunks (source, chunk_index, content, embedding)
                VALUES (%s, %s, %s, %s)
                """,
                (source, chunk_index, content, embedding),
            )
        conn.commit()


# ──────────────────────────────────────────────
# File Parsing
# ──────────────────────────────────────────────


def parse_txt_md(file_path: Path) -> str:
    """Parse a text or markdown file."""
    return file_path.read_text(encoding="utf-8")


def parse_pdf(file_path: Path) -> str:
    """Parse a PDF file, extracting text from all pages."""
    reader = PdfReader(str(file_path))
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n".join(text_parts)


def parse_file(file_path: Path) -> str | None:
    """Parse a file based on its extension.

    Returns:
        The file's text content, or None if parsing failed.
    """
    suffix = file_path.suffix.lower()

    try:
        if suffix in {".txt", ".md"}:
            return parse_txt_md(file_path)
        elif suffix == ".pdf":
            return parse_pdf(file_path)
        else:
            return None
    except Exception as e:
        print(f"  [ERROR] Failed to parse {file_path.name}: {e}")
        return None


# ──────────────────────────────────────────────
# Text Chunking
# ──────────────────────────────────────────────


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks.

    Args:
        text: The text to chunk.
        chunk_size: Maximum characters per chunk.
        overlap: Number of overlapping characters between chunks.

    Returns:
        List of text chunks.
    """
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at a sentence or word boundary
        if end < len(text):
            # Look for last sentence break
            for sep in [". ", ".\n", "\n\n", "\n", " "]:
                last_sep = chunk.rfind(sep)
                if last_sep > chunk_size // 2:
                    chunk = chunk[: last_sep + len(sep)]
                    break

        chunks.append(chunk.strip())
        start += len(chunk) - overlap

        # Prevent infinite loop if chunk is very small
        if len(chunk) <= overlap:
            start += overlap

    return [c for c in chunks if c]  # Remove empty chunks


# ──────────────────────────────────────────────
# Embedding Generation
# ──────────────────────────────────────────────


def get_embedding(text: str) -> list[float] | None:
    """Get embedding for a text chunk using Ollama.

    Args:
        text: The text to embed.

    Returns:
        The embedding vector, or None if failed.
    """
    try:
        response = httpx.post(
            f"{OLLAMA_BASE_URL}/api/embed",
            json={"model": EMBEDDING_MODEL, "input": text},
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()

        # Ollama returns embeddings in different formats depending on version
        if "embeddings" in data:
            return data["embeddings"][0]
        elif "embedding" in data:
            return data["embedding"]
        else:
            print(f"  [ERROR] Unexpected embedding response format: {list(data.keys())}")
            return None

    except httpx.ConnectError:
        print(f"  [ERROR] Cannot connect to Ollama at {OLLAMA_BASE_URL}")
        return None
    except Exception as e:
        print(f"  [ERROR] Embedding failed: {e}")
        return None


# ──────────────────────────────────────────────
# Main Ingestion Pipeline
# ──────────────────────────────────────────────


def ingest_file(conn, file_path: Path) -> bool:
    """Ingest a single file into the vector database.

    Args:
        conn: Database connection.
        file_path: Path to the file to ingest.

    Returns:
        True if successful, False otherwise.
    """
    print(f"\n[INGEST] {file_path.name}")

    # Parse file
    text = parse_file(file_path)
    if not text:
        print(f"  [SKIP] No text extracted")
        return False

    print(f"  Extracted {len(text):,} characters")

    # Chunk text
    chunks = chunk_text(text)
    print(f"  Split into {len(chunks)} chunks")

    if not chunks:
        print(f"  [SKIP] No chunks generated")
        return False

    # Clear existing chunks for this file (for re-ingestion)
    clear_source(conn, file_path.name)

    # Generate embeddings and prepare for insertion
    embedded_chunks = []
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        if embedding is None:
            print(f"  [ERROR] Failed to embed chunk {i + 1}/{len(chunks)}")
            return False

        embedded_chunks.append((i, chunk, embedding))

        # Progress indicator
        if (i + 1) % 10 == 0 or (i + 1) == len(chunks):
            print(f"  Embedded {i + 1}/{len(chunks)} chunks...")

    # Insert into database
    insert_chunks(conn, file_path.name, embedded_chunks)
    print(f"  [OK] Inserted {len(embedded_chunks)} chunks into database")

    return True


def main() -> None:
    """Main entry point."""
    print("=" * 60)
    print("  RAG Ingestion PoC")
    print("=" * 60)

    # Validate configuration
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL not set in environment")
        sys.exit(1)

    print(f"\n[CONFIG]")
    print(f"  Database: {DATABASE_URL.split('@')[-1]}")  # Hide credentials
    print(f"  Ollama: {OLLAMA_BASE_URL}")
    print(f"  Embedding model: {EMBEDDING_MODEL}")
    print(f"  Data directory: {DATA_DIR}")
    print(f"  Chunk size: {CHUNK_SIZE} chars, overlap: {CHUNK_OVERLAP} chars")

    # Check data directory
    if not DATA_DIR.exists():
        print(f"\n[ERROR] Data directory not found: {DATA_DIR}")
        sys.exit(1)

    # Find supported files
    files = [f for f in DATA_DIR.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not files:
        print(f"\n[ERROR] No supported files found in {DATA_DIR}")
        print(f"  Supported extensions: {SUPPORTED_EXTENSIONS}")
        sys.exit(1)

    print(f"\n[FILES] Found {len(files)} file(s) to ingest:")
    for f in files:
        print(f"  - {f.name} ({f.stat().st_size / 1024:.1f} KB)")

    # Connect to database
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print(f"\n[DB] Connected to PostgreSQL")
    except Exception as e:
        print(f"\n[ERROR] Failed to connect to database: {e}")
        sys.exit(1)

    # Setup database (create extension and table)
    try:
        setup_database(conn)
    except Exception as e:
        print(f"\n[ERROR] Failed to setup database: {e}")
        conn.close()
        sys.exit(1)

    # Test Ollama connection
    print(f"\n[OLLAMA] Testing connection...")
    test_embedding = get_embedding("test")
    if test_embedding is None:
        print(f"[ERROR] Cannot connect to Ollama or model not available")
        print(f"  Make sure Ollama is running and {EMBEDDING_MODEL} is pulled:")
        print(f"  ollama pull {EMBEDDING_MODEL}")
        conn.close()
        sys.exit(1)
    print(f"  [OK] Embedding model ready (dimension: {len(test_embedding)})")

    # Ingest files
    success_count = 0
    for file_path in files:
        if ingest_file(conn, file_path):
            success_count += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"  COMPLETE: {success_count}/{len(files)} files ingested")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
