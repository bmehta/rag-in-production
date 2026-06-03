# Chunking Strategy

## Overview

Chunking is the process of breaking large documents into manageable pieces for embedding and retrieval. The strategy used significantly impacts retrieval quality, latency, and cost.

## MVP Strategy: Fixed-Size Chunking

### Specification

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Chunk Size | 768 tokens (~500-600 words) | Balance context window with embedding cost |
| Overlap | 20% (~150 tokens) | Prevent information loss at boundaries |
| Token Estimation | Word count ÷ 1.3 | Conservative estimate for technical text |
| Minimum Chunk | 10 tokens | Skip very small fragments |
| Maximum Chunks | Unlimited | Assume reasonable document sizes |

### Algorithm

```python
tokens = text.split()  # Tokenize by whitespace
window_size = 768
overlap = window_size * 0.2  # 150 tokens
stride = window_size - overlap  # 618 tokens

for start_idx in range(0, len(tokens), stride):
    end_idx = min(start_idx + window_size, len(tokens))
    chunk = tokens[start_idx:end_idx]
    if len(chunk) > 10:
        yield chunk
```

### Metadata Preserved

Each chunk includes:
- `chunk_id`: Unique identifier (document_id + chunk_index)
- `document_id`: Source document
- `page_number`: Page in original PDF
- `source`: Original filename
- `chunk_index`: Sequential position
- `text`: Chunk content
- `embedding`: Dense vector representation

### Advantages

✅ **Simple**: No LLM dependencies, fast processing
✅ **Predictable**: Consistent size for batching embeddings
✅ **Debuggable**: Easy to trace which chunk retrieved
✅ **Scalable**: Works for 10s to 1000s of documents
✅ **Storage efficient**: Minimal metadata overhead

### Limitations

❌ **May split mid-sentence**: Technical content can be fragmented
❌ **Loses structure**: No awareness of sections, tables, bullet points
❌ **Compliance boundaries**: May cut off requirements mid-clause
❌ **Limited context**: No implicit relationship between consecutive chunks

### NIST Document Considerations

**Challenge**: NIST 800-53r5 is highly structured with nested requirements

**Example of problematic split**:
```
Chunk 1 (ends):
"AC-2 Account Management. Organizations must...
  (a) Identify and select the following types..."

Chunk 2 (starts):
"...of information system accounts: Privileged;
Non-privileged; Service; Shared/Group..."
```

**Impact**: Both chunks incomplete, reduces retrieval quality

**Mitigation in MVP**: 
- Larger overlap (20%) helps preserve context across boundaries
- Claude prompt encourages citing related clauses
- Can add section detection post-retrieval

## Future: Document-Structure-Aware Chunking

### Recommended for: 10+ documents, retrieval accuracy >5% failure rate

### Approach

1. **Parse Document Structure**
   ```
   Document
   ├── Control Family (e.g., "AC - Access Control")
   ├── Control (e.g., "AC-2 Account Management")
   │   ├── Requirement Statements
   │   ├── Sub-requirements (a, b, c, ...)
   │   └── Supplemental Guidance
   ```

2. **Hierarchical Chunking**
   - Each control = 1+ chunks
   - Sub-requirements = separate chunks with parent reference
   - Supplemental guidance = optional additional chunks

3. **Contextual Enrichment**
   ```python
   chunk_with_context = {
       "text": "Requirement statement",
       "context": {
           "family": "AC - Access Control",
           "control": "AC-2 Account Management",
           "requirement": "(a)",
           "parent_requirement": "AC-2"
       }
   }
   ```

### Expected Improvements

| Metric | Fixed-Size | Structure-Aware | Improvement |
|--------|-----------|-----------------|------------|
| Top-20 Retrieval Failure | ~5% | ~2.9% | 42% ↓ |
| Exact Control Match | ~82% | ~95% | 13% ↑ |
| Avg Chunk Coherence | 3/5 | 4.5/5 | 50% ↑ |

### Implementation

**Option A: Manual Section Detection**
- Use PDF text structure (section headers with numbers)
- Regex pattern matching for NIST control IDs (AC-2, SC-28, etc.)
- Split on detected boundaries
- ~1K lines of code, works for well-formatted PDFs

