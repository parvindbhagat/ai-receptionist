# WP-RAG: WordPress RAG System - Async Batch Document Processing & Local Embeddings

A production-ready Retrieval-Augmented Generation (RAG) system with **asynchronous batch ingestion**, local LLM support, semantic embeddings, and vector storage. Built with Docker for seamless local development and cloud deployment.

**Current Status:** ✅ **Fully Operational** — Async batch ingestion, semantic search, and query capabilities all working.

## ✨ What's Implemented & Tested

- ✅ **Async Batch Ingestion** - Process multiple URLs without HTTP timeouts
- ✅ **Job Status Tracking** - Real-time progress with per-URL reporting
- ✅ **Semantic Search** - Find relevant documents using vector embeddings
- ✅ **Query Processing** - Get AI responses with source context
- ✅ **Health Monitoring** - Check all microservices status
- ✅ **Job Cancellation** - Stop running batch operations
- ✅ **Error Handling** - Per-URL failure reporting with retry capability
- ✅ **Local Embeddings** - Ollama integration for semantic vectors
- ✅ **Multi-Format Ingestion** - Support for URLs, PDFs, DOCX, TXT files

### Recently Added Features
- **Async Batch Ingestion** (March 18, 2026) - Solves HTTP timeout issues for large document sets

## 📊 System Overview

| Component | Status | Purpose |
|-----------|--------|---------|
| API Gateway | ✅ Running | Central entry point, job management |
| Document Processor | ✅ Running | URL/file extraction |
| Chunk Service | ✅ Running | Document splitting |
| Embedding Service | ✅ Running | Vector generation |
| RAG Service | ✅ Running | Query/search processing |
| Qdrant DB | ✅ Running | Vector storage & retrieval |
| Ollama LLM | ✅ Running | Local LLM engine |
| **Knowledge Base** | 📝 Empty | Ready for batch ingestion |


## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                    API Gateway (Port 3000)                         │
│                 Single Entry Point - All Operations                │
└──────┬────────────────┬─────────────────┬──────────────────────────┘
       │                │                 │
┌──────▼────────┐  ┌───▼────────┐  ┌────▼──────────┐
│ DOC PROCESSOR │  │ RAG SERVICE│  │JOB MANAGER    │
│  (Port 4001)  │  │ (Port 4002)│  │(Async Worker) │
└──────┬────────┘  └───┬────────┘  └───────────────┘
       │                │
┌──────▼─────────┐  ┌──▼──────────────────┐
│CHUNK SERVICE   │  │ QDRANT VECTOR DB   │
│(Port 4003)     │  │ (Port 6333)        │
└──────┬─────────┘  └──────────────────────┘
       │                  ▲
┌──────▼──────────────────┼──────────┐
│ EMBEDDING SERVICE      │          │
│ (Port 4004)            │          │
└──────┬──────────────────┘          │
       │                             │
┌──────▼──────────────────┐          │
│ OLLAMA/vLLM LLM RUNNER  ├──────────┘
│ (Port 11434 or 8000)    │
└─────────────────────────┘
```

## 📦 Microservices Overview

### 1. **API Gateway** (Port 3000)
- Central entry point for all operations
- Routes requests to appropriate services
- Manages asynchronous batch jobs
- Health checks for all services
- Provides unified REST API

### 2. **Document Processor** (Port 4001)
- Handles file uploads (PDF, DOCX, TXT)
- Extracts content from URLs
- Text preprocessing and validation
- Supports multiple document formats

### 3. **Chunk Service** (Port 4003)
- Splits documents into semantic chunks
- Recursive character splitting strategy
- Configurable chunk size and overlap
- Optimizes for embedding efficiency

### 4. **Embedding Service** (Port 4004)
- Generates semantic embeddings using local LLMs
- Batch processing for improved performance
- Stores vectors in Qdrant vector database
- Supports multiple embedding models

### 5. **RAG Service** (Port 4002)
- Semantic search across knowledge base
- Context retrieval for query processing
- Response generation using local LLM
- Configurable similarity thresholds

### 6. **Async Job Manager**
- Runs in background within API Gateway
- Enables long-running batch operations
- Tracks job status and progress
- Supports job cancellation

### 7. **Supporting Services**
- **Qdrant** (Port 6333): Vector database for semantic search
- **Ollama** (Port 11434): Local LLM runner (primary)
- **vLLM** (Port 8000): Alternative LLM runner (optional, for higher throughput)

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (Windows/Mac) or Docker (Linux)
- 16+ GB RAM recommended (for local LLM)
- 50GB+ disk space for models

### Setup

1. **Clone and navigate to project:**
```bash
cd "path/to/WPRAG"
```

2. **Create .env file:**
```bash
# Copy from example
cp .env.example .env

