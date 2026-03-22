# 🔗 API Client Guide - Postman & Requestly

**How to use Postman, Requestly, or any REST client to query your RAG System**

---

## 📋 Common Headers (All Requests)

```
Content-Type: application/json
Accept: application/json
```

**Optional Headers** (if authentication added later):
```
Authorization: Bearer YOUR_TOKEN_HERE
X-API-Key: YOUR_API_KEY
```

---

## 🎯 Main Endpoints

### **1. QUERY THE KNOWLEDGE BASE** ⭐ (Most Important)

**Endpoint:** `POST http://localhost:3000/query`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "query": "What is the difference between AI and machine learning?",
  "threshold": 0.7,
  "max_relevant_chunks": 5
}
```

**Response Example:**
```json
{
  "query": "What is the difference between AI and machine learning?",
  "answer": "Machine learning is a subset of artificial intelligence...",
  "context_chunks": [
    {
      "text": "Machine learning focuses on algorithms...",
      "source": "https://en.wikipedia.org/wiki/Machine_learning",
      "score": 0.87
    }
  ],
  "model": "mistral:7b"
}
```

**Postman Setup:**
1. Method: POST
2. URL: `http://localhost:3000/query`
3. Tab: Headers → Add `Content-Type: application/json`
4. Tab: Body → Select "raw" → JSON mode
5. Paste JSON body above
6. Click Send

---

### **2. SEARCH KNOWLEDGE BASE** (No LLM Response)

**Endpoint:** `POST http://localhost:3000/search`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "query": "deep learning neural networks",
  "limit": 5,
  "threshold": 0.6
}
```

**Response Example:**
```json
{
  "query": "deep learning neural networks",
  "results": [
    {
      "id": "chunk_123",
      "text": "Neural networks are computing systems...",
      "source": "https://en.wikipedia.org/wiki/Deep_learning",
      "score": 0.92
    }
  ],
  "count": 1
}
```

**Use Case:** You want search results without LLM-generated responses.

---

### **3. SUBMIT BATCH URL INGESTION** (Async)

**Endpoint:** `POST http://localhost:3000/ingest/urls`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "urls": [
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://en.wikipedia.org/wiki/Machine_learning",
    "https://en.wikipedia.org/wiki/Neural_network"
  ]
}
```

**Response Example (HTTP 202):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Batch ingestion started. Poll /jobs/{job_id}/status for progress"
}
```

**Next:** Use job_id to poll status (see below)

---

### **4. CHECK JOB STATUS** (For Async Operations)

**Endpoint:** `GET http://localhost:3000/jobs/{job_id}/status`

**Method:** GET (No body needed)

**Headers:**
```
Accept: application/json
```

**Response Example:**
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
  "results": [
    {
      "index": 1,
      "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
      "status": "success",
      "chunks_created": 268
    }
  ]
}
```

**Postman Setup:**
1. Method: GET
2. URL: `http://localhost:3000/jobs/550e8400-e29b-41d4-a716-446655440000/status`
3. Tab: Headers → Add `Accept: application/json`
4. No body needed
5. Click Send

---

### **5. LIST ALL JOBS**

**Endpoint:** `GET http://localhost:3000/jobs?limit=10`

**Method:** GET

**Headers:**
```
Accept: application/json
```

**Query Parameters:**
- `limit` (optional): Number of jobs to return (default: 10)

**Response Example:**
```json
{
  "jobs": [
    {
      "job_id": "550e8400-1",
      "status": "completed",
      "total_urls": 3,
      "successful": 3,
      "failed": 0,
      "total_chunks": 430
    },
    {
      "job_id": "550e8400-2",
      "status": "processing",
      "total_urls": 2,
      "successful": 0,
      "failed": 0,
      "total_chunks": 0
    }
  ],
  "count": 2
}
```

---

### **6. CANCEL A JOB**

**Endpoint:** `POST http://localhost:3000/jobs/{job_id}/cancel`

**Headers:**
```
Content-Type: application/json
```

**Body:** (Empty or `{}`)
```json
{}
```

**Response Example:**
```json
{
  "message": "Cancel requested"
}
```

---

### **7. SYSTEM HEALTH CHECK**

**Endpoint:** `GET http://localhost:3000/health`

**Method:** GET

**Headers:**
```
Accept: application/json
```

