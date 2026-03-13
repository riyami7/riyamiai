"""RAG routes for document ingestion and search."""

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.exceptions import NotFoundError
from app.schemas.rag import (
    RagIngestJobResponse,
    RagIngestJobStatus,
    RagSearchRequest,
    RagSearchResponse,
)
from app.schemas.error import ErrorResponse
from app.services.rag import RagService
from app.models.user import User
from app.dependencies.auth import get_current_user, require_role

router = APIRouter(
    prefix="/api/rag",
    tags=["RAG"],
)


def get_rag_service(db: Session = Depends(get_db)) -> RagService:
    """Dependency to get RagService instance."""
    return RagService(db)


@router.post(
    "/ingest",
    response_model=RagIngestJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
    },
)
async def ingest_documents(
    background_tasks: BackgroundTasks,
    _: User = Depends(require_role("admin")),
) -> RagIngestJobResponse:
    """Start background ingestion of documents into the vector store (admin only).

    This endpoint immediately returns a job_id. The actual ingestion runs
    in the background. Poll GET /api/rag/ingest/{job_id} to check progress.

    Scans the configured data directory (app/data/ by default), parses
    supported files (.txt, .md, .pdf), chunks the text, generates embeddings
    via Ollama, and stores them in PostgreSQL with pgvector.
    """
    job_id = RagService.start_ingest_job()
    background_tasks.add_task(RagService.ingest_background, job_id)

    return RagIngestJobResponse(
        job_id=job_id,
        status="pending",
        message=f"Ingestion job started. Poll GET /api/rag/ingest/{job_id} for status.",
    )


@router.get(
    "/ingest/{job_id}",
    response_model=RagIngestJobStatus,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
async def get_ingest_status(
    job_id: str,
    _: User = Depends(require_role("admin")),
) -> RagIngestJobStatus:
    """Get the status of a background ingestion job (admin only).

    Returns the current progress including files processed, current file,
    and the full result when completed.
    """
    job_status = RagService.get_job_status(job_id)
    if job_status is None:
        raise NotFoundError(
            detail="Ingestion job not found",
            error_code="JOB_NOT_FOUND",
            context={"job_id": job_id},
        )
    return job_status


@router.post(
    "/search",
    response_model=RagSearchResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        503: {"model": ErrorResponse, "description": "Ollama service unavailable"},
    },
)
async def search_documents(
    request: RagSearchRequest,
    service: RagService = Depends(get_rag_service),
    _: User = Depends(get_current_user),
) -> RagSearchResponse:
    """Search the vector store for documents similar to the query (auth required).

    Returns the most relevant document chunks with similarity scores.
    The query is embedded using the same model used for document ingestion.
    """
    return await service.search(request.query, request.top_k)
