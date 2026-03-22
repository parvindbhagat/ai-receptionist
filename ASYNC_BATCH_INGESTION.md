# 🚀 **Async Batch Ingestion - Complete Guide**

## ✅ **Problem Solved**

Your RAG system now supports **asynchronous batch ingestion** for multiple URLs, solving the HTTP timeout issue:

### **Before (Synchronous)**
- Submit batch ingestion request
- Request blocks waiting for all URLs to process
- **Timeout after 300 seconds** (even though processing takes 10-15 minutes)
- ❌ No way to know job progress

### **After (Asynchronous)**
- Submit batch ingestion request → Get `job_id` immediately (HTTP 202)
- **Request completes in < 1 second**
- Poll job status independently  
- ✅ Full progress tracking and job monitoring

---

## 📋 **Async Workflow**

### **Step 1: Submit Batch Ingestion Job**

```powershell
$payload = @{
  urls = @(
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://en.wikipedia.org/wiki/Machine_learning",
    "https://en.wikipedia.org/wiki/Deep_learning"
  )
} | ConvertTo-Json

$job = Invoke-RestMethod -Uri "http://localhost:3000/ingest/urls" `
  -Method Post `
  -Body $payload `
  -ContentType "application/json"

Write-Host "Job ID: $($job.job_id)"
Write-Host "Status: $($job.status)"
```

**Response (HTTP 202 - Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Batch ingestion started. Poll /jobs/{job_id}/status for progress"
}
```

---

### **Step 2: Poll Job Status**

```powershell
$job_id = "550e8400-e29b-41d4-a716-446655440000"

$status = Invoke-RestMethod -Uri "http://localhost:3000/jobs/$job_id/status" `
  -TimeoutSec 30

Write-Host "Status: $($status.status)"
Write-Host "Progress: $($status.current_index)/$($status.total_urls)"
Write-Host "Chunks Created: $($status.total_chunks)"
Write-Host "Current URL: $($status.current_url)"
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
  "completed_at": null,
  "results": [...]
}
```

---

### **Step 3: Monitor Until Complete**

```powershell
$job_id = "550e8400-e29b-41d4-a716-446655440000"

$completed = $false
while (-not $completed) {
  $status = Invoke-RestMethod "http://localhost:3000/jobs/$job_id/status"
  
  Write-Host "[$($status.status.ToUpper())] $($status.current_index)/$($status.total_urls) | Chunks: $($status.total_chunks)"
  
  if ($status.status -in @("completed", "failed", "cancelled")) {
    $completed = $true
    Write-Host "`n✅ Job Finished!"
    Write-Host "  Successful: $($status.successful)"
    Write-Host "  Failed: $($status.failed)"
    Write-Host "  Total Chunks: $($status.total_chunks)"
  } else {
    Start-Sleep -Seconds 10
  }
}
```

---

## 🎯 **Job Statuses**

| Status | Meaning | Can Poll Again? |
|--------|---------|-----------------|
| `queued` | Waiting to start | Yes |
| `processing` | Currently ingesting URLs | Yes |
| `completed` | All success or some failed | No - Terminal State |
| `failed` | Critical error occurred | No - Terminal State |
| `cancelled` | User cancelled the job | No - Terminal State |

---

## 🔧 **API Endpoints**

### **POST /ingest/urls** - Submit Batch Job
```
Returns: HTTP 202 (Accepted)
{
  "job_id": "uuid",
  "status": "queued"
}
```

### **GET /jobs/{job_id}/status** - Get Job Status
```
Returns: HTTP 200
{
  "job_id": "uuid",
  "status": "processing|completed|failed|cancelled",
  "total_urls": number,
  "successful": number,
  "failed": number,
  "total_chunks": number,
  "current_url": "...",
  "current_index": number,
  "results": [...]
}
```

### **GET /jobs** - List All Jobs
```
Returns: HTTP 200
{
  "jobs": [...],
  "count": number
}
```

### **POST /jobs/{job_id}/cancel** - Cancel Running Job
```
Returns: HTTP 200
{
  "message": "Cancel requested"
}
```

---

## ⏱️ **Performance & Timing**

| Operation | Time |
|-----------|------|
| Job submission | < 1 second |
| Batch job startup delay | 1-2 seconds |
| Per Wikipedia article | 3-5 minutes |
| Per chunk embedding | ~1 second |
| Status poll response | < 100ms |

**Example: 3 Wikipedia URLs**
- Total time: **10-15 minutes** depending on article size
- AI article (268 chunks): ~5 minutes
- ML article (162 chunks): ~3 minutes
- DL article (~200 chunks): ~4 minutes

---

## 💡 **Complete Examples**

### **Example 1: Build Knowledge Base from News Articles**

```powershell
$urls = @(
  "https://news.example.com/ai-trends",
  "https://news.example.com/ml-breakthroughs",
  "https://news.example.com/deep-learning-applications"
)

# Submit
$job = Invoke-RestMethod -Uri "http://localhost:3000/ingest/urls" `
  -Method Post `
  -Body (@{urls = $urls} | ConvertTo-Json) `
  -ContentType "application/json"

# Monitor with exponential backoff
$wait_time = 10
while ($true) {
  $status = Invoke-RestMethod "http://localhost:3000/jobs/$($job.job_id)/status"
  
  Write-Host "$(Get-Date -Format 'HH:mm:ss') [$($status.status)] $($status.successful)/$($status.total_urls) complete"
  
  if ($status.status -eq "completed") {
    Write-Host "✅ Knowledge base ready with $($status.total_chunks) chunks!"
    break
  }
  
  Start-Sleep -Seconds $wait_time
  $wait_time = [Math]::Min($wait_time + 5, 60)  # Cap at 60 seconds
}
```

