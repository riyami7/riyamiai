"""RAG repository for pgvector operations."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings


class RagRepository:
    """Repository class for RAG document chunk operations using pgvector."""

    def __init__(self, db: Session):
        self.db = db
        self._settings = get_settings()

    def setup_table(self) -> None:
        """Enable pgvector extension and create document_chunks table if not exists."""
        dimension = self._settings.rag_embedding_dimension

        # Enable pgvector extension
        self.db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Create document_chunks table
        self.db.execute(
            text(f"""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    source TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector({dimension}),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
        )

        # Create index on source for faster lookups
        self.db.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_document_chunks_source
                ON document_chunks (source)
            """)
        )

        self.db.commit()

    def clear_source(self, source: str) -> int:
        """Remove existing chunks for a source file.

        Args:
            source: Source filename.

        Returns:
            Number of rows deleted.
        """
        result = self.db.execute(
            text("DELETE FROM document_chunks WHERE source = :source"),
            {"source": source},
        )
        self.db.commit()
        return result.rowcount

    def insert_chunks(
        self, source: str, chunks: list[tuple[int, str, list[float]]]
    ) -> int:
        """Insert chunks with their embeddings into the database.

        Args:
            source: Source filename.
            chunks: List of (chunk_index, content, embedding) tuples.

        Returns:
            Number of chunks inserted.
        """
        for chunk_index, content, embedding in chunks:
            # Convert embedding list to pgvector format string
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            self.db.execute(
                text("""
                    INSERT INTO document_chunks (source, chunk_index, content, embedding)
                    VALUES (:source, :chunk_index, :content, :embedding)
                """),
                {
                    "source": source,
                    "chunk_index": chunk_index,
                    "content": content,
                    "embedding": embedding_str,
                },
            )
        self.db.commit()
        return len(chunks)

    def search(
        self, embedding: list[float], top_k: int | None = None
    ) -> list[dict]:
        """Search for similar chunks using cosine similarity.

        Args:
            embedding: Query embedding vector.
            top_k: Number of results to return (uses config default if None).

        Returns:
            List of dicts with content, source, chunk_index, and score.
        """
        if top_k is None:
            top_k = self._settings.rag_search_top_k

        # Convert embedding list to pgvector format string
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"

        # Cosine similarity search using <=> operator
        # pgvector's <=> returns distance, so we compute 1 - distance for similarity
        result = self.db.execute(
            text("""
                SELECT 
                    content,
                    source,
                    chunk_index,
                    1 - (embedding <=> :embedding) as score
                FROM document_chunks
                ORDER BY embedding <=> :embedding
                LIMIT :top_k
            """),
            {"embedding": embedding_str, "top_k": top_k},
        )

        return [
            {
                "content": row.content,
                "source": row.source,
                "chunk_index": row.chunk_index,
                "score": float(row.score),
            }
            for row in result.fetchall()
        ]

    def count(self) -> int:
        """Get total count of document chunks.

        Returns:
            Total number of chunks.
        """
        result = self.db.execute(text("SELECT COUNT(*) FROM document_chunks"))
        return result.scalar() or 0

    def get_sources(self) -> list[str]:
        """Get list of unique source files.

        Returns:
            List of source filenames.
        """
        result = self.db.execute(
            text("SELECT DISTINCT source FROM document_chunks ORDER BY source")
        )
        return [row.source for row in result.fetchall()]
