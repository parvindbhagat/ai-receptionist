import os
import logging
import requests
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from datetime import datetime
import json
import uuid
import threading
from typing import Dict

app = Flask(__name__)
CORS(app)

# Configuration
DOC_PROCESSOR_URL = os.getenv("DOC_PROCESSOR_URL", "http://doc-processor:4001")
CHUNK_SERVICE_URL = os.getenv("CHUNK_SERVICE_URL", "http://chunk-service:4003")
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://embedding-service:4004")
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag-service:4002")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# In-memory job tracker for async operations
job_store: Dict = {}
job_lock = threading.Lock()


@app.route("/health", methods=["GET"])
def health():
    """Health check - check all services"""
    try:
        health_status = {
            "status": "unhealthy",
            "services": {}
        }
        
        services = {
            "doc_processor": DOC_PROCESSOR_URL,
            "chunk_service": CHUNK_SERVICE_URL,
            "embedding_service": EMBEDDING_SERVICE_URL,
            "rag_service": RAG_SERVICE_URL
        }
        
        all_healthy = True
        for service_name, service_url in services.items():
            try:
                response = requests.get(f"{service_url}/health", timeout=5)
                if response.status_code == 200:
                    health_status["services"][service_name] = "healthy"
                else:
                    health_status["services"][service_name] = "unhealthy"
                    all_healthy = False
            except Exception as e:
                logger.warning(f"Service {service_name} unhealthy: {e}")
                health_status["services"][service_name] = "unavailable"
                all_healthy = False
        
        if all_healthy:
            health_status["status"] = "healthy"
            return jsonify(health_status), 200
        else:
            return jsonify(health_status), 503
    
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/ingest/url", methods=["POST"])
def ingest_url():
    """Ingest content from a URL"""
    try:
        data = request.json
        url = data.get("url")

        doc_id = data.get("doc_id")
        
        if not url:
            return jsonify({"error": "url required"}), 400
        
        logger.info(f"Ingesting URL: {url}")
        
        response = requests.post(
            f"{DOC_PROCESSOR_URL}/process-url",
            json={"url": url, "doc_id": doc_id} if doc_id else {"url": url}
        )
        
        return response.json(), response.status_code
    
    except Exception as e:
        logger.error(f"Error ingesting URL: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/ingest/file", methods=["POST"])
def ingest_file():
    """Ingest a file (PDF, DOCX, TXT)"""
    try:
        if "file" not in request.files:
            return jsonify({"error": "file required"}), 400
        
        file = request.files["file"]
        
        logger.info(f"Ingesting file: {file.filename}")
        
        # Create a new request to doc-processor
        files = {"file": (file.filename, file.stream)}
        response = requests.post(
            f"{DOC_PROCESSOR_URL}/process-file",
            files=files
        )
        
        return response.json(), response.status_code
    
    except Exception as e:
        logger.error(f"Error ingesting file: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/query", methods=["POST"])
def query():
    """Query the RAG system"""
    try:
        data = request.json
        user_query = data.get("query")
        
        if not user_query:
            return jsonify({"error": "query required"}), 400
        
        logger.info(f"Processing query: {user_query[:100]}")
        
        response = requests.post(
            f"{RAG_SERVICE_URL}/query",
            json={"query": user_query}
        )
        
        return response.json(), response.status_code
    
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/search", methods=["POST"])
def search():
    """Search knowledge base"""
    try:
        data = request.json
        query = data.get("query")
        limit = data.get("limit", 5)
        threshold = data.get("threshold", 0.7)
        
        if not query:
            return jsonify({"error": "query required"}), 400
        
        logger.info(f"Searching for: {query[:100]}")
        
        response = requests.post(
            f"{RAG_SERVICE_URL}/search",
            json={
                "query": query,
                "limit": limit,
                "threshold": threshold
            }
        )
        
        return response.json(), response.status_code
    
    except Exception as e:
        logger.error(f"Error searching: {e}")
        return jsonify({"error": str(e)}), 500


