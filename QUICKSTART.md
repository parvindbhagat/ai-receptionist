# Getting Started - Quick Commands

## 1. Initial Setup (First Time Only)

```bash
# Navigate to project
cd "path/to/WPRAG"

# Copy environment template
cp .env.example .env

# Start Docker services
docker-compose up -d

# Wait for services to be ready (30-60 seconds)
sleep 60

# Pull LLM models into Ollama (this takes 5-10 minutes)
docker exec ollama ollama pull mistral:7b
docker exec ollama ollama pull nomic-embed-text

# Verify setup
curl http://localhost:3000/health
```

## 2. Test the System

```bash
# Test with a simple URL
curl -X POST http://localhost:3000/ingest/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Artificial_intelligence"}'

# Query the knowledge base
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is artificial intelligence?"}'
```

## 3. Common Operations

```bash
# View service logs
docker-compose logs -f api-gateway
docker-compose logs -f rag-service

# Restart services
docker-compose restart

# Stop all services
docker-compose down

# Start services again
docker-compose up -d

# Check if models are loaded
docker exec ollama ollama list

# Access Qdrant Dashboard
# Open: http://localhost:6333/dashboard
```

## 4. Upload a File

```powershell
# PowerShell (Windows)
$FilePath = "C:\path\to\your\document.pdf"
$Uri = "http://localhost:3000/ingest/file"

$FileStream = [System.IO.File]::OpenRead($FilePath)
$Form = @{
    file = $FileStream
}

Invoke-RestMethod -Uri $Uri -Method Post -Form $Form
$FileStream.Close()
```

```bash
# Bash/Linux
curl -X POST http://localhost:3000/ingest/file \
  -F "file=@/path/to/document.pdf"
```

## 5. Troubleshooting

```bash
# Check all services are running
docker-compose ps

# View service health
curl http://localhost:3000/health | jq

# Check Ollama models
docker exec ollama ollama list

# View Qdrant collections
curl http://localhost:6333/collections

# Clear everything and restart
docker-compose down -v
docker-compose up -d
```

## 6. Performance Tuning

```bash
# Monitor Docker resource usage
docker stats

# If out of memory, reduce max context:
# Edit .env: MAX_CONTEXT_CHUNKS=3

# Use smaller model for faster responses:
# Edit .env: CHAT_MODEL=neural-chat:7b
```

## Service Ports

- **API Gateway**: http://localhost:3000 (Main entry point)
- **RAG Service**: http://localhost:4002
- **Doc Processor**: http://localhost:4001
- **Chunk Service**: http://localhost:4003
- **Embedding Service**: http://localhost:4004
- **Ollama**: http://localhost:11434
- **Qdrant**: http://localhost:6333

## Next Steps

1. ✅ Start system
2. ✅ Ingest documents (URLs or files)
3. ✅ Query the knowledge base
4. 🔄 Add custom chunking strategies
5. 🔄 Integrate with your application
6. 🚀 Deploy to AWS when ready
