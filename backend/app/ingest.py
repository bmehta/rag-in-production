"""
PDF ingestion pipeline: parsing, chunking, embedding, and indexing.

Handles:
- PDF text extraction
- Fixed-size chunking (768 tokens, 20% overlap)
- Embedding generation using BAAI/bge
- Indexing into OpenSearch with metadata
"""

import os
import io
import hashlib
from datetime import datetime
from typing import Tuple

import pdfplumber
import structlog
from sentence_transformers import SentenceTransformer
from opensearchpy import OpenSearch, AWSV4SignerAuth, NotFoundError

logger = structlog.get_logger(__name__)

# Constants
CHUNK_SIZE_TOKENS = 768
OVERLAP_RATIO = 0.2  # 20% overlap
CHUNK_OVERLAP_TOKENS = int(CHUNK_SIZE_TOKENS * OVERLAP_RATIO)
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSION = 384  # bge-small output dimension
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "opensearch")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", "9200"))
OPENSEARCH_INDEX = "rag-chunks"


class PDFIngestionPipeline:
    """Manages the complete PDF ingestion workflow."""

    def __init__(self):
        """Initialize the ingestion pipeline with embeddings model and OpenSearch client."""
        logger.info("Initializing PDFIngestionPipeline")

        # Load embedding model
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("Embedding model loaded", model=EMBEDDING_MODEL)

        # Initialize OpenSearch client
        self.opensearch_client = OpenSearch(
            hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
            http_auth=("admin", "admin"),  # Default Docker credentials
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
        )

        # Ensure index exists
        self._ensure_index_exists()
        logger.info("OpenSearch client initialized")

    def _ensure_index_exists(self):
        """Create the OpenSearch index if it doesn't exist."""
        index_body = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index": {
                    "max_result_window": 10000,
                },
            },
            "mappings": {
                "properties": {
                    # BM25 text search
                    "text": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    # Dense vector for semantic search
                    "embedding": {
                        "type": "dense_vector",
                        "dimension": EMBEDDING_DIMENSION,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "parameters": {"ef_construction": 256, "m": 16},
                        },
                    },
                    # Metadata fields
                    "chunk_id": {"type": "keyword"},
                    "document_id": {"type": "keyword"},
                    "document_name": {"type": "keyword"},
                    "page_number": {"type": "integer"},
                    "section": {"type": "text"},
                    "chunk_index": {"type": "integer"},
                    "created_at": {"type": "date"},
                    "source": {"type": "keyword"},
                }
            },
        }

        if not self.opensearch_client.indices.exists(index=OPENSEARCH_INDEX):
            self.opensearch_client.indices.create(
                index=OPENSEARCH_INDEX, body=index_body
            )
            logger.info("Created OpenSearch index", index=OPENSEARCH_INDEX)
        else:
            logger.info("OpenSearch index already exists", index=OPENSEARCH_INDEX)

    async def ingest(self, filename: str, content: bytes) -> Tuple[str, int]:
        """
        Ingest a PDF document: extract, chunk, embed, and index.

        Args:
            filename: Name of the PDF file
            content: Binary content of the PDF

        Returns:
            Tuple of (document_id, chunks_created)
        """
        try:
            logger.info("Starting ingestion", filename=filename)

            # Generate document ID
            document_id = self._generate_document_id(filename)

            # Extract text from PDF
            pdf_text_by_page = await self._extract_pdf_text(content)
            logger.info(
                "PDF text extracted",
                document_id=document_id,
                pages=len(pdf_text_by_page),
            )

            # Chunk the text
            chunks = await self._chunk_text(pdf_text_by_page, filename)
            logger.info(
                "Text chunked",
                document_id=document_id,
                chunks_count=len(chunks),
            )

            # Generate embeddings
            embeddings = await self._embed_chunks(chunks)
            logger.info(
                "Embeddings generated",
                document_id=document_id,
                embeddings_count=len(embeddings),
            )

            # Index in OpenSearch
            chunks_indexed = await self._index_chunks(
                document_id=document_id,
                filename=filename,
                chunks=chunks,
                embeddings=embeddings,
            )

            logger.info(
                "Ingestion complete",
                document_id=document_id,
                chunks_indexed=chunks_indexed,
            )

            return document_id, chunks_indexed

        except Exception as e:
            logger.error("Error during ingestion", filename=filename, error=str(e))
            raise

    async def _extract_pdf_text(self, content: bytes) -> dict:
        """
        Extract text from PDF by page.

        Returns:
            Dictionary mapping page numbers to page text
        """
        pdf_file = io.BytesIO(content)
        text_by_page = {}

        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    text_by_page[page_num] = text

        return text_by_page

    async def _chunk_text(self, text_by_page: dict, filename: str) -> list:
        """
        Chunk text using fixed-size chunks with overlap.

        Args:
            text_by_page: Dictionary of page number -> text
            filename: Source filename for metadata

        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []
        chunk_index = 0

        # Simple token approximation: split by whitespace
        for page_num, page_text in sorted(text_by_page.items()):
            tokens = page_text.split()

            # Sliding window chunking
            for start_idx in range(
                0, len(tokens), CHUNK_SIZE_TOKENS - CHUNK_OVERLAP_TOKENS
            ):
                end_idx = min(start_idx + CHUNK_SIZE_TOKENS, len(tokens))
                chunk_tokens = tokens[start_idx:end_idx]

                if len(chunk_tokens) > 10:  # Skip very small chunks
                    chunk_text = " ".join(chunk_tokens)
                    chunks.append(
                        {
                            "chunk_index": chunk_index,
                            "text": chunk_text,
                            "page_number": page_num,
                            "source": filename,
                            "token_count": len(chunk_tokens),
                        }
                    )
                    chunk_index += 1

        logger.info(
            "Text chunking complete",
            total_chunks=len(chunks),
            avg_chunk_size=sum(c["token_count"] for c in chunks) / len(chunks)
            if chunks
            else 0,
        )

        return chunks

    async def _embed_chunks(self, chunks: list) -> list:
        """
        Generate embeddings for chunks using BAAI/bge model.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            List of embeddings (each is a list of floats)
        """
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=False)

        # Convert to list format for JSON serialization
        return [emb.tolist() if hasattr(emb, "tolist") else emb for emb in embeddings]

    async def _index_chunks(
        self, document_id: str, filename: str, chunks: list, embeddings: list
    ) -> int:
        """
        Index chunks in OpenSearch.

        Args:
            document_id: Unique document identifier
            filename: Source filename
            chunks: List of chunk dictionaries
            embeddings: List of embedding vectors

        Returns:
            Number of chunks successfully indexed
        """
        indexed_count = 0

        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = f"{document_id}_{chunk['chunk_index']}"

            doc_body = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "document_name": filename,
                "page_number": chunk["page_number"],
                "text": chunk["text"],
                "embedding": embedding,
                "source": chunk["source"],
                "chunk_index": chunk["chunk_index"],
                "created_at": datetime.utcnow().isoformat(),
            }

            try:
                self.opensearch_client.index(
                    index=OPENSEARCH_INDEX, id=chunk_id, body=doc_body
                )
                indexed_count += 1
            except Exception as e:
                logger.error(
                    "Error indexing chunk",
                    chunk_id=chunk_id,
                    error=str(e),
                )

        # Refresh index to make documents searchable
        self.opensearch_client.indices.refresh(index=OPENSEARCH_INDEX)

        logger.info(
            "Chunks indexed successfully",
            total=len(chunks),
            successful=indexed_count,
        )

        return indexed_count

    async def list_documents(self) -> list:
        """
        List all documents in the index.

        Returns:
            List of document metadata
        """
        query = {
            "aggs": {
                "documents": {
                    "terms": {
                        "field": "document_id",
                        "size": 100,
                    }
                }
            },
            "size": 0,
        }

        response = self.opensearch_client.search(
            index=OPENSEARCH_INDEX, body=query
        )

        documents = []
        for bucket in response["aggregations"]["documents"]["buckets"]:
            documents.append(
                {
                    "document_id": bucket["key"],
                    "chunk_count": bucket["doc_count"],
                }
            )

        return documents

    @staticmethod
    def _generate_document_id(filename: str) -> str:
        """Generate a unique document ID from filename and timestamp."""
        timestamp = datetime.utcnow().isoformat()
        hash_input = f"{filename}_{timestamp}".encode()
        hash_hex = hashlib.md5(hash_input).hexdigest()[:8]
        return f"doc_{hash_hex}"