def process_urls_async(job_id: str, urls: list):
    """Background worker for batch URL ingestion"""
    try:
        job_store[job_id]["status"] = "processing"
        job_store[job_id]["started_at"] = datetime.now().isoformat()
        
        logger.info(f"[Job {job_id}] Starting batch ingestion of {len(urls)} URLs")
        
        for idx, url in enumerate(urls, 1):
            if job_store[job_id].get("cancel_requested"):
                job_store[job_id]["status"] = "cancelled"
                logger.info(f"[Job {job_id}] Cancelled by user")
                break
            
            try:
                if not isinstance(url, str) or not url.strip():
                    job_store[job_id]["results"].append({
                        "index": idx,
                        "url": url,
                        "status": "failed",
                        "error": "Invalid URL format"
                    })
                    job_store[job_id]["failed"] += 1
                    continue
                
                logger.info(f"[Job {job_id}] [{idx}/{len(urls)}] Processing: {url[:80]}")
                job_store[job_id]["current_url"] = url
                job_store[job_id]["current_index"] = idx
                
                response = requests.post(
                    f"{DOC_PROCESSOR_URL}/process-url",
                    json={"url": url},
                    timeout=600  # 10 minute timeout per URL
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    job_store[job_id]["results"].append({
                        "index": idx,
                        "url": url,
                        "status": "success",
                        "doc_id": result_data.get("doc_id"),
                        "chunks_created": result_data.get("chunks_created")
                    })
                    job_store[job_id]["successful"] += 1
                    job_store[job_id]["total_chunks"] += result_data.get("chunks_created", 0)
                else:
                    job_store[job_id]["results"].append({
                        "index": idx,
                        "url": url,
                        "status": "failed",
                        "error": response.json().get("error", "Unknown error")
                    })
                    job_store[job_id]["failed"] += 1
            
            except Exception as e:
                logger.error(f"[Job {job_id}] Error processing URL {idx}: {e}")
                job_store[job_id]["results"].append({
                    "index": idx,
                    "url": url,
                    "status": "failed",
                    "error": str(e)
                })
                job_store[job_id]["failed"] += 1
        
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["completed_at"] = datetime.now().isoformat()
        logger.info(f"[Job {job_id}] Complete: {job_store[job_id]['successful']} successful, {job_store[job_id]['failed']} failed, {job_store[job_id]['total_chunks']} total chunks")
    
    except Exception as e:
        logger.error(f"[Job {job_id}] Unexpected error: {e}")
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = str(e)


@app.route("/ingest/urls", methods=["POST"])
def ingest_urls():
    """Batch ingest multiple URLs as knowledge base (async)"""
    try:
        data = request.json
        urls = data.get("urls", [])
        
        if not urls or not isinstance(urls, list):
            return jsonify({"error": "urls array required"}), 400
        
        if len(urls) == 0:
            return jsonify({"error": "at least one URL required"}), 400
        
        # Create job
        job_id = str(uuid.uuid4())
        
        with job_lock:
            job_store[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "total_urls": len(urls),
                "successful": 0,
                "failed": 0,
                "total_chunks": 0,
                "results": [],
                "current_url": None,
                "current_index": 0,
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "cancel_requested": False
            }
        
        # Start background thread
        thread = threading.Thread(target=process_urls_async, args=(job_id, urls), daemon=True)
        thread.start()
        
        logger.info(f"[Job {job_id}] Created batch ingestion job for {len(urls)} URLs")
        
        return jsonify({
            "job_id": job_id,
            "status": "queued",
            "message": f"Batch ingestion started. Poll /jobs/{job_id}/status for progress"
        }), 202
    
    except Exception as e:
        logger.error(f"Error creating batch ingestion job: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/jobs/<job_id>/status", methods=["GET"])
def get_job_status(job_id):
    """Get status of a batch ingestion job"""
    try:
        if job_id not in job_store:
            return jsonify({"error": "Job not found"}), 404
        
        with job_lock:
            job = dict(job_store[job_id])
        
        return jsonify(job), 200
    
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/jobs/<job_id>/cancel", methods=["POST"])
def cancel_job(job_id):
    """Cancel a running batch ingestion job"""
    try:
        if job_id not in job_store:
            return jsonify({"error": "Job not found"}), 404
        
        with job_lock:
            if job_store[job_id]["status"] in ["completed", "failed", "cancelled"]:
                return jsonify({"error": "Cannot cancel job in terminal state"}), 400
            
            job_store[job_id]["cancel_requested"] = True
        
        return jsonify({"message": "Cancel requested"}), 200
    
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/jobs", methods=["GET"])
def list_jobs():
    """List all batch ingestion jobs"""
    try:
        limit = request.args.get("limit", 10, type=int)
        
        with job_lock:
            jobs = sorted(
                [dict(j) for j in job_store.values()],
                key=lambda x: x["created_at"],
                reverse=True
            )[:limit]
        
        return jsonify({"jobs": jobs, "count": len(jobs)}), 200
    
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/knowledge-base/config", methods=["POST"])
def save_knowledge_base_config():
    """Save knowledge base configuration for later reference"""
    try:
        data = request.json
        name = data.get("name")
        description = data.get("description", "")
        urls = data.get("urls", [])
        
        if not name or not urls:
            return jsonify({"error": "name and urls required"}), 400
        
        config = {
            "id": f"kb_{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}",
            "name": name,
            "description": description,
            "urls": urls,
            "created_at": datetime.now().isoformat(),
            "total_urls": len(urls)
        }
        
        logger.info(f"Knowledge base config saved: {config['id']}")
        
        return jsonify({
            "success": True,
            "config": config,
            "next_step": "Use POST /ingest/urls with this same urls array to build the knowledge base"
        }), 200
    
    except Exception as e:
        logger.error(f"Error saving knowledge base config: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/status", methods=["GET"])
def status():
    """Get system status and configuration"""
    try:
        rag_config = requests.get(f"{RAG_SERVICE_URL}/config").json()
        chunk_info = requests.get(f"{CHUNK_SERVICE_URL}/chunk-info").json()
        embed_info = requests.get(f"{EMBEDDING_SERVICE_URL}/embedding-info").json()
        
        return jsonify({
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "rag_config": rag_config,
            "chunk_config": chunk_info,
            "embedding_config": embed_info,
            "services": {
                "doc_processor": DOC_PROCESSOR_URL,
                "chunk_service": CHUNK_SERVICE_URL,
                "embedding_service": EMBEDDING_SERVICE_URL,
                "rag_service": RAG_SERVICE_URL
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def index():
    """API documentation"""
    return jsonify({
        "name": "RAG System API Gateway",
        "version": "1.0.0",
        "note": "Batch ingestion is now ASYNC - submit job, then poll status",
        "endpoints": {
            "GET": {
                "/health": "Check health of all services",
                "/status": "Get system status and configuration",
                "/jobs": "List all batch ingestion jobs",
                "/jobs/{job_id}/status": "Get status of a specific job"
            },
            "POST": {
                "/ingest/url": "Ingest single URL (blocking)",
                "/ingest/urls": "**ASYNC** Batch ingest multiple URLs - returns job_id",
                "/ingest/file": "Ingest file (PDF, DOCX, TXT)",
                "/query": "Query the knowledge base and get answer",
                "/search": "Search knowledge base for relevant chunks",
                "/knowledge-base/config": "Save knowledge base configuration",
                "/jobs/{job_id}/cancel": "Cancel a running job"
            }
        },
        "async_batch_ingestion_workflow": {
            "step_1_submit": {
                "method": "POST",
                "endpoint": "/ingest/urls",
                "body": {
                    "urls": [
                        "https://chrysalis.in/our-services/learning-consulting/",
                        "https://chrysalis.in/our-services/leadership-development/",
                        "https://chrysalis.in/our-services/learning-technology-solutions/",
                        "https://chrysalis.in/our-services/"
                    ]
                },
                "response": {
                    "job_id": "uuid-string",
                    "status": "queued",
                    "message": "Batch ingestion started. Poll /jobs/{job_id}/status for progress"
                },
                "http_code": 202
            },
            "step_2_poll_status": {
                "method": "GET",
                "endpoint": "/jobs/{job_id}/status",
                "response": {
                    "job_id": "uuid-string",
                    "status": "processing|completed|failed|cancelled",
                    "total_urls": 3,
                    "successful": 2,
                    "failed": 0,
                    "total_chunks": 430,
                    "current_url": "https://en.wikipedia.org/wiki/Machine_learning",
                    "current_index": 2,
                    "results": [
                        {
                            "index": 1,
                            "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
                            "status": "success",
                            "chunks_created": 268
                        }
                    ],
                    "created_at": "2026-03-18T08:00:00",
                    "started_at": "2026-03-18T08:01:00",
                    "completed_at": None
                }
            },
            "step_3_view_all_jobs": {
                "method": "GET",
                "endpoint": "/jobs?limit=10",
                "returns": "List of latest batch ingestion jobs with status"
            }
        },
        "performance_notes": {
            "time_per_url": "~3-5 minutes per Wikipedia article",
            "time_per_chunk": "~1 second per chunk (embedded vector storage)",
            "recommendation": "Ingest 3-5 URLs per job, larger articles may take 10-15 minutes",
            "monitoring": "Poll /jobs/{job_id}/status every 10-30 seconds"
        }
    }), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False)
