"""
FastAPI application for RAG pipeline backend.

Endpoints:
- GET /api/health - Health check
- POST /api/ingest - Ingest and index PDF documents
- POST /api/query - Query documents and generate answers
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import structlog

from app.ingest import PDFIngestionPipeline
from app.query import QueryEngine

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global application state
ingest_pipeline: Optional[PDFIngestionPipeline] = None
query_engine: Optional[QueryEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: startup and shutdown."""
    global ingest_pipeline, query_engine

    # Startup
    logger.info("Starting RAG Pipeline backend")
    try:
        ingest_pipeline = PDFIngestionPipeline()
        query_engine = QueryEngine()
        logger.info("Application initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize application", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Shutting down RAG Pipeline backend")
    # Cleanup resources if needed
    pass


# Initialize FastAPI app
app = FastAPI(
    title="RAG Pipeline API",
    description="Fullstack RAG system with BM25 + vector search",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class HealthResponse(BaseModel):
    status: str
    message: str


class IngestResponse(BaseModel):
    status: str
    document_id: str
    chunks_created: int
    message: str


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


class SourceChunk(BaseModel):
    chunk_id: str
    text: str
    document_id: str
    page_number: int
    relevance_score: float
    source: str


class QueryResponse(BaseModel):
    query: str
    answer: str
    source_chunks: list[SourceChunk]


# API Endpoints


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        message="RAG Pipeline backend is running",
    )


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)):
    """
    Ingest a PDF document.

    Accepts a PDF file, extracts text, chunks it, embeds it,
    and indexes it in OpenSearch.
    """
    if ingest_pipeline is None:
        raise HTTPException(status_code=500, detail="Ingestion pipeline not initialized")

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    try:
        logger.info("Ingesting document", filename=file.filename)

        # Read file content
        content = await file.read()

        # Process document
        document_id, chunks_count = await ingest_pipeline.ingest(
            filename=file.filename,
            content=content,
        )

        logger.info(
            "Document ingested successfully",
            document_id=document_id,
            chunks_count=chunks_count,
        )

        return IngestResponse(
            status="success",
            document_id=document_id,
            chunks_created=chunks_count,
            message=f"Document ingested successfully. Created {chunks_count} chunks.",
        )

    except Exception as e:
        logger.error("Error ingesting document", error=str(e), filename=file.filename)
        raise HTTPException(status_code=500, detail=f"Error ingesting document: {str(e)}")


@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Query documents and generate an answer.

    Performs hybrid search (BM25 + vector), retrieves top chunks,
    and generates an answer using Claude API.
    """
    if query_engine is None:
        raise HTTPException(status_code=500, detail="Query engine not initialized")

    try:
        logger.info("Processing query", query=request.query, top_k=request.top_k)

        # Execute query and generation
        answer, source_chunks = await query_engine.query_and_generate(
            query=request.query,
            top_k=request.top_k,
        )

        logger.info(
            "Query processed successfully",
            query=request.query,
            sources_count=len(source_chunks),
        )

        # Format response
        formatted_chunks = [
            SourceChunk(
                chunk_id=chunk["chunk_id"],
                text=chunk["text"],
                document_id=chunk["document_id"],
                page_number=chunk.get("page_number", 0),
                relevance_score=chunk.get("relevance_score", 0.0),
                source=chunk.get("source", ""),
            )
            for chunk in source_chunks
        ]

        return QueryResponse(
            query=request.query,
            answer=answer,
            source_chunks=formatted_chunks,
        )

    except Exception as e:
        logger.error("Error processing query", error=str(e), query=request.query)
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.get("/api/documents", tags=["admin"])
async def list_documents():
    """
    List all ingested documents (admin endpoint).

    Returns metadata for all documents currently in the index.
    """
    if ingest_pipeline is None:
        raise HTTPException(status_code=500, detail="Ingestion pipeline not initialized")

    try:
        documents = await ingest_pipeline.list_documents()
        return {"documents": documents}

    except Exception as e:
        logger.error("Error listing documents", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
