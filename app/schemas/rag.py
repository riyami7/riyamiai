"""RAG-related schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class RagIngestResult(BaseModel):
    """Schema for a single file ingestion result."""

    filename: str = Field(..., description="Name of the file")
    success: bool = Field(..., description="Whether ingestion succeeded")
    chunks_created: int = Field(default=0, description="Number of chunks created")
    error: str | None = Field(default=None, description="Error message if failed")


class RagIngestResponse(BaseModel):
    """Schema for RAG ingestion response."""

    files_processed: int = Field(..., description="Total number of files processed")
    files_succeeded: int = Field(..., description="Number of files successfully ingested")
    total_chunks: int = Field(..., description="Total chunks created across all files")
    results: list[RagIngestResult] = Field(..., description="Per-file results")

    model_config = {
        "json_schema_extra": {
            "example": {
                "files_processed": 2,
                "files_succeeded": 2,
                "total_chunks": 45,
                "results": [
                    {"filename": "document.pdf", "success": True, "chunks_created": 30, "error": None},
                    {"filename": "notes.md", "success": True, "chunks_created": 15, "error": None},
                ],
            }
        }
    }


class RagSearchRequest(BaseModel):
    """Schema for RAG search request."""

    query: str = Field(
        ...,
        min_length=1,
        description="Search query text",
        example="How do I install Ollama?",
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of results to return (uses server default if omitted)",
    )


class RagSearchResult(BaseModel):
    """Schema for a single RAG search result."""

    content: str = Field(..., description="The matched chunk content")
    source: str = Field(..., description="Source filename")
    chunk_index: int = Field(..., description="Index of the chunk within the source")
    score: float = Field(..., description="Similarity score (higher is more similar)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "content": "To install Ollama, run: curl -fsSL https://ollama.ai/install.sh | sh",
                "source": "ollama-cheatsheet.md",
                "chunk_index": 2,
                "score": 0.89,
            }
        }
    }


class RagSearchResponse(BaseModel):
    """Schema for RAG search response."""

    query: str = Field(..., description="The original search query")
    results: list[RagSearchResult] = Field(..., description="Matching document chunks")
    total_results: int = Field(..., description="Number of results returned")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "How do I install Ollama?",
                "results": [
                    {
                        "content": "To install Ollama, run: curl -fsSL https://ollama.ai/install.sh | sh",
                        "source": "ollama-cheatsheet.md",
                        "chunk_index": 2,
                        "score": 0.89,
                    }
                ],
                "total_results": 1,
            }
        }
    }


# ──────────────────────────────────────────────
# Background Job Schemas
# ──────────────────────────────────────────────


class RagIngestJobResponse(BaseModel):
    """Schema for immediate response when starting a background ingest job."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Initial job status (pending)")
    message: str = Field(..., description="Human-readable message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "message": "Ingestion job started. Poll GET /api/rag/ingest/{job_id} for status.",
            }
        }
    }


class RagIngestJobStatus(BaseModel):
    """Schema for polling the status of a background ingest job."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(
        ...,
        description="Job status: pending, processing, completed, or failed",
    )
    files_total: int | None = Field(
        default=None, description="Total number of files to process"
    )
    files_processed: int = Field(
        default=0, description="Number of files processed so far"
    )
    current_file: str | None = Field(
        default=None, description="Name of the file currently being processed"
    )
    started_at: datetime | None = Field(
        default=None, description="Timestamp when processing started"
    )
    completed_at: datetime | None = Field(
        default=None, description="Timestamp when processing completed"
    )
    result: RagIngestResponse | None = Field(
        default=None, description="Full ingestion result (only when status=completed)"
    )
    error: str | None = Field(
        default=None, description="Error message (only when status=failed)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "files_total": 3,
                "files_processed": 1,
                "current_file": "document.pdf",
                "started_at": "2026-02-17T10:00:00Z",
                "completed_at": None,
                "result": None,
                "error": None,
            }
        }
    }