**Response Example:**
```json
{
  "status": "healthy",
  "services": {
    "chunk_service": "healthy",
    "doc_processor": "healthy",
    "embedding_service": "healthy",
    "rag_service": "healthy"
  }
}
```

---

### **8. API DOCUMENTATION**

**Endpoint:** `GET http://localhost:3000/`

**Method:** GET

**Response:** Full API documentation with workflow examples

---

## 🚀 POSTMAN COLLECTION

Save this as `.json` and import into Postman:

```json
{
  "info": {
    "name": "RAG System API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Query Knowledge Base",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"query\": \"What is machine learning?\",\n  \"threshold\": 0.7,\n  \"max_relevant_chunks\": 5\n}"
        },
        "url": {
          "raw": "http://localhost:3000/query",
          "protocol": "http",
          "host": ["localhost"],
          "port": "3000",
          "path": ["query"]
        }
      }
    },
    {
      "name": "Search Knowledge Base",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"query\": \"deep learning\",\n  \"limit\": 5,\n  \"threshold\": 0.6\n}"
        },
        "url": {
          "raw": "http://localhost:3000/search",
          "protocol": "http",
          "host": ["localhost"],
          "port": "3000",
          "path": ["search"]
        }
      }
    },
    {
      "name": "Submit Batch Ingestion",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"urls\": [\n    \"https://en.wikipedia.org/wiki/Artificial_intelligence\",\n    \"https://en.wikipedia.org/wiki/Machine_learning\"\n  ]\n}"
        },
        "url": {
          "raw": "http://localhost:3000/ingest/urls",
          "protocol": "http",
          "host": ["localhost"],
          "port": "3000",
          "path": ["ingest", "urls"]
        }
      }
    },
    {
      "name": "Check Job Status",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Accept",
            "value": "application/json"
          }
        ],
        "url": {
          "raw": "http://localhost:3000/jobs/{{job_id}}/status",
          "protocol": "http",
          "host": ["localhost"],
          "port": "3000",
          "path": ["jobs", "{{job_id}}", "status"]
        }
      }
    },
    {
      "name": "List All Jobs",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Accept",
            "value": "application/json"
          }
        ],
        "url": {
          "raw": "http://localhost:3000/jobs?limit=10",
          "protocol": "http",
          "host": ["localhost"],
          "port": "3000",
          "path": ["jobs"],
          "query": [
            {
              "key": "limit",
              "value": "10"
            }
          ]
        }
      }
    },
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Accept",
            "value": "application/json"
          }
        ],
        "url": {
          "raw": "http://localhost:3000/health",
          "protocol": "http",
          "host": ["localhost"],
          "port": "3000",
          "path": ["health"]
        }
      }
    }
  ]
}
```

---

## 🔧 POSTMAN SETUP STEP-BY-STEP

### **Create New Request:**
1. Click **+ New** → **Request**
2. Give it a name: "Query RAG System"
3. Choose **POST** method
4. Paste URL: `http://localhost:3000/query`

### **Add Headers:**
1. Click **Headers** tab
2. Add row: `Content-Type` → `application/json`

### **Add Body:**
1. Click **Body** tab
2. Select **raw**
3. Change dropdown to **JSON**
4. Paste:
```json
{
  "query": "What is artificial intelligence?",
  "threshold": 0.7,
  "max_relevant_chunks": 5
}
```

### **Send Request:**
1. Click **Send**
2. See response below

---

## 🎨 REQUESTLY SETUP

### **Create Rule:**
1. Click **+ Create Rule**
2. **Redirect Request**
3. Source URL: Any
4. Destination URL: `http://localhost:3000/query`
5. Method: POST

### **Add Body:**
In the request interceptor:
```json
{
  "query": "machine learning definition",
  "threshold": 0.7,
  "max_relevant_chunks": 5
}
```

### **Add Headers:**
```
Content-Type: application/json
```

---

## 💻 CURL EXAMPLES

### **Query Knowledge Base**
```bash
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is deep learning?",
    "threshold": 0.7,
    "max_relevant_chunks": 5
  }'
```

### **Search Knowledge Base**
```bash
curl -X POST http://localhost:3000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "neural networks",
    "limit": 5,
    "threshold": 0.6
  }'
```

