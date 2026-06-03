# Quick Start Guide

Get the RAG Pipeline running in 5 minutes.

## Prerequisites

- Docker & Docker Compose
- Anthropic API key (get one at https://console.anthropic.com/)

## 1. Clone and Setup

```bash
cd /Users/binitamehta/Projects/rag-in-production
cp .env.example .env
```

## 2. Add Your API Key

Edit `.env` and set:
```bash
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

## 3. Start the Stack

```bash
docker-compose up --build
```

Wait for output showing all services healthy:
```
opensearch-1 | {"type": "server", "timestamp": "..."}
backend-1    | INFO:     Application startup complete
frontend-1   | ▲ Next.js 14.0.0
```

## 4. Open in Browser

- **Query UI**: http://localhost:3000
- **Ingest UI**: http://localhost:3000/ingest
- **API Docs**: http://localhost:8000/docs
- **OpenSearch**: http://localhost:9200 (admin/admin)

## 5. Ingest a Document

1. Go to http://localhost:3000/ingest
2. Download NIST 800-53r5 from: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5.pdf
3. Click upload area and select the PDF
4. Wait for "Ingestion complete" message (~30s for full document)

## 6. Query

1. Go to http://localhost:3000
2. Try a query: "What are AC-2 access control requirements?"
3. See retrieved chunks and Claude-generated answer

## Verification

### Health Check

```bash
curl http://localhost:8000/api/health
# Response: {"status":"healthy","message":"RAG Pipeline backend is running"}
```

### List Ingested Documents

```bash
curl http://localhost:8000/api/documents
# Response: {"documents":[{"document_id":"doc_...","chunk_count":245}]}
```

### Detailed Query

```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is AC-2?",
    "top_k": 3
  }' | jq
```

## Troubleshooting

### Port Already in Use
```bash
# Kill process on port
lsof -ti :3000 | xargs kill -9  # Frontend
lsof -ti :8000 | xargs kill -9  # Backend
lsof -ti :9200 | xargs kill -9  # OpenSearch
```

### OpenSearch Won't Start
```bash
# Check memory
docker stats

# Increase VM memory for Docker:
# macOS: Docker Desktop → Settings → Resources → Memory: 4GB+
```

### API Key Error
```bash
# Verify key is set
echo $ANTHROPIC_API_KEY

# If not set, add to Docker Compose:
docker-compose down
source .env
docker-compose up --build
```

### Slow PDF Upload
- Normal for large PDFs (2-3 min for 500-page document)
- Check backend logs: `docker-compose logs backend`
- Verify embeddings are being generated: `docker-compose logs | grep "embedding"`

## Next Steps

### 1. Test with Multiple Documents
- Upload NIST 800-171
- Upload NIST 800-172
- Query cross-document requirements

### 2. Evaluate Retrieval
- Run 10 test queries
- Compare retrieved chunks
- Note which queries have low relevance scores

### 3. Try Different Queries
- **Exact match**: "AC-2 Account Management"
- **Semantic**: "How to manage user accounts?"
- **Multi-control**: "Encryption and access control"
- **Compliance**: "Federal system security requirements"

### 4. Check Logs
```bash
docker-compose logs -f backend     # Backend logs
docker-compose logs -f opensearch  # OpenSearch health
```

### 5. Stop Services
```bash
docker-compose down
```

## Testing Advanced Features

### Query with Custom Top-K

```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Access control requirements",
    "top_k": 10
  }' | jq '.source_chunks | length'
```

### Direct OpenSearch Query

```bash
curl -X GET "http://localhost:9200/rag-chunks/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": {
        "text": "access control"
      }
    },
    "size": 5
  }'
```

### Check Embeddings

```bash
curl -X GET "http://localhost:9200/rag-chunks/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {"match_all": {}},
    "_source": ["chunk_id", "page_number", "document_name"],
    "size": 3
  }'
```

## Documentation

- [Architecture](./docs/ARCHITECTURE.md) - System design and components
- [Chunking Strategy](./docs/CHUNKING_STRATEGY.md) - How documents are split
- [Scaling Roadmap](./docs/SCALING.md) - Path to production (6-month plan)
- [Full README](./README.md) - Complete documentation

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Connection refused: localhost:9200` | OpenSearch not running | `docker-compose up opensearch` |
| `ANTHROPIC_API_KEY not set` | Missing env var | `export ANTHROPIC_API_KEY=...` |
| `PDF upload fails` | File too large | Max 50MB supported |
| `Query returns empty` | No documents indexed | Upload a PDF first |
| `Slow responses` | Resource constraints | Check `docker stats` |

## Performance Baselines

| Operation | Time | Notes |
|-----------|------|-------|
| PDF Upload (100 pages) | ~30s | Depends on CPU |
| PDF Upload (500 pages) | ~2min | NIST 800-53r5 size |
| Query Response | 1-3s | BM25 + vector + Claude |
| First Query (cold) | 5-8s | Model loading |
| Subsequent Queries | 1-2s | Cached model |

## Need Help?

1. Check logs: `docker-compose logs -f backend`
2. Test connectivity: `curl http://localhost:8000/api/health`
3. Verify data: `curl http://localhost:8000/api/documents`
4. Review docs: `/docs` folder
5. Test in Swagger UI: http://localhost:8000/docs