# Edit if needed (defaults are good for local development)
# nano .env
```

3. **Pull LLM models to Ollama (one-time setup):**
```bash
# Pull embedding model
docker exec ollama ollama pull nomic-embed-text

# Pull chat model
docker exec ollama ollama pull mistral:7b

# Or use larger model for better quality (requires more VRAM):
# docker exec ollama ollama pull llama2:13b
```

4. **Start the system:**
```bash
docker-compose up -d
```

5. **Verify services are running:**
```bash
curl http://localhost:3000/health
```

### Enable vLLM (Optional - for higher throughput)
```bash
docker-compose --profile vllm up -d vllm
```

## 🎯 First-Time Setup Checklist

After running `docker-compose up -d`, verify your setup:

- [ ] Check health: `curl http://localhost:3000/health`
- [ ] Pull LLM models (one-time):
  ```bash
  docker exec ollama ollama pull nomic-embed-text
  docker exec ollama ollama pull mistral:7b
  ```
- [ ] Test batch ingestion with 1-2 URLs first
- [ ] Monitor job progress with status endpoint
- [ ] Query your knowledge base after ingestion completes
- [ ] Check logs if anything fails: `docker-compose logs`

## 💡 Recommended First Test

**Ingest a Wikipedia article and query it:**

```bash
# Step 1: Submit batch job
curl -X POST http://localhost:3000/ingest/urls \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://en.wikipedia.org/wiki/Machine_learning"]}'

# Step 2: Check status every 30 seconds until "completed"
curl "http://localhost:3000/jobs/{job_id}/status"

# Step 3: Query your knowledge base
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?"}'
```



### **NEW: Async Batch Ingestion (Recommended for Multiple Documents)**

Batch ingest multiple URLs as a knowledge base without HTTP timeouts:

#### Step 1: Submit Batch Job
```bash
curl -X POST http://localhost:3000/ingest/urls \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://en.wikipedia.org/wiki/Artificial_intelligence",
      "https://en.wikipedia.org/wiki/Machine_learning",
      "https://en.wikipedia.org/wiki/Deep_learning"
    ]
  }'
```

**Response (HTTP 202 - Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Batch ingestion started. Poll /jobs/{job_id}/status for progress"
}
```

#### Step 2: Poll Job Status
```bash
curl http://localhost:3000/jobs/550e8400-e29b-41d4-a716-446655440000/status
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "total_urls": 3,
  "successful": 1,
  "failed": 0,
  "total_chunks": 268,
  "current_url": "https://en.wikipedia.org/wiki/Machine_learning",
  "current_index": 2,
  "created_at": "2026-03-18T08:00:00",
  "started_at": "2026-03-18T08:01:00",
  "completed_at": null
}
```

#### Step 3: View All Jobs
```bash
curl "http://localhost:3000/jobs?limit=10"
```

### **Single URL Ingestion (Blocking)**

For individual documents when you can wait for completion:

```bash
curl -X POST http://localhost:3000/ingest/url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/article"
  }'
