# Scaling Roadmap

## MVP to Production: 6-Month Path

This document outlines the scaling journey from MVP (current state) to production-ready system handling 100K+ compliance documents.

## Phase 1: MVP (Month 1)

**Goal**: Validate core RAG workflow with single NIST document

**Architecture**:
```
1 OpenSearch node (1GB)
1 FastAPI worker (async)
1 Next.js dev server
Local BAAI/bge embeddings
```

**Capabilities**:
- Upload single or few NIST documents (~200-500 pages)
- Query with hybrid search (BM25 + vector)
- Generate answers with Claude
- ~1-2s query latency

**Operations**:
- Docker Compose for local development
- Manual PDF uploads via UI
- Logs to stdout

**Metrics to Track**:
- Query latency (p50, p95, p99)
- Retrieval accuracy (top-20 failure rate)
- Answer generation quality
- User feedback

**Success Criteria**:
- ✅ System runs end-to-end locally
- ✅ Query latency < 3s
- ✅ Top-20 retrieval failure rate < 10%
- ✅ Collected 50+ query-answer pairs

## Phase 2: Multi-Document + Async Ingestion (Month 2)

**Goal**: Support 100+ compliance documents with background ingestion

**Architecture Change**:
```
3-node OpenSearch cluster (3GB total)
FastAPI + Celery workers
Job queue (Redis)
Document caching layer
```

**Enhancements**:
1. **Async Ingestion Pipeline**
   - Convert `/api/ingest` to async job queue
   - Background workers process PDFs
   - Progress tracking endpoint `/api/ingest/{job_id}`
   - Retry logic with exponential backoff

2. **Improved Chunking**
   - Add LLM-based document structure detection
   - Extract control hierarchies (AC-2, SC-28, etc.)
   - Hierarchical metadata

3. **Embedding Optimization**
   - Batch embedding (32 chunks/batch)
   - GPU support (optional, for faster embedding)
   - Cache embeddings to avoid re-processing

4. **Search Enhancement**
   - Add reranking (Cohere API)
   - Query expansion (synonym detection)
   - Results caching (Redis)

**Operations**:
- Docker Compose with Redis + Celery
- Monitoring dashboard (basic)
- Document ingestion monitoring
- Alerting for failed jobs

**Metrics**:
- Ingestion throughput (chunks/min)
- Queue length and processing time
- Cache hit rate
- Answer generation latency with reranking

**Success Criteria**:
- ✅ Ingest 100 NIST documents (10-20 docs/min)
- ✅ Query latency < 2s (with reranking)
- ✅ Top-20 retrieval accuracy > 95%
- ✅ Support concurrent uploads

## Phase 3: Production Infrastructure (Month 3)

**Goal**: Deploy to cloud with high availability

**Architecture Change**:
```
AWS ECS / GKE deployment
Multi-zone OpenSearch cluster (6 nodes, 2 replicas)
CloudFront CDN for frontend
RDS for document metadata
S3 for document storage
```

**Enhancements**:
1. **Security**
   - TLS/SSL for all services
   - API authentication (API keys)
   - VPC/network isolation
   - Secrets management (AWS Secrets Manager / GCP Secret Manager)

2. **Availability**
   - Multi-zone deployment
   - Load balancing (Application Load Balancer)
   - Auto-scaling (Kubernetes HPA or EC2 ASG)
   - Database replication and backups

3. **Observability**
   - Prometheus metrics
   - ELK/CloudWatch logging
   - Jaeger distributed tracing
   - Grafana dashboards
   - PagerDuty alerting

4. **CI/CD**
   - GitHub Actions for automated testing
   - Semantic versioning
   - Blue-green deployments
   - Rollback capability

**Operations**:
- Terraform/CloudFormation IaC
- 24/7 monitoring
- Automated backups (daily)
- Disaster recovery procedures

**Metrics**:
- Availability (target: 99.9%)
- Error rates (target: <0.1%)
- MTTR (Mean Time To Recover)
- Cost per query

**Success Criteria**:
- ✅ 99.9% uptime over 30 days
- ✅ P95 latency < 2s
- ✅ Support 1000+ concurrent users
- ✅ Ingest 1K documents/day

