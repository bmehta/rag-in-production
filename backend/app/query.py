"""
Query engine: hybrid search, rank fusion, and LLM-based answer generation.

Handles:
- Parallel BM25 + vector search in OpenSearch
- Reciprocal Rank Fusion (RRF) for combining results
- Claude API integration for answer generation
- Source attribution
"""

import os
from typing import Tuple, List
from collections import defaultdict

import structlog
from sentence_transformers import SentenceTransformer
from opensearchpy import OpenSearch
from openai import OpenAI

logger = structlog.get_logger(__name__)

# Constants
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "opensearch")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", "9200"))
OPENSEARCH_INDEX = "rag-chunks"
CLAUDE_MODEL = "gpt-4"

# Rank fusion weights (60% semantic / 40% lexical for compliance)
VECTOR_WEIGHT = 0.6
BM25_WEIGHT = 0.4


class QueryEngine:
    """Manages query execution, retrieval, and answer generation."""

    def __init__(self):
        """Initialize the query engine."""
        logger.info("Initializing QueryEngine")

        # Load embedding model
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("Embedding model loaded", model=EMBEDDING_MODEL)

        # Initialize OpenSearch client
        self.opensearch_client = OpenSearch(
            hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
            http_auth=("admin", "admin"),
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
        )

        self.openai_client = None

        logger.info("QueryEngine initialized successfully")

    def _get_openai_client(self) -> OpenAI:
        """Create the OpenAI client on first use when an API key is configured."""
        if self.openai_client is not None:
            return self.openai_client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.openai_client = OpenAI(api_key=api_key)
        return self.openai_client

    async def retrieve(self, query: str, top_k: int = 10) -> List[dict]:
        """
        Run hybrid retrieval only (no LLM generation).

        Args:
            query: User query string
            top_k: Number of top chunks to return

        Returns:
            Ranked chunks with chunk_id, page_number, text, relevance_score, etc.
        """
        logger.info("Starting retrieval", query=query, top_k=top_k)
        results = await self._hybrid_search(query, top_k)
        logger.info("Retrieval complete", results_count=len(results))
        return results

    async def query_and_generate(
        self, query: str, top_k: int = 5
    ) -> Tuple[str, List[dict]]:
        """
        Execute hybrid search and generate an answer.

        Args:
            query: User query string
            top_k: Number of top results to return

        Returns:
            Tuple of (generated_answer, source_chunks)
        """
        try:
            logger.info("Starting query and generation", query=query, top_k=top_k)

            # Perform hybrid search
            search_results = await self._hybrid_search(query, top_k)
            logger.info(
                "Hybrid search complete",
                results_count=len(search_results),
            )

            # Generate answer using Claude
            answer = await self._generate_answer(query, search_results)
            logger.info("Answer generated successfully")

            return answer, search_results

        except Exception as e:
            logger.error("Error in query_and_generate", error=str(e), query=query)
            raise

    async def _hybrid_search(self, query: str, top_k: int) -> List[dict]:
        """
        Perform hybrid search combining BM25 and vector search with rank fusion.

        Args:
            query: User query
            top_k: Number of top results

        Returns:
            List of search results ranked by fusion score
        """
        try:
            # Generate embedding for query
            query_embedding = self.embedding_model.encode([query])[0]
            if hasattr(query_embedding, "tolist"):
                query_embedding = query_embedding.tolist()

            # Execute BM25 search
            bm25_results = await self._bm25_search(query, top_k * 2)
            logger.info("BM25 search complete", results=len(bm25_results))

            # Execute vector search
            vector_results = await self._vector_search(query_embedding, top_k * 2)
            logger.info("Vector search complete", results=len(vector_results))

            # Apply rank fusion
            fused_results = self._reciprocal_rank_fusion(
                bm25_results, vector_results, top_k
            )

            return fused_results

        except Exception as e:
            logger.error("Error in hybrid search", error=str(e), query=query)
            raise

    async def _bm25_search(self, query: str, top_k: int) -> List[dict]:
        """
        Execute BM25 keyword search.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of search results with scores
        """
        search_body = {
            "query": {"multi_match": {"query": query, "fields": ["text"]}},
            "size": top_k,
            "_source": [
                "chunk_id",
                "document_id",
                "document_name",
                "page_number",
                "text",
                "source",
            ],
        }

        response = self.opensearch_client.search(
            index=OPENSEARCH_INDEX, body=search_body
        )

        results = []
        for hit in response["hits"]["hits"]:
            results.append(
                {
                    "chunk_id": hit["_source"]["chunk_id"],
                    "document_id": hit["_source"]["document_id"],
                    "document_name": hit["_source"]["document_name"],
                    "page_number": hit["_source"]["page_number"],
                    "text": hit["_source"]["text"],
                    "source": hit["_source"]["source"],
                    "bm25_score": hit["_score"],
                    "vector_score": None,
                }
            )

        return results

    async def _vector_search(self, query_embedding: list, top_k: int) -> List[dict]:
        """
        Execute semantic vector search using embeddings.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results

        Returns:
            List of search results with scores
        """
        search_body = {
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": top_k,
                    }
                }
            },
            "size": top_k,
            "_source": [
                "chunk_id",
                "document_id",
                "document_name",
                "page_number",
                "text",
                "source",
            ],
        }

        response = self.opensearch_client.search(
            index=OPENSEARCH_INDEX, body=search_body
        )

        results = []
        for hit in response["hits"]["hits"]:
            results.append(
                {
                    "chunk_id": hit["_source"]["chunk_id"],
                    "document_id": hit["_source"]["document_id"],
                    "document_name": hit["_source"]["document_name"],
                    "page_number": hit["_source"]["page_number"],
                    "text": hit["_source"]["text"],
                    "source": hit["_source"]["source"],
                    "bm25_score": None,
                    "vector_score": hit["_score"],
                }
            )

        return results

    def _reciprocal_rank_fusion(
        self, bm25_results: list, vector_results: list, top_k: int
    ) -> List[dict]:
        """
        Combine BM25 and vector results using Reciprocal Rank Fusion.

        RRF formula: score = sum(1 / (rank + 1)) for each result

        Args:
            bm25_results: Results from BM25 search
            vector_results: Results from vector search
            top_k: Number of top results to return

        Returns:
            Fused and re-ranked results
        """
        # Build rank maps
        bm25_ranks = {result["chunk_id"]: i for i, result in enumerate(bm25_results)}
        vector_ranks = {
            result["chunk_id"]: i for i, result in enumerate(vector_results)
        }

        # Calculate RRF scores
        rrf_scores = defaultdict(float)
        chunk_metadata = {}

        for chunk_id, rank in bm25_ranks.items():
            rrf_scores[chunk_id] += BM25_WEIGHT / (rank + 1)
            # Store metadata from BM25 result
            chunk_metadata[chunk_id] = next(
                (r for r in bm25_results if r["chunk_id"] == chunk_id), {}
            )

        for chunk_id, rank in vector_ranks.items():
            rrf_scores[chunk_id] += VECTOR_WEIGHT / (rank + 1)
            # Update metadata from vector result if not already present
            if chunk_id not in chunk_metadata:
                chunk_metadata[chunk_id] = next(
                    (r for r in vector_results if r["chunk_id"] == chunk_id), {}
                )

        # Sort by RRF score
        sorted_results = sorted(
            rrf_scores.items(), key=lambda x: x[1], reverse=True
        )

        # Format results
        fused_results = []
        for chunk_id, fusion_score in sorted_results[:top_k]:
            metadata = chunk_metadata.get(chunk_id, {})
            fused_results.append(
                {
                    "chunk_id": metadata.get("chunk_id", chunk_id),
                    "document_id": metadata.get("document_id"),
                    "document_name": metadata.get("document_name"),
                    "page_number": metadata.get("page_number"),
                    "text": metadata.get("text"),
                    "source": metadata.get("source"),
                    "relevance_score": float(fusion_score),
                    "bm25_score": metadata.get("bm25_score"),
                    "vector_score": metadata.get("vector_score"),
                }
            )

        logger.info(
            "Rank fusion complete",
            total_unique_chunks=len(rrf_scores),
            top_k_selected=len(fused_results),
        )

        return fused_results

    async def _generate_answer(self, query: str, search_results: List[dict]) -> str:
        """
        Generate an answer using Claude API with retrieved context.

        Args:
            query: Original user query
            search_results: Retrieved chunks from search

        Returns:
            Generated answer with source attribution
        """
        # Build context from search results
        context = "\n\n".join(
            [
                f"[Source: {result['document_name']}, Page {result['page_number']}, "
                f"Relevance: {result['relevance_score']:.2%}]\n{result['text']}"
                for result in search_results
            ]
        )

        # Construct prompt
        system_prompt = """You are an expert compliance analyst specializing in NIST security standards.
Your task is to answer questions about NIST compliance requirements based on provided documents.

Guidelines:
1. Base your answer only on the provided context
2. If the context doesn't contain sufficient information, say so clearly
3. Cite specific sections, page numbers, and requirement IDs when available
4. For complex requirements, break them down into clear, actionable components
5. If multiple requirements are relevant, explain how they interact"""

        user_prompt = f"""Based on the following context from NIST compliance documents, please answer this question:

Question: {query}

Context:
{context}

Please provide a comprehensive answer grounded in the provided compliance documentation."""

        try:
            response = self._get_openai_client().chat.completions.create(
                model=CLAUDE_MODEL,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
            )

            answer = response.choices[0].message.content

            logger.info(
                "Answer generated",
                query=query,
                output_tokens=response.usage.completion_tokens,
            )

            return answer

        except Exception as e:
            logger.error("Error generating answer", error=str(e), query=query)
            raise