```

### **File Upload Ingestion**

Upload and process local files (PDF, DOCX, TXT):

```bash
curl -X POST http://localhost:3000/ingest/file \
  -F "file=@document.pdf"
```

### **Query the Knowledge Base**

Submit a question and get AI-generated answers with source context:

```bash
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is artificial intelligence?"
  }'
```

### **Semantic Search (Without Answer Generation)**

Search for relevant chunks without waiting for AI response:

```bash
curl -X POST http://localhost:3000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning applications",
    "limit": 5,
    "threshold": 0.7
  }'
```

### **System Health & Status**

Check if all services are running:

```bash
curl http://localhost:3000/health
curl http://localhost:3000/status
```

### **Cancel a Running Job**

Stop an in-progress batch ingestion:

```bash
curl -X POST http://localhost:3000/jobs/550e8400-e29b-41d4-a716-446655440000/cancel
```

## 🔌 Complete API Reference

### GET Endpoints
```
GET /health              - Check health of all microservices
GET /status              - Get system status and configuration
GET /jobs                - List all batch ingestion jobs (supports ?limit=10)
GET /jobs/{job_id}/status - Get detailed status of specific job
```

### POST Endpoints
```
POST /ingest/url            - Ingest single URL (blocking)
POST /ingest/urls           - **ASYNC** Batch ingest multiple URLs
POST /ingest/file           - Upload and ingest file (PDF, DOCX, TXT)
POST /query                 - Query knowledge base and get AI response
POST /search                - Semantic search without answer generation
POST /knowledge-base/config - Save knowledge base metadata
POST /jobs/{job_id}/cancel  - Cancel running batch ingestion job
```

### Job State Diagram
```
queued → processing → completed
  ↓         ↓
  └─ cancelled (if cancelled while processing)
  ↓
  failed (on error)
```



Edit `.env` file to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `CHAT_MODEL` | `mistral:7b` | Local LLM for responses |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Model for embeddings |
| `CHUNK_SIZE` | `1000` | Characters per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `SIMILARITY_THRESHOLD` | `0.7` | Minimum similarity score |
| `MAX_CONTEXT_CHUNKS` | `5` | Max chunks in context |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## 📊 Available Models (Ollama)

### Embedding Models (Fast, Small)
- `nomic-embed-text` (138M) - **Recommended** - Fast, good quality
- `mxbai-embed-large` (335M) - Higher quality, slower
- `all-minilm:22m` (22M) - Very fast, lower quality

### Chat Models
- `mistral:7b` (Default) - Fast, good balance
- `llama2:7b` - Good quality, balanced
- `neural-chat:7b` - Optimized for chat
- `llama2:13b` - Higher quality (requires ~25GB VRAM)
- `mistral:large` - Needs more resources

**For low-resource machines:** Use `mistral:7b` + `nomic-embed-text`

## 🔧 Troubleshooting

### Batch Ingestion Job Issues

**Job appears stuck in "processing" state:**
```bash
# Check job details
curl http://localhost:3000/jobs/{job_id}/status

# If truly hung, cancel and retry
curl -X POST http://localhost:3000/jobs/{job_id}/cancel

# Check API Gateway logs for errors
docker-compose logs api-gateway
```

**Job status keeps returning empty results:**
```bash
# Ensure embedding service is working
curl http://localhost:3000/health

# Check embedding service logs
docker-compose logs embedding-service
```

**Jobs stuck after container restart:**
- Note: Jobs are stored in-memory and are lost on container restart
- Resubmit batch ingestion after restart

### Models Not Available

```bash
# List available models
docker exec ollama ollama list

# Pull models manually
docker exec ollama ollama pull mistral:7b
docker exec ollama ollama pull nomic-embed-text
```

### Service Connection Errors

```bash
# Check service logs (all services)
docker-compose logs doc-processor
docker-compose logs chunk-service
docker-compose logs embedding-service
docker-compose logs rag-service
docker-compose logs api-gateway