### **Submit Batch Ingestion**
```bash
curl -X POST http://localhost:3000/ingest/urls \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://en.wikipedia.org/wiki/Artificial_intelligence",
      "https://en.wikipedia.org/wiki/Machine_learning"
    ]
  }'
```

### **Check Job Status**
```bash
curl -X GET "http://localhost:3000/jobs/550e8400-e29b-41d4-a716-446655440000/status" \
  -H "Accept: application/json"
```

### **List Jobs**
```bash
curl -X GET "http://localhost:3000/jobs?limit=10" \
  -H "Accept: application/json"
```

### **Health Check**
```bash
curl -X GET http://localhost:3000/health \
  -H "Accept: application/json"
```

---

## 🌐 JAVASCRIPT FETCH EXAMPLES

### **Query Knowledge Base**
```javascript
fetch('http://localhost:3000/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'What is machine learning?',
    threshold: 0.7,
    max_relevant_chunks: 5
  })
})
.then(r => r.json())
.then(data => console.log(data))
.catch(err => console.error(err));
```

### **Search Knowledge Base**
```javascript
fetch('http://localhost:3000/search', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'deep learning neural networks',
    limit: 5,
    threshold: 0.6
  })
})
.then(r => r.json())
.then(data => console.log(data))
.catch(err => console.error(err));
```

### **Submit Batch Ingestion**
```javascript
fetch('http://localhost:3000/ingest/urls', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    urls: [
      'https://en.wikipedia.org/wiki/Artificial_intelligence',
      'https://en.wikipedia.org/wiki/Machine_learning'
    ]
  })
})
.then(r => r.json())
.then(data => {
  console.log('Job ID:', data.job_id);
  // Poll status using data.job_id
})
.catch(err => console.error(err));
```

### **Check Job Status**
```javascript
const jobId = '550e8400-e29b-41d4-a716-446655440000';
fetch(`http://localhost:3000/jobs/${jobId}/status`, {
  method: 'GET',
  headers: {
    'Accept': 'application/json'
  }
})
.then(r => r.json())
.then(data => console.log(`Status: ${data.status}, Progress: ${data.current_index}/${data.total_urls}`))
.catch(err => console.error(err));
```

---

## ❌ Common Mistakes

| Mistake | Fix |
|---------|-----|
| Missing `Content-Type` header | Add `Content-Type: application/json` |
| Using GET instead of POST | Use POST for /query, /search, /ingest/urls |
| Malformed JSON in body | Validate JSON syntax (use jsonlint.com) |
| Hardcoding job_id | Copy from previous response or use variables |
| Using http:// instead of http:// | Use `http://localhost:3000` (not https) |
| Wrong port number | Use port `3000` for API Gateway |
| Empty body for POST requests | Include body with required fields |

---

## 📌 QUICK REFERENCE

| Operation | Method | URL | Body Required |
|-----------|--------|-----|---|
| Query KB | POST | `/query` | ✅ Yes |
| Search KB | POST | `/search` | ✅ Yes |
| Ingest URLs | POST | `/ingest/urls` | ✅ Yes |
| Check Job | GET | `/jobs/{id}/status` | ❌ No |
| List Jobs | GET | `/jobs` | ❌ No |
| Cancel Job | POST | `/jobs/{id}/cancel` | ✅ Yes (empty) |
| Health | GET | `/health` | ❌ No |

---

## 🎯 Most Used: Query Knowledge Base

**Copy-paste this to Postman:**

```
Method: POST
URL: http://localhost:3000/query

Headers:
Content-Type: application/json

Body (raw, JSON):
{
  "query": "What is artificial intelligence?",
  "threshold": 0.7,
  "max_relevant_chunks": 5
}
```

---

## 📞 Troubleshooting

**Q: Getting 404 error**  
A: Make sure API Gateway is running: `docker ps | grep api-gateway`

**Q: Getting Connection refused**  
A: Check if port 3000 is correct: `docker-compose ps`

**Q: Getting 500 error**  
A: Check service logs: `docker logs api-gateway`

**Q: Response empty**  
A: Knowledge base may be empty. Ingest URLs first with `/ingest/urls`

**Q: Job status stuck in "queued"**  
A: Wait a few seconds, then poll again. First URL is usually processing.

---

**Now you can test your RAG system from any API client!** 🚀
