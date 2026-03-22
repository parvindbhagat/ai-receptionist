import os
import logging
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

app = Flask(__name__)
CORS(app)

# Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "wp_ai_receptionist")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 32))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize Qdrant client
qdrant_client = QdrantClient(url=QDRANT_URL)
EMBEDDING_DIMENSION = 768  # Adjust based on your embedding model


def get_embedding(text):
    """Get embedding from Ollama"""
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embed",
            json={
                "model": EMBEDDING_MODEL,
                "input": text
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        embeddings = result.get("embeddings", [])
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
        return None
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        return None


def ensure_collection_exists():
    """Ensure Qdrant collection exists"""
    try:
        collections = qdrant_client.get_collections().collections
        if not any(c.name == QDRANT_COLLECTION for c in collections):
            logger.info(f"Creating collection: {QDRANT_COLLECTION}")
            qdrant_client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE),
            )
    except Exception as e:
        logger.error(f"Error ensuring collection exists: {e}")
        raise


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    try:
        ensure_collection_exists()
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/embed", methods=["POST"])
def embed_text():
    """Embed a single text"""
    try:
        data = request.json
        text = data.get("text")
        
        if not text:
            return jsonify({"error": "text required"}), 400
        
        embedding = get_embedding(text)
        
        if not embedding:
            return jsonify({"error": "Failed to generate embedding"}), 500
        
        return jsonify({
            "success": True,
            "text": text[:100] + "..." if len(text) > 100 else text,
            "embedding_dim": len(embedding)
        }), 200
    
    except Exception as e:
        logger.error(f"Error embedding text: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/embed-batch", methods=["POST"])
def embed_batch():
    """Embed batch of chunks and store in Qdrant"""
    try:
        ensure_collection_exists()
        
        data = request.json
        chunks = data.get("chunks", [])
        
        if not chunks:
            return jsonify({"error": "chunks required"}), 400
        
        logger.info(f"Processing batch of {len(chunks)} chunks")
        
        points = []
        successful = 0
        
        for chunk in chunks:
            try:
                text = chunk.get("text")
                chunk_id = chunk.get("chunk_id")
                
                if not text or not chunk_id:
                    logger.warning(f"Skipping chunk with missing text or id: {chunk}")
                    continue
                
                # Get embedding
                embedding = get_embedding(text)
                if not embedding:
                    logger.warning(f"Failed to get embedding for chunk: {chunk_id}")
                    continue
                
                # Create point for Qdrant
                point = PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id)),
                    vector=embedding,
                    payload={
                        "chunk_id": chunk_id,
                        "text": text,
                        "source": chunk.get("source", ""),
                        "doc_id": chunk.get("doc_id", ""),
                        "chunk_index": chunk.get("chunk_index", 0),
                        "metadata": chunk.get("metadata", {})
                    }
                )
                points.append(point)
                successful += 1
                
                if len(points) >= BATCH_SIZE:
                    # Upsert batch to Qdrant
                    qdrant_client.upsert(
                        collection_name=QDRANT_COLLECTION,
                        points=points
                    )
                    logger.info(f"Upserted {len(points)} vectors to Qdrant")
                    points = []
            
            except Exception as e:
                logger.error(f"Error processing chunk {chunk.get('chunk_id')}: {e}")
                continue
        
        # Upsert remaining points
        if points:
            qdrant_client.upsert(
                collection_name=QDRANT_COLLECTION,
                points=points
            )
            logger.info(f"Upserted {len(points)} vectors to Qdrant")
        
        logger.info(f"Successfully embedded {successful}/{len(chunks)} chunks")
        
        return jsonify({
            "success": True,
            "vectors_created": successful,
            "total_chunks": len(chunks),
            "collection": QDRANT_COLLECTION,
            "embedding_model": EMBEDDING_MODEL
        }), 200
    
    except Exception as e:
        logger.error(f"Error in embedding batch: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/embedding-info", methods=["GET"])
def embedding_info():
    """Get embedding model info"""
    try:
        return jsonify({
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dim": EMBEDDING_DIMENSION,
            "ollama_url": OLLAMA_BASE_URL,
            "qdrant_url": QDRANT_URL,
            "collection": QDRANT_COLLECTION
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 4004))
    app.run(host="0.0.0.0", port=port, debug=False)