# Restart all services
docker-compose restart

# Full restart (if stuck)
docker-compose down
docker-compose up -d
```

### Out of Memory Issues

```bash
# Monitor memory usage
docker stats

# Reduce load by:
# 1. Edit .env
MAX_CONTEXT_CHUNKS=3
CHAT_MODEL=mistral:7b  # Use smaller model variant

# 2. Ingest fewer URLs per batch (3-5 max)

# 3. Reduce chunk size
CHUNK_SIZE=500  # Smaller chunks = less memory during embedding
```

### Qdrant Vector Database Issues

```bash
# Check Qdrant health
docker exec qdrant curl localhost:6333/health

# Check Qdrant logs
docker-compose logs qdrant

# Reset Qdrant data (⚠️ DELETES all embeddings)
docker-compose down
docker volume rm wprag_qdrant_storage  # Adjust volume name as needed
docker-compose up -d
```

### HTTP Timeouts on Batch Ingestion

**Problem:** "Connection timeout" when ingesting multiple URLs

**Solution:** Use async batch endpoint (`POST /ingest/urls`) instead of synchronous processing. Note: The async endpoint will not timeout even for very large batches.

### No Results from Query/Search

```bash
# Verify vectors are stored
curl http://localhost:3000/status

# Ensure documents were ingested (check job status)
curl http://localhost:3000/jobs

# Check similarity threshold (may be too high)
# Edit .env:
SIMILARITY_THRESHOLD=0.5  # Lower threshold for more results
```

## 📈 Performance Tips & Batch Ingestion

### Why Async Batch Ingestion?

Traditional synchronous requests fail for large knowledge bases due to HTTP timeouts (typically 300 seconds):
- Single Wikipedia article: ~3-5 minutes to process (chunking + embedding)
- 3 Wikipedia articles: ~10-15 minutes total
- Result: ❌ **HTTP timeout error**

**Solution:** Use async batch ingestion:
- Submit job → Get `job_id` immediately (HTTP 202)
- Request completes in < 1 second
- Poll status independently while processing continues
- No timeouts, full visibility into progress

### Performance Profile

| Operation | Time | Notes |
|-----------|------|-------|
| Chunk generation | ~1-2 sec per article | Faster for smaller docs |
| Embedding per chunk | ~1 sec per chunk | Varies with model complexity |
| Vector storage | Included in embedding time | Qdrant handles efficiently |
| **Total for 3 Wikipedia articles** | **10-15 minutes** | ~400+ chunks total |

### Batch Ingestion Best Practices

1. **Single Batch:** 3-5 URLs per batch for good visibility
2. **Content Size:** Test with representative articles first
3. **Monitoring:** Poll status every 10-30 seconds
4. **Model Selection:** Use `mistral:7b` + `nomic-embed-text` for best balance
5. **Resource Management:** Ensure 16GB+ RAM for stable processing

### Optimization Strategies

1. **Reduce chunk size** → Faster embeddings but less granular results
2. **Use smaller model** → `mistral:7b` instead of `llama2:13b`
3. **Enable GPU** → 5-10x speedup (CUDA/Metal support)
4. **Batch multiple documents** → Better throughput than individual requests

## 🚀 Deployment to AWS

When ready for production:

1. **Replace local services:**
   - Ollama → SageMaker Endpoints / Bedrock
   - Qdrant → Managed Qdrant Cloud / Aurora
   - Containers → ECS / Lambda

2. **Use infrastructure as code:**
   - Bicep/CloudFormation for AWS resources
   - Same Docker images for ECS tasks

3. **Add scaling:**
   - Auto-scaling groups
   - Load balancers
   - API Gateway

## 📝 Environment Variables

See `.env.example` for all available configuration options.

## 🛠️ Development

### Testing Async Batch Ingestion

**Quick Test on Windows (PowerShell):**
```powershell
# Submit batch job
$urls = @("https://en.wikipedia.org/wiki/Machine_learning")
$response = Invoke-RestMethod -Uri "http://localhost:3000/ingest/urls" `
  -Method Post `
  -Body (@{urls = $urls} | ConvertTo-Json) `
  -ContentType "application/json"

$jobId = $response.job_id
Write-Host "Job ID: $jobId"

# Poll status every 10 seconds
do {
  $status = Invoke-RestMethod -Uri "http://localhost:3000/jobs/$jobId/status"
  Write-Host "Status: $($status.status) - Chunks: $($status.total_chunks) - Progress: $($status.current_index)/$($status.total_urls)"
  Start-Sleep -Seconds 10
} while ($status.status -eq "processing")

Write-Host "Final Result: $($status | ConvertTo-Json)"
```

