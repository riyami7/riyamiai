"""RAG service for document ingestion and retrieval."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from PyPDF2 import PdfReader
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.exceptions import ServiceUnavailableError
from app.repositories.rag import RagRepository
from app.utils.notifications import send_telegram_notification
from app.schemas.rag import (
    RagIngestJobStatus,
    RagIngestResponse,
    RagIngestResult,
    RagSearchResponse,
    RagSearchResult,
)

# Supported file extensions for ingestion
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}

# In-memory job store for tracking background ingestion jobs
_ingest_jobs: dict[str, RagIngestJobStatus] = {}


class RagService:
    """Service class for RAG document ingestion and retrieval."""

    def __init__(self, db: Session):
        self.db = db
        self._repo = RagRepository(db)
        self._settings = get_settings()

    # ──────────────────────────────────────────────
    # File Parsing Helpers
    # ──────────────────────────────────────────────

    def _parse_txt_md(self, file_path: Path) -> str:
        """Parse a text or markdown file."""
        return file_path.read_text(encoding="utf-8")

    def _parse_pdf(self, file_path: Path) -> str:
        """Parse a PDF file, extracting text from all pages."""
        reader = PdfReader(str(file_path))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n".join(text_parts)

    def _parse_file(self, file_path: Path) -> str | None:
        """Parse a file based on its extension.

        Returns:
            The file's text content, or None if parsing failed.
        """
        suffix = file_path.suffix.lower()

        try:
            if suffix in {".txt", ".md"}:
                return self._parse_txt_md(file_path)
            elif suffix == ".pdf":
                return self._parse_pdf(file_path)
            else:
                return None
        except Exception:
            return None

    # ──────────────────────────────────────────────
    # Text Chunking
    # ──────────────────────────────────────────────

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks.

        Args:
            text: The text to chunk.

        Returns:
            List of text chunks.
        """
        if not text:
            return []

        chunk_size = self._settings.rag_chunk_size
        overlap = self._settings.rag_chunk_overlap

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at a sentence or word boundary
            if end < len(text):
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

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for a text chunk using Ollama.

        Args:
            text: The text to embed.

        Returns:
            The embedding vector.

        Raises:
            ServiceUnavailableError: If Ollama is unreachable or model unavailable.
        """
        base_url = self._settings.ollama_base_url
        model = self._settings.rag_embedding_model

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/api/embed",
                    json={"model": model, "input": text},
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
                    raise ServiceUnavailableError(
                        detail="Unexpected embedding response format",
                        error_code="EMBEDDING_FORMAT_ERROR",
                    )

        except httpx.ConnectError:
            raise ServiceUnavailableError(
                detail=f"Cannot connect to Ollama at {base_url}",
                error_code="OLLAMA_UNAVAILABLE",
            )
        except httpx.HTTPStatusError as e:
            raise ServiceUnavailableError(
                detail=f"Ollama embedding failed: {e.response.text}",
                error_code="EMBEDDING_FAILED",
            )

    # ──────────────────────────────────────────────
    # Public Methods
    # ──────────────────────────────────────────────

    async def ingest(self) -> RagIngestResponse:
        """Ingest all supported documents from the data directory.

        Scans the configured data directory, parses each supported file,
        chunks the text, generates embeddings via Ollama, and stores in pgvector.

        Returns:
            Summary of ingestion results.

        Raises:
            ServiceUnavailableError: If Ollama is unreachable.
        """
        # Setup database table if not exists
        self._repo.setup_table()

        data_dir = Path(self._settings.rag_data_dir)
        if not data_dir.exists():
            return RagIngestResponse(
                files_processed=0,
                files_succeeded=0,
                total_chunks=0,
                results=[],
            )

        # Find supported files
        files = [
            f for f in data_dir.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        results: list[RagIngestResult] = []
        total_chunks = 0

        for file_path in files:
            result = await self._ingest_file(file_path)
            results.append(result)
            if result.success:
                total_chunks += result.chunks_created

        files_succeeded = sum(1 for r in results if r.success)

        return RagIngestResponse(
            files_processed=len(files),
            files_succeeded=files_succeeded,
            total_chunks=total_chunks,
            results=results,
        )

    async def _ingest_file(self, file_path: Path) -> RagIngestResult:
        """Ingest a single file into the vector database.

        Args:
            file_path: Path to the file to ingest.

        Returns:
            Result of the ingestion attempt.
        """
        filename = file_path.name

        # Parse file
        text = self._parse_file(file_path)
        if not text:
            return RagIngestResult(
                filename=filename,
                success=False,
                chunks_created=0,
                error="Failed to parse file or no text extracted",
            )

        # Chunk text
        chunks = self._chunk_text(text)
        if not chunks:
            return RagIngestResult(
                filename=filename,
                success=False,
                chunks_created=0,
                error="No chunks generated from file",
            )

        # Clear existing chunks for this file (for re-ingestion)
        self._repo.clear_source(filename)

        # Generate embeddings
        try:
            embedded_chunks: list[tuple[int, str, list[float]]] = []
            for i, chunk in enumerate(chunks):
                embedding = await self._get_embedding(chunk)
                embedded_chunks.append((i, chunk, embedding))
        except ServiceUnavailableError as e:
            return RagIngestResult(
                filename=filename,
                success=False,
                chunks_created=0,
                error=str(e.detail),
            )

        # Insert into database
        self._repo.insert_chunks(filename, embedded_chunks)

        return RagIngestResult(
            filename=filename,
            success=True,
            chunks_created=len(embedded_chunks),
            error=None,
        )

    async def search(
        self, query: str, top_k: int | None = None
    ) -> RagSearchResponse:
        """Search for documents similar to the query.

        Args:
            query: Search query text.
            top_k: Number of results to return (uses config default if None).

        Returns:
            Search results with scores.

        Raises:
            ServiceUnavailableError: If Ollama is unreachable.
        """
        # Get query embedding
        query_embedding = await self._get_embedding(query)

        # Search for similar chunks
        raw_results = self._repo.search(query_embedding, top_k)

        # Convert to response schema
        results = [
            RagSearchResult(
                content=r["content"],
                source=r["source"],
                chunk_index=r["chunk_index"],
                score=r["score"],
            )
            for r in raw_results
        ]

        return RagSearchResponse(
            query=query,
            results=results,
            total_results=len(results),
        )

    async def get_context(
        self, query: str, top_k: int | None = None
    ) -> str:
        """Get RAG context string for a query to inject into LLM prompt.

        Args:
            query: The user's message to find context for.
            top_k: Number of chunks to retrieve (uses config default if None).

        Returns:
            Formatted context string, or empty string if no relevant context.

        Raises:
            ServiceUnavailableError: If Ollama is unreachable.
        """
        search_response = await self.search(query, top_k)

        if not search_response.results:
            return ""

        # Format context with source attribution
        context_parts = ["Context from knowledge base:"]
        for i, result in enumerate(search_response.results, 1):
            context_parts.append(
                f"\n[{i}] (from {result.source}):\n{result.content}"
            )

        return "\n".join(context_parts)

    # ──────────────────────────────────────────────
    # Background Job Methods
    # ──────────────────────────────────────────────

    @staticmethod
    def start_ingest_job() -> str:
        """Create a new ingest job and return its ID.

        Returns:
            The job_id for tracking the background job.
        """
        job_id = str(uuid.uuid4())
        _ingest_jobs[job_id] = RagIngestJobStatus(
            job_id=job_id,
            status="pending",
            files_total=None,
            files_processed=0,
            current_file=None,
            started_at=None,
            completed_at=None,
            result=None,
            error=None,
        )
        return job_id

    @staticmethod
    def get_job_status(job_id: str) -> RagIngestJobStatus | None:
        """Get the current status of an ingest job.

        Args:
            job_id: The job ID to look up.

        Returns:
            The job status, or None if not found.
        """
        return _ingest_jobs.get(job_id)

    @staticmethod
    async def ingest_background(job_id: str) -> None:
        """Run ingestion in the background, updating job status as it progresses.

        This method creates its own database session since it runs outside
        the request lifecycle.

        Args:
            job_id: The job ID to update as processing progresses.
        """
        job = _ingest_jobs.get(job_id)
        if not job:
            return

        # Create a new database session for this background task
        db = SessionLocal()
        try:
            service = RagService(db)

            # Update status to processing
            job.status = "processing"
            job.started_at = datetime.now(timezone.utc)

            # Setup database table if not exists
            service._repo.setup_table()

            data_dir = Path(service._settings.rag_data_dir)
            if not data_dir.exists():
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.result = RagIngestResponse(
                    files_processed=0,
                    files_succeeded=0,
                    total_chunks=0,
                    results=[],
                )
                return

            # Find supported files
            files = [
                f
                for f in data_dir.iterdir()
                if f.suffix.lower() in SUPPORTED_EXTENSIONS
            ]

            job.files_total = len(files)

            results: list[RagIngestResult] = []
            total_chunks = 0

            for file_path in files:
                job.current_file = file_path.name

                result = await service._ingest_file(file_path)
                results.append(result)

                if result.success:
                    total_chunks += result.chunks_created

                job.files_processed += 1

            # Mark as completed
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.current_file = None
            files_succeeded = sum(1 for r in results if r.success)
            job.result = RagIngestResponse(
                files_processed=len(files),
                files_succeeded=files_succeeded,
                total_chunks=total_chunks,
                results=results,
            )

            # Send success notification
            await send_telegram_notification(
                f"<b>RAG Ingestion Complete</b>\n\n"
                f"Files: {files_succeeded}/{len(files)} succeeded\n"
                f"Chunks created: {total_chunks}"
            )

        except Exception as e:
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            job.error = str(e)

            # Send failure notification
            await send_telegram_notification(
                f"<b>RAG Ingestion Failed</b>\n\n"
                f"Error: {str(e)}"
            )
        finally:
            db.close()
