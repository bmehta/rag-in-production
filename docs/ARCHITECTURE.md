# Architecture Documentation

## Overview

The RAG Pipeline is a fullstack retrieval-augmented generation system designed for querying NIST compliance documents. The architecture combines lexical (BM25) and semantic (vector) search with LLM-based answer generation.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  User Interface (Browser)                    │
│            React/Next.js + Tailwind CSS (Port 3000)         │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│              (Python, Async/Await) (Port 8000)              │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  API Routes:                                         │  │
│  │  - POST /api/ingest      (PDF ingestion)           │  │
│  │  - POST /api/query       (Hybrid search + gen)     │  │
│  │  - GET /api/documents    (List documents)          │  │
│  │  - GET /api/health       (Health check)            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  PDFIngestion  │  │  QueryEngine │  │  Chunking    │  │
│  │  Pipeline      │  │              │  │  Strategy    │  │
│  └────────────────┘  └──────────────┘  └──────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼──────────┬──────────┐
        ▼            ▼          ▼          ▼
    ┌──────────┐ ┌────────┐ ┌────────┐ ┌─────────┐
    │OpenSearch│ │  BAAI/ │ │ Claude │ │ Sentence│
    │  (Index) │ │  bge   │ │  API   │ │Transform│
    │ (Port    │ │ Model  │ │        │ │         │
    │  9200)   │ │        │ │        │ │         │
    └──────────┘ └────────┘ └────────┘ └─────────┘
```

## Component Details

### 1. Frontend (Next.js + React + Tailwind CSS)

**Purpose**: User-facing interface for querying and ingesting documents

**Key Pages**:
- `/` (index.tsx): Query interface - search bar, results display, source attribution
- `/ingest` (ingest.tsx): PDF upload interface with progress feedback

**Technology Stack**:
- Next.js 14 for server-side rendering and API route organization
- React 18 for component-based UI
- TypeScript for type safety
- Tailwind CSS for responsive styling
- Axios for HTTP client

**Key Features**:
- Real-time query input with debouncing capability
- Expandable source chunks showing relevance scores
- Visual relevance indicator (progress bar)
- File upload with type validation
- Error handling and loading states

### 2. Backend (FastAPI + Python)

**Purpose**: Core business logic - ingestion, retrieval, and generation

**Structure**:
```
backend/
├── app/
│   ├── main.py         # FastAPI app, routes, middleware
│   ├── ingest.py       # PDF processing, chunking, indexing
│   ├── query.py        # Hybrid search, rank fusion, generation
│   └── __init__.py
├── requirements.txt    # Python dependencies
└── Dockerfile          # Container configuration
```

**Key Classes**:

#### PDFIngestionPipeline (ingest.py)
Manages the end-to-end ingestion workflow:

```python
class PDFIngestionPipeline:
    async def ingest(filename, content) → (document_id, chunks_count)
    async def _extract_pdf_text(content) → dict[page_num: text]
    async def _chunk_text(text_by_page, filename) → list[chunks]
    async def _embed_chunks(chunks) → list[embeddings]
    async def _index_chunks(document_id, chunks, embeddings) → int
```

Flow:
1. Extract text from PDF (page-by-page)
2. Chunk text into fixed-size segments (768 tokens, 20% overlap)
3. Generate embeddings using BAAI/bge-small-en-v1.5
4. Index chunks in OpenSearch with metadata

#### QueryEngine (query.py)
Handles query execution and answer generation:

```python
class QueryEngine:
    async def query_and_generate(query, top_k) → (answer, source_chunks)
    async def _hybrid_search(query, top_k) → list[results]
    async def _bm25_search(query, top_k) → list[results]
    async def _vector_search(embedding, top_k) → list[results]
    def _reciprocal_rank_fusion(bm25, vector, top_k) → list[results]
    async def _generate_answer(query, results) → str
```

Flow:
1. Generate query embedding
2. Execute BM25 search in parallel
3. Execute vector search in parallel
4. Apply Reciprocal Rank Fusion (60% semantic, 40% lexical weighting)
5. Pass top-K results to Claude API
6. Generate answer with source attribution

### 3. OpenSearch (Search Index)

**Purpose**: Store and retrieve document chunks with hybrid search capabilities

**Configuration**:
- **Index**: `rag-chunks`
- **Shards**: 1 (MVP) → scale to 3+ for production
- **Replicas**: 0 (MVP) → 1+ for high availability

**Mappings**:
```json
{
  "text": { "type": "text", "analyzer": "standard" },      // BM25
  "embedding": { "type": "dense_vector", "dimension": 384 }, // Vector
  "chunk_id": { "type": "keyword" },
  "document_id": { "type": "keyword" },
  "page_number": { "type": "integer" },
  "source": { "type": "keyword" },
  "created_at": { "type": "date" }
}
```

**Search Process**:
1. **BM25 Search**: Exact phrase matching, technical identifiers
2. **Vector Search**: Semantic similarity, paraphrased queries
3. **Rank Fusion**: Combine both rankings using Reciprocal Rank Fusion (RRF)

### 4. Embeddings (BAAI/bge-small-en-v1.5)

**Purpose**: Convert text to dense vectors for semantic search

**Specifications**:
- Model: `BAAI/bge-small-en-v1.5`
- Dimension: 384
- Output: List of floats representing semantic meaning
- Library: `sentence-transformers`

**Why this model**:
- Small footprint (~130MB) - runs locally without GPU
- Designed for retrieval tasks (optimized for similarity search)
- Good performance on technical documents
- Cost-free (no API calls)

### 5. LLM Integration (Claude 3.5 Sonnet)

**Purpose**: Generate context-aware answers grounded in retrieved documents

**Configuration**:
- Model: `claude-3-5-sonnet-20241022`
- Max tokens: 2048
- System prompt: Compliance-focused reasoning

**Prompt Structure**:
```
System Prompt:
- Expert compliance analyst persona
- Base answers on provided context only
- Cite sections and page numbers
- Explain complex requirements
- Describe requirement interactions