## Phase 4: Advanced Retrieval (Month 4)

**Goal**: Improve retrieval accuracy to 98%+ with advanced techniques

**Enhancements**:
1. **Contextual Embeddings**
   - Pre-embed contextual windows around each chunk
   - Include parent requirement context
   - Result: ~35% improvement in retrieval

2. **Multi-Stage Ranking**
   - Stage 1: BM25 (fast, lexical)
   - Stage 2: Vector (semantic)
   - Stage 3: Reranker (slow but accurate)
   - Stage 4: LLM-based relevance scoring

3. **Query Understanding**
   - Extract compliance clauses from query (AC-2, SC-28)
   - Detect query intent (definition, requirement, example)
   - Adjust search weights accordingly

4. **Knowledge Graph Integration** (optional)
   - Extract relationships (AC-2 related to AC-3, etc.)
   - Use graph for relevance boosting
   - Support connected searches

**Ingestion Enhancement**:
- Parallel chunk processing (process 10 chunks in parallel)
- Vectorized embedding (batch 128 chunks)
- GPU acceleration for embeddings

**Operations**:
- A/B testing framework for retrieval improvements
- Continuous evaluation on benchmark queries
- Automated quality checks

**Metrics**:
- NDCG@10 (target: 0.92+)
- MRR (target: 0.95+)
- User satisfaction scores
- Cost per query (optimized)

**Success Criteria**:
- ✅ NDCG@10 > 0.92
- ✅ Retrieval failure rate < 2%
- ✅ User feedback rating > 4.5/5
- ✅ Ingest 10K documents

## Phase 5: Specialized Vector DB (Month 5)

**Goal**: Optimize for ultra-high scale (100K+ documents)

**Architecture Change**:
```
Purpose-built vector DB (Milvus or Weaviate)
OpenSearch for BM25 (optional, retire if query-only)
HybridSearch coordinator service
```

**Why Specialized DB?**
- OpenSearch good for hybrid, but not optimized for vector scale
- Specialized DBs offer: better ANN algorithms, faster indexing, lower cost at scale

**Enhancements**:
1. **Vector DB Setup**
   - Replace dense_vector embeddings with Milvus/Weaviate
   - Keep BM25 in OpenSearch or move to Elasticsearch
   - New flow: BM25 from OpenSearch + Vector from Milvus

2. **Approximate Nearest Neighbor (ANN)**
   - HNSW (Hierarchical Navigable Small World) for fast similarity
   - IVF (Inverted File Index) for memory efficiency
   - Trade: Speed vs. exact accuracy (still >99%)

3. **Caching Strategy**
   - Query result caching (Redis)
   - Embedding cache for popular chunks
   - Recent ingestion cache

4. **Partitioning & Sharding**
   - Partition by document collection (NIST 800-53, 800-171, etc.)
   - Shard by time (older docs → archive storage)
   - Routing logic for transparent distributed queries

**Ingestion Optimization**:
- Batch embedding (1K chunks/batch)
- Parallel indexing to both OpenSearch and Milvus
- Throughput: 1K docs/min (10x improvement)

**Operations**:
- Automated index optimization
- Background maintenance windows
- Compliance document versioning

**Metrics**:
- Query latency (P95: <500ms)
- Indexing throughput (1K docs/min)
- Storage efficiency (bits per vector)
- Cost per document stored

**Success Criteria**:
- ✅ Support 100K documents
- ✅ Query latency < 500ms
- ✅ Ingest 10K docs/day
- ✅ 50% cost reduction vs. OpenSearch-only

## Phase 6: Machine Learning & Eval (Month 6)

**Goal**: Continuous improvement with ML-driven ranking

**Enhancements**:
1. **Learning-to-Rank (LTR)**
   - Train ML model on query-relevance feedback
   - Features: BM25 score, vector similarity, term overlap, entity match, etc.
   - Output: Unified ranking score

2. **Query Understanding ML**
   - Classify query intent (definition, example, requirement, relationship)
   - Extract entities (control IDs, keywords)
   - Adjust search parameters dynamically

3. **Answer Quality Scoring**
   - Fine-tune LLM for compliance domain (optional)
   - Automatic quality scoring of generated answers
   - User feedback loop for continuous improvement