### Running Individual Services Locally (without Docker)

```bash
# Install Python dependencies
cd services/api-gateway
pip install -r requirements.txt

# Run API Gateway (connects to containerized services)
python app.py

# In another terminal, run another service:
cd services/chunk-service
pip install -r requirements.txt
python app.py
```

### Adding New Services

1. Create folder in `services/{service-name}`
2. Add `Dockerfile` and `requirements.txt`
3. Create `app.py` with Flask endpoints
4. Update `docker-compose.yaml`
5. Update `.env.example` if adding new config vars
6. Update API Gateway to route to new service
7. Add health check endpoint at `/health`

### Monitoring Production Deployments

For production, consider:
1. **Persistent Job Storage:** Add database for job history
2. **Job Retry Logic:** Automatic retry for failed URLs
3. **Monitoring Dashboards:** Prometheus + Grafana for metrics
4. **Job Timeout Handling:** Maximum runtime limits per job
5. **Rate Limiting:** Prevent DOS on batch ingestion endpoint



## 📄 License

Your project license here

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Test locally with `docker-compose`
4. Submit PR

## ❓ FAQ

**Q: Why is my batch ingestion timing out?**
A: Use the async endpoint (`POST /ingest/urls`) instead of synchronous processing. The API Gateway will return immediately with a `job_id` for background processing.

**Q: How do I know when my batch job is finished?**
A: Poll `GET /jobs/{job_id}/status` to check progress. The status will be "completed" when done. Response includes per-URL results and chunk counts.

**Q: Can I ingest unlimited URLs in one batch?**
A: Yes, but recommended: 3-5 URLs per batch for better visibility. Check status regularly during long-running jobs.

**Q: What happens if a URL fails during batch ingestion?**
A: Failed URLs are recorded in job results with error details. Other URLs continue processing. You can retry failed URLs in a new batch.

**Q: Can I cancel a batch job?**
A: Yes! Call `POST /jobs/{job_id}/cancel` while it's "processing". Once "completed", "failed", or "cancelled", you cannot change its state.

**Q: How long does batch ingestion typically take?**
A: ~3-5 minutes per Wikipedia-sized article (including chunking and embedding). 3 articles = ~10-15 minutes. Varies based on document size and system resources.

**Q: Can I use OpenAI API instead of local LLM?**
A: Yes! Update `PROVIDER=openai` in `.env` and add `OPENAI_API_KEY`. Async batch ingestion works with any provider.

**Q: How much disk space do I need?**
A: ~20-40GB for models, 5-10GB for documents and vectors. Larger knowledge bases need more storage.

**Q: Can I add custom chunking strategies?**
A: Yes, modify `services/chunk-service/app.py` to support recursive, semantic, or custom splitting strategies.

**Q: How do I backup my knowledge base?**
A: Export Qdrant collection snapshots or backup the Docker volume. See Qdrant documentation for snapshot management.

**Q: Can batch jobs survive container restarts?**
A: No, jobs are stored in-memory in the API Gateway. Restart requires resubmitting active batches. Consider implementing persistent job storage for production.

