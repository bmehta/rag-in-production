# Verification Checklist - Phase 5: Integration & Testing

Complete this checklist to verify the RAG Pipeline MVP is working correctly.

## Pre-Flight Check ✈️

- [ ] Docker and Docker Compose installed
- [ ] Anthropic API key obtained from https://console.anthropic.com/
- [ ] .env file created with API key
- [ ] No services running on ports 3000, 8000, 9200
- [ ] At least 4GB RAM available for Docker

## Startup & Initialization

- [ ] **Build and start stack**: `docker-compose up --build`
- [ ] **All services healthy**: Check no errors in logs
  - [ ] OpenSearch started (port 9200)
  - [ ] Backend started (port 8000)
  - [ ] Frontend started (port 3000)
- [ ] **Health check passes**: `curl http://localhost:8000/api/health`
  - Expected response: `{"status":"healthy","message":"RAG Pipeline backend is running"}`

## Backend Validation

### API Endpoints

- [ ] **GET /api/health**: Returns healthy status
  ```bash
  curl http://localhost:8000/api/health
  ```

- [ ] **GET /api/documents**: Returns empty list (no docs ingested yet)
  ```bash
  curl http://localhost:8000/api/documents
  ```

- [ ] **Swagger UI accessible**: http://localhost:8000/docs
  - [ ] Can see all endpoints documented
  - [ ] Can see request/response schemas

### OpenSearch Integration

- [ ] **OpenSearch responds**: `curl http://localhost:9200/_cluster/health`
- [ ] **Index exists after first ingest**: `curl http://localhost:9200/rag-chunks/_stats`
- [ ] **Can query index**: 
  ```bash
  curl -X GET "http://localhost:9200/rag-chunks/_search?pretty" -H "Content-Type: application/json" -d '{"query":{"match_all":{}},"size":1}'
  ```

### Embedding Model

- [ ] **Model loads without errors**: Check backend logs
  - Look for: "Embedding model loaded"
  - No CUDA/GPU errors expected (CPU mode is fine)

## Frontend Validation

### UI Accessibility

- [ ] **Homepage loads**: http://localhost:3000
  - [ ] Navigation bar visible
  - [ ] Query/Ingest links present
  - [ ] Page styled with Tailwind CSS

- [ ] **Query page loads**: http://localhost:3000
  - [ ] Search input visible
  - [ ] Submit button present
  - [ ] "No results" placeholder shown

- [ ] **Ingest page loads**: http://localhost:3000/ingest
  - [ ] Upload area visible
  - [ ] Document list shown
  - [ ] Instructions present

### Responsive Design

- [ ] **Desktop layout** (1920x1080): Content properly laid out
- [ ] **Tablet layout** (768x1024): Content readable
- [ ] **Mobile layout** (375x667): Touch targets appropriately sized

## Document Ingestion Test

### 1. Prepare PDF

- [ ] Download NIST 800-53r5 from:
  ```
  https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5.pdf
  ```
- [ ] File is ~4MB, should take 1-2 minutes to process

### 2. Upload Document

- [ ] Go to http://localhost:3000/ingest
- [ ] Click upload area and select NIST PDF
- [ ] See "Ingesting document..." message
- [ ] Wait for success message showing chunk count
  - Expected: ~200-300 chunks for NIST 800-53r5

### 3. Verify Ingestion

- [ ] **Document listed**: `curl http://localhost:8000/api/documents`
  - Should show: `{"documents":[{"document_id":"doc_...", "chunk_count": XXX}]}`

- [ ] **Chunks in OpenSearch**: 
  ```bash
  curl -X GET "http://localhost:9200/rag-chunks/_search" \
    -H "Content-Type: application/json" \
    -d '{"query":{"match_all":{}},"size":1}' | jq '.hits.total.value'
  ```
  - Should show: number of chunks ≥ 200

- [ ] **No ingestion errors**: Check backend logs
  ```bash
  docker-compose logs backend | grep -i error
  ```
  - Should see no errors (warnings are OK)

## Query & Retrieval Test

### Test Case 1: Exact Requirement Query

**Query**: "What is AC-2?"

**Expected behavior**:
- [ ] Query processes (no timeout)
- [ ] Answer generated (not empty)
- [ ] Source chunks displayed (≥ 1)
- [ ] Relevance scores shown (0-100%)
- [ ] Answer mentions "AC-2" or "Account Management"

### Test Case 2: Semantic Query

**Query**: "How do I manage user accounts?"

**Expected behavior**:
- [ ] Retrieves AC-2 control
- [ ] Answer discusses user account management
- [ ] Different chunks than exact query

### Test Case 3: Multi-Control Query

**Query**: "What are security requirements for federal systems?"

**Expected behavior**:
- [ ] Retrieves multiple controls (AC, SC, SI, etc.)
- [ ] Answer mentions security requirements
- [ ] Page numbers in source chunks

### Test Case 4: Complex Query

**Query**: "Explain encryption and access control requirements"

**Expected behavior**:
- [ ] Retrieves both encryption (SC-28) and access controls (AC-2)
- [ ] Answer explains both areas
- [ ] Sources cited correctly

