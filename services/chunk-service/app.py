import os
import logging
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain.text_splitter import RecursiveCharacterTextSplitter

app = Flask(__name__)
CORS(app)

# Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://embedding-service:4004")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "wp_ai_receptionist")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", " ", ""]
)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route("/chunk", methods=["POST"])
def chunk_document():
    """Chunk a document and send to embeddings"""
    try:
        data = request.json
        text = data.get("text")
        doc_id = data.get("doc_id")
        source = data.get("source", "unknown")
        metadata = data.get("metadata", {})
        
        if not text or not doc_id:
            return jsonify({"error": "text and doc_id required"}), 400
        
        logger.info(f"Chunking document: {doc_id} from source: {source}")
        
        # Split text into chunks
        chunks = text_splitter.split_text(text)
        
        if not chunks:
            return jsonify({"error": "No chunks generated"}), 400
        
        logger.info(f"Generated {len(chunks)} chunks from document {doc_id}")
        
        # Prepare chunk batch with metadata
        chunk_batch = []
        for idx, chunk in enumerate(chunks):
            chunk_batch.append({
                "chunk_id": f"{doc_id}_chunk_{idx}",
                "text": chunk,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "source": source,
                "doc_id": doc_id,
                "metadata": {**metadata, "chunk_number": idx}
            })
        
        # Send chunks for embedding
        embedding_response = requests.post(
            f"{EMBEDDING_SERVICE_URL}/embed-batch",
            json={"chunks": chunk_batch}
        )
        
        if embedding_response.status_code != 200:
            logger.error(f"Embedding failed: {embedding_response.text}")
            return jsonify({"error": f"Embedding failed: {embedding_response.text}"}), 500
        
        embed_result = embedding_response.json()
        vectors_created = embed_result.get("vectors_created", len(chunks))
        
        logger.info(f"Successfully created {vectors_created} embeddings for document {doc_id}")
        
        return jsonify({
            "success": True,
            "doc_id": doc_id,
            "chunk_count": len(chunks),
            "vectors_created": vectors_created,
            "source": source
        }), 200
    
    except Exception as e:
        logger.error(f"Error chunking document: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/chunk-info", methods=["GET"])
def chunk_info():
    """Get chunking configuration"""
    return jsonify({
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "splitter_type": "RecursiveCharacterTextSplitter"
    }), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 4003))
    app.run(host="0.0.0.0", port=port, debug=False)