User Prompt:
- Question from user
- Retrieved context chunks
- Request for grounded answer
```

**Response Handling**:
- Extract answer from Claude response
- Preserve source chunk metadata for attribution
- Include relevance scores in UI

## Data Flow

### Ingestion Flow

```
1. User uploads PDF via /api/ingest
   ↓
2. Validate file (PDF type check)
   ↓
3. Extract text using pdfplumber (per page)
   ↓
4. Chunk text (768 tokens, 20% overlap)
   ↓
5. Generate embeddings (BAAI/bge-small-en-v1.5)
   ↓
6. Index in OpenSearch (BM25 + vector fields)
   ↓
7. Return document_id and chunk count
```

**Document ID Generation**:
```python
document_id = "doc_" + md5(filename + timestamp)[:8]
# Example: doc_a1b2c3d4
```

### Query Flow

```
1. User submits query via /api/query
   ↓
2. Generate query embedding (BAAI/bge)
   ↓
3. Execute BM25 search (parallel)
   ├─ Match against "text" field
   ├─ Return top 10 ranked by BM25 score
   ↓
4. Execute vector search (parallel)
   ├─ Find similar to query embedding
   ├─ Return top 10 ranked by cosine similarity
   ↓
5. Apply Reciprocal Rank Fusion
   ├─ Combine rankings with 60/40 semantic/lexical weighting
   ├─ Deduplicate results
   ├─ Return top-K merged results
   ↓
6. Send to Claude API
   ├─ Pass query + context chunks
   ├─ Use compliance-focused system prompt
   ├─ Generate grounded answer
   ↓
7. Return answer + source chunks to UI
```

## Error Handling & Resilience

### Ingestion
- **File validation**: Check PDF format before processing
- **PDF parsing errors**: Log and skip malformed pages
- **Embedding failures**: Retry with exponential backoff
- **Indexing errors**: Log failed chunks, continue with others

### Query
- **Index not ready**: Return 503 Service Unavailable
- **OpenSearch timeout**: Fallback to vector search only
- **Claude API timeout**: Return partial results without answer
- **No results**: Explain to user why retrieval failed

### Deployment
- **OpenSearch health checks**: Docker Compose `healthcheck` directive
- **Backend dependency management**: Wait for OpenSearch before starting
- **Frontend API fallback**: Graceful degradation if backend unavailable

## Scalability Considerations

### Current MVP (Single machine)
- 1 OpenSearch node (1GB heap)
- 1 FastAPI worker (single-threaded async)
- Frontend served by Next.js dev server

### Stage 1: Multi-worker Backend (1K docs/day)
- OpenSearch cluster (3 nodes)
- FastAPI with multiple workers (Gunicorn)
- Redis caching layer for embeddings
- Document-structure aware chunking

### Stage 2: Distributed Ingestion (10K docs/day)
- Job queue (Celery + Redis)
- Background workers for embedding/indexing
- Batch embedding optimization
- Chunk caching

### Stage 3: Vector DB Optimization (100K docs)
- Consider vector-optimized store (Milvus, Weaviate)
- Approximate nearest neighbor (ANN) indices
- Query result caching
- Reranking layer

## Security Considerations

**MVP (Development)**:
- No authentication (local development only)
- OpenSearch without SSL (Docker internal network)
- Admin credentials hardcoded (default Docker setup)

**Production Upgrade**:
- Add API authentication (API keys or OAuth)
- Enable SSL/TLS for OpenSearch
- Rotate credentials via environment variables
- Implement rate limiting
- Add CORS restrictions
- Log security events

## Monitoring & Observability

**Current**: Structured logging with `structlog` library

**Future Enhancements**:
- Application metrics (Prometheus)
- Distributed tracing (Jaeger)
- Error tracking (Sentry)
- Dashboard (Grafana)
- Query logging for evaluation

## Testing Strategy

### Unit Tests
- Chunking logic (boundary conditions, overlap)
- Embedding generation (vector dimension, normalization)
- Rank fusion (score calculation)

### Integration Tests
- End-to-end PDF ingestion
- Hybrid search accuracy
- Claude API integration
- API endpoint validation

### E2E Tests
- Upload PDF → query → receive answer
- Test with provided NIST document
- Validate source attribution

## References

- [OpenSearch Hybrid Search](https://opensearch.org/docs/latest/search-plugins/hybrid-search/)
- [BAAI/bge Model](https://huggingface.co/BAAI/bge-small-en-v1.5)
- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [Claude API Documentation](https://docs.anthropic.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