## Response Quality Validation

For each query, verify:

- [ ] **Answer addresses the query**: Not off-topic
- [ ] **Answer is grounded**: References retrieved chunks
- [ ] **Source citations accurate**: Page numbers correct
- [ ] **No hallucinations**: No requirements not in sources
- [ ] **Compliance-focused**: Uses NIST terminology

## Performance Benchmarks

Measure and record:

| Metric | Measured | Expected | Pass |
|--------|----------|----------|------|
| API Health Response | __ms | <100ms | [ ] |
| Query Latency (warm) | __ms | <3000ms | [ ] |
| Query Latency (cold) | __ms | <5000ms | [ ] |
| PDF Ingestion (100 pages) | __sec | <60sec | [ ] |
| Chunk Count | __ | >200 | [ ] |

## Error Handling Tests

### Test 1: Invalid PDF Upload

- [ ] Upload non-PDF file
- [ ] See error message: "File must be a PDF"
- [ ] No crash or server error

### Test 2: Query Empty Database (reset)

- [ ] (Optional) Delete documents from OpenSearch
- [ ] Submit query
- [ ] See error or no results
- [ ] No crash

### Test 3: Very Long Query

- [ ] Submit 1000+ character query
- [ ] System handles gracefully
- [ ] Either returns results or error message

### Test 4: Rapid Queries

- [ ] Submit 5 queries in quick succession
- [ ] All complete successfully
- [ ] No race conditions

## Integration Test: Full Workflow

**Complete End-to-End Test**:

1. [ ] Start with fresh Docker Compose setup
2. [ ] Upload NIST 800-53r5 PDF
3. [ ] Verify chunks indexed
4. [ ] Execute 10 diverse queries
5. [ ] Review answers for accuracy
6. [ ] Check source attributions
7. [ ] Verify page numbers correct
8. [ ] No errors in backend logs
9. [ ] UI remains responsive
10. [ ] Can navigate between pages

## Documentation Verification

- [ ] README.md: Comprehensive and accurate
- [ ] ARCHITECTURE.md: All components documented
- [ ] CHUNKING_STRATEGY.md: Rationale clear
- [ ] SCALING.md: Roadmap realistic
- [ ] QUICKSTART.md: Works as documented
- [ ] CONTRIBUTING.md: Guidelines complete

## Code Quality Checks

### Backend

- [ ] No syntax errors: `python -m py_compile backend/app/*.py`
- [ ] Imports resolve: Can import all modules
- [ ] Type hints present: Check with `mypy` if available
- [ ] Logging works: See structured logs in output

### Frontend

- [ ] No TypeScript errors: `npx tsc --noEmit` (if installed)
- [ ] CSS renders: All Tailwind classes applied
- [ ] Responsive: Test mobile view in browser dev tools
- [ ] No console errors: Check browser dev tools

## Security Checklist

- [ ] API key not in code: Only in .env
- [ ] No credentials hardcoded: Check backend files
- [ ] CORS configured: Only allow localhost
- [ ] Environment variables documented: .env.example provided
- [ ] .gitignore excludes secrets: Check .env not tracked

## Final Sign-Off

- [ ] All checkboxes above completed ✅
- [ ] No unresolved issues or errors
- [ ] System ready for Phase 6 evaluation
- [ ] Documentation complete and accurate

**Date Tested**: _______________
**Tester**: _______________
**Notes**: _______________

## If Tests Fail

### Backend Won't Start

```bash
# Check Docker logs
docker-compose logs backend

# Common issues:
# 1. OpenSearch not ready - wait 30s
# 2. ANTHROPIC_API_KEY not set - set in .env
# 3. Port already in use - kill process: lsof -ti :8000 | xargs kill -9
```

### OpenSearch Health Check Fails

```bash
docker-compose logs opensearch
# May need to increase memory for Docker
# macOS: Docker Desktop → Settings → Resources → Memory: 4GB+
```

### Ingestion Fails

```bash
# Check for PDF parsing errors
docker-compose logs backend | grep -i pdf

# Try with smaller PDF first
# File must be valid PDF, not image or corrupted
```

### Queries Return No Results

```bash
# Verify documents indexed
curl "http://localhost:9200/rag-chunks/_count"

# Check if embeddings generated
docker-compose logs backend | grep "Embeddings generated"
```

### UI Not Loading

```bash
# Check frontend logs
docker-compose logs frontend

# Try clear cache: Ctrl+Shift+Delete (Dev Tools)
# Try hard reload: Ctrl+Shift+R
```

## Success Criteria Summary

The MVP is **successful** when:

1. ✅ All services start without errors
2. ✅ Can ingest NIST 800-53r5 PDF (200+ chunks)
3. ✅ Can query and receive grounded answers
4. ✅ Query latency < 3 seconds
5. ✅ Top-20 retrieval failure rate < 10%
6. ✅ UI is responsive and intuitive
7. ✅ Source attribution is accurate
8. ✅ No unhandled errors in logs
9. ✅ Documentation is complete
10. ✅ Ready for evaluation and scaling

---

**Next Step**: After successful verification, proceed to Phase 6 (Evaluation & Documentation)