### **Example 2: Batch Multiple Knowledge Bases**

```powershell
$knowledge_bases = @(
  @{
    name = "AI Foundations"
    urls = @(
      "https://en.wikipedia.org/wiki/Artificial_intelligence",
      "https://en.wikipedia.org/wiki/History_of_artificial_intelligence"
    )
  },
  @{
    name = "ML Techniques"
    urls = @(
      "https://en.wikipedia.org/wiki/Machine_learning",
      "https://en.wikipedia.org/wiki/Deep_learning"
    )
  }
)

$jobs = @()

foreach ($kb in $knowledge_bases) {
  Write-Host "Starting: $($kb.name)"
  $job = Invoke-RestMethod -Uri "http://localhost:3000/ingest/urls" `
    -Method Post `
    -Body (@{urls = $kb.urls} | ConvertTo-Json) `
    -ContentType "application/json"
  
  $jobs += @{
    name = $kb.name
    job_id = $job.job_id
  }
}

# Wait for all jobs
foreach ($job_ref in $jobs) {
  while ($true) {
    $status = Invoke-RestMethod "http://localhost:3000/jobs/$($job_ref.job_id)/status"
    
    if ($status.status -eq "completed") {
      Write-Host "✅ $($job_ref.name): $($status.total_chunks) chunks"
      break
    }
    
    Start-Sleep -Seconds 10
  }
}

Write-Host "All knowledge bases ready!"
```

### **Example 3: Monitor with Progress Bar**

```powershell
function Watch-IngestionJob($job_id) {
  while ($true) {
    $status = Invoke-RestMethod "http://localhost:3000/jobs/$job_id/status"
    $percent = if ($status.total_urls -gt 0) {
      [Math]::Round(($status.current_index / $status.total_urls) * 100)
    } else {
      0
    }
    
    Write-Progress -Activity "Batch Ingestion" `
      -Status "$($status.status)" `
      -PercentComplete $percent `
      -CurrentOperation "$($status.current_index)/$($status.total_urls) URLs | $($status.total_chunks) chunks"
    
    if ($status.status -eq "completed") {
      Write-Progress -Activity "Batch Ingestion" -Completed
      return $status
    }
    
    Start-Sleep -Seconds 5
  }
}

$result = Watch-IngestionJob "550e8400-e29b-41d4-a716-446655440000"
Write-Host "Final: $($result.successful) successful, $($result.failed) failed"
```

---

## ⚠️ **Error Handling**

### **Normal Ingestion Complete (even with failures)**
```json
{
  "status": "completed",
  "successful": 2,
  "failed": 1,
  "results": [
    {"url": "...", "status": "success", "chunks_created": 100},
    {"url": "...", "status": "failed", "error": "HTTP 403 - Access Denied"}
  ]
}
```

### **Critical Error (entire job fails)**
```json
{
  "status": "failed",
  "error": "Service unavailable"
}
```

### **Handling in Code**
```powershell
$status = Invoke-RestMethod "http://localhost:3000/jobs/$job_id/status"

switch ($status.status) {
  "processing" { 
    Write-Host "Still processing..." 
  }
  "completed" {
    if ($status.failed -gt 0) {
      Write-Host "⚠️ Some URLs failed:"
      $status.results | Where-Object {$_.status -eq "failed"} | ForEach-Object {
        Write-Host "  - $($_.url): $($_.error)"
      }
    }
  }
  "failed" {
    Write-Host "❌ Job failed: $($status.error)"
  }
}
```

---

## 📊 **Job Results Structure**

```
job_id: Unique identifier for tracking
status: Current state (queued, processing, completed, failed, cancelled)
total_urls: Total URLs submitted
successful: Count of successfully ingested URLs
failed: Count of failed URLs
total_chunks: Total chunks created across all URLs
current_url: URL currently being processed
current_index: Which URL is being processed (1-based)
created_at: ISO timestamp when job was created
started_at: ISO timestamp when processing began
completed_at: ISO timestamp when job finished (or null if still running)
results: Array of per-URL results
  ├── index: URL index (1-based)
  ├── url: The URL that was ingested
  ├── status: "success" or "failed"
  ├── chunks_created: Number of chunks (success only)
  └── error: Error message (failure only)
```

---

## ✨ **Key Improvements**

✅ **No More Timeouts** - Async processing handles long-running tasks
✅ **Full Progress Tracking** - Know exactly where the job is  
✅ **Non-Blocking** - Submit multiple jobs, they run independently
✅ **Cancellable** - Can stop a job mid-process with `/jobs/{id}/cancel`
✅ **Job History** - View all recent jobs with `/jobs?limit=10`
✅ **Per-URL Results** - See which URLs succeeded/failed and why

---

## 🎓 **Development Notes**

The async implementation uses:
- **Python `threading.Thread`** for background jobs
- **Thread-safe job store** with locks for concurrent access
- **ISO 8601 timestamps** for all date/time fields
- **HTTP 202 (Accepted)** for async job submission
- **Graceful cancellation** with `cancel_requested` flag

All job data is **in-memory** and will be cleared if the container restarts. For production, consider:
- Persisting to database (PostgreSQL, MongoDB)
- Job queue (Redis, RabbitMQ)
- Task workers (Celery, Huey)