**Option B: LLM-Based Chunking**
- Pass document to Claude with chunking instructions
- Claude identifies control boundaries and requirements
- Return structured chunks with hierarchy
- Cost: ~$1-2 per 100K tokens (NIST 800-53r5 ≈ 170K tokens)
- Benefit: Works for any compliance document, highest quality
- Recommended approach for production

**Option C: Semantic Chunking**
- Use embedding similarity to detect content boundaries
- When similarity drops below threshold, start new chunk
- Slower (requires embedding all potential boundaries)
- Works for any document type
- Good balance of cost and quality

## Extraction & Chunking Pipeline

### Step 1: Text Extraction

```python
import pdfplumber

with pdfplumber.open("NIST.SP.800-53r5.pdf") as pdf:
    for page_num, page in enumerate(pdf.pages):
        text = page.extract_text()  # Per-page extraction
        # Preserve page boundaries for metadata
```

**Why page-by-page?**
- Enables accurate page_number in metadata
- Easier to debug "where did this come from?"
- Handles headers/footers gracefully (per-page extraction skips)

### Step 2: Text Cleaning

```python
def clean_text(text):
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove control characters
    text = ''.join(ch for ch in text if ch.isprintable() or ch.isspace())
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    return text
```

### Step 3: Chunking

See "Algorithm" section above

### Step 4: Embedding

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('BAAI/bge-small-en-v1.5')
embeddings = model.encode(texts, convert_to_numpy=False)
```

### Step 5: Indexing

```python
opensearch_client.index(
    index="rag-chunks",
    id=chunk_id,
    body={
        "text": chunk["text"],
        "embedding": embeddings[i],
        "page_number": chunk["page_number"],
        # ... metadata
    }
)
```

## Evaluation Metrics

### Chunking Quality Metrics

1. **Chunk Coherence**: Does chunk make sense on its own? (1-5 scale)
2. **Boundary Quality**: Are boundaries at natural breaking points? (1-5 scale)
3. **Information Density**: Information per token (higher = better compression)
4. **Overlap Effectiveness**: Is overlap preventing lost information? (% of cross-boundary dependencies)

### Retrieval Impact Metrics

1. **Top-K Retrieval Rate**: Percentage of queries where relevant chunk appears in top-K
2. **MRR (Mean Reciprocal Rank)**: Average rank of first relevant result
3. **NDCG@10**: Normalized discounted cumulative gain at rank 10
4. **Precision@K**: Percentage of top-K results that are relevant

## Recommendations by Use Case

### For MVP: Single NIST Document
- ✅ Use: Fixed-size chunking (768 tokens, 20% overlap)
- Time to implement: 1 hour
- Retrieval quality: ~85-90%

### For Production: 3-5 NIST Documents
- ✅ Use: LLM-based structure-aware chunking (Option B)
- Time to implement: 1-2 days
- Retrieval quality: ~95-98%
- Cost: ~$2-3 one-time (per document set)

### For Multiple Compliance Frameworks
- ✅ Use: Hybrid approach
  - LLM chunking for structured docs (NIST, ISO)
  - Semantic chunking for unstructured docs (whitepapers)
- Time to implement: 2-3 days
- Retrieval quality: ~95%+ across domains

### For Scaling (100K+ Documents)
- ✅ Use: Pre-computed optimal chunking
  - Cache LLM chunking results
  - Use stored chunk boundaries for similar documents
- Performance: 10x faster ingestion

## Monitoring & Iteration

### Track These Metrics

1. **Ingestion**: Chunks per document, avg chunk size, processing time
2. **Retrieval**: Top-K failure rate, MRR, user feedback (thumbs up/down)
3. **Generation**: Answer quality scores, citation accuracy

### When to Upgrade Chunking

- ❌ Top-20 retrieval failure rate > 5%
- ❌ User feedback: "couldn't find relevant information"
- ❌ Cross-domain documents (non-NIST)
- ✅ Ingesting 10+ compliance documents

### Upgrade Path

1. **Month 1**: Fixed-size chunking + collect query feedback
2. **Month 2**: Analyze failures, consider LLM chunking
3. **Month 3**: Implement LLM-based chunking
4. **Month 4+**: Monitor quality, iterate prompt engineering

## References

- **Chunking Strategies**: https://www.anthropic.com/research/long-context-window-retrieval
- **Token Estimation**: GPT-3 tokenizer (useful approximation)
- **NIST Documents**: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5.pdf
- **Evaluation**: TREC evaluation metrics (https://trec.nist.gov/)