4. **Evaluation Framework**
   - Track NDCG, MRR, MAP across query categories
   - A/B test new retrieval strategies
   - Benchmark on standardized compliance QA dataset

**Data Collection**:
- Log all queries + click feedback (implicit)
- Explicit ratings: users rate answer quality
- A/B test results
- Generate synthetic test queries

**Operations**:
- ML pipeline (training, validation, deployment)
- Offline evaluation before production deployment
- Online A/B testing for final validation
- Rollback capability if metrics degrade

**Metrics**:
- User satisfaction (NPS)
- Click-through rate (CTR) on results
- Answer quality scores
- Compliance to user expectations

**Success Criteria**:
- ✅ 98%+ retrieval accuracy
- ✅ User satisfaction > 4.7/5
- ✅ Support 100K+ documents
- ✅ 99.95% uptime

## Timeline & Effort Estimate

| Phase | Duration | Team Size | Est. Effort |
|-------|----------|-----------|------------|
| 1 (MVP) | 1 month | 1-2 | 200 hours |
| 2 (Async + Reranking) | 1 month | 2 | 300 hours |
| 3 (Cloud Prod) | 1 month | 2-3 | 400 hours |
| 4 (Advanced Retrieval) | 1 month | 2 | 300 hours |
| 5 (Vector DB) | 1 month | 2 | 250 hours |
| 6 (ML & Eval) | 1 month | 2-3 | 350 hours |
| **Total** | **6 months** | **2-3** | **1800 hours** |

## Cost Trajectory

| Phase | Infrastructure | APIs | Total/Month |
|-------|-----------------|------|------------|
| 1 (MVP) | $50 (local) | $100 | $150 |
| 2 | $200 (small cluster) | $200 | $400 |
| 3 (Prod) | $1K (HA setup) | $500 | $1.5K |
| 4 | $2K (multi-zone) | $800 | $2.8K |
| 5 | $2.5K (vector DB) | $500 | $3K |
| 6 | $3K (ops overhead) | $400 | $3.4K |

**Cost Optimization Strategies**:
- Use open-source vector DB (Milvus) vs. managed (Pinecone)
- Batch Claude API calls (10-100 queries/batch)
- Cache common queries (80/20 rule: 20% queries = 80% volume)
- Archive old documents to cheaper storage

## Key Decisions at Each Phase

### Phase 1→2 Transition
**Decision**: Keep OpenSearch or add specialized vector DB?
- **Keep** if: <10K documents, simple queries, cost-sensitive
- **Switch** if: 100K+ documents, latency critical, accuracy focus

### Phase 3→4 Transition
**Decision**: Invest in retrieval improvement?
- **Yes** if: User feedback indicates retrieval issues (>5% failure)
- **No** if: Generation quality is bottleneck, answer issues common

### Phase 5→6 Transition
**Decision**: Implement ML ranking?
- **Yes** if: Enough query volume (1000+ queries/week) for training
- **No** if: Deterministic rules sufficient, cost prohibitive

## Appendix: Technology Choices

### Vector DB Options for Phase 5

| DB | Pros | Cons | Cost |
|----|------|------|------|
| **Milvus** (Open) | Open-source, powerful, scalable | Self-hosted ops | $0-1K/mo |
| **Weaviate** (Open) | Good community, good UX | Newer, less proven | $0-2K/mo |
| **Pinecone** (Managed) | Managed ops, easy | Expensive, vendor lock-in | $5-50K/mo |
| **Qdrant** (Open/Managed) | Growing, good perf | Smaller community | $0-3K/mo |

**Recommendation**: Start with open-source (Milvus), migrate to managed if ops burden becomes high.

### ML Infrastructure

- **Training**: Scikit-learn (small scale) → LightGBM or XGBoost (production)
- **Serving**: FastAPI with MLflow model registry
- **Evaluation**: Custom metric library + TREC eval tools

### References

- [TREC Evaluation Metrics](https://trec.nist.gov/trec_eval/)
- [Learning to Rank](https://en.wikipedia.org/wiki/Learning_to_rank)
- [Milvus Docs](https://milvus.io/docs)
- [Weaviate Docs](https://weaviate.io/developers/weaviate)
