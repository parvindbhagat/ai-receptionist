import os
import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from qdrant_client import QdrantClient
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configuration
PROVIDER = os.getenv("PROVIDER", "ollama")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
CHAT_MODEL = os.getenv("CHAT_MODEL", "mistral:7b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "wp_ai_receptionist")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.5))  # Lowered from 0.7 for better recall
SIMILARITY_THRESHOLD_RELAXED = float(os.getenv("SIMILARITY_THRESHOLD_RELAXED", 0.4))  # For fallback searches
MAX_CONTEXT_CHUNKS = int(os.getenv("MAX_CONTEXT_CHUNKS", 7))  # Increased from 5
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize Qdrant client
qdrant_client = QdrantClient(url=QDRANT_URL)


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


def expand_query(query):
    """Expand query with related terms to help with semantic matching"""
    # Common problem-to-solution mappings
    expansions = {
        "leadership": "leadership development training program organizational transformation",
        "develop": "development learning solution training framework",
        "train": "training program development learning solution",
        "skill": "skill development upskilling training program",
        "performance": "performance improvement development training",
        "culture": "culture transformation organizational development learning",
        "onboard": "onboarding employee development learning program",
        "engagement": "engagement learning experience interactive training",
        "succession": "succession planning leadership development organizational",
        "team": "team building development collaboration learning",
        "capability": "capability building development training solution",
        "transformation": "organizational transformation development learning innovation",
        "coaching": "coaching mentoring development guidance support",
        "learning": "learning development training program solution"
    }
    
    expanded = query
    query_lower = query.lower()
    
    for key, value in expansions.items():
        if key in query_lower:
            expanded = f"{query} {value}"
            break
    
    return expanded


def search_knowledge_base(query):
    """Search Qdrant for relevant chunks using REST API with fallback strategy"""
    try:
        # Expand query to include related terms
        expanded_query = expand_query(query)
        
        # Get query embedding
        query_embedding = get_embedding(expanded_query)
        if not query_embedding:
            return []
        
        # First search with standard threshold
        search_payload = {
            "vector": query_embedding,
            "limit": MAX_CONTEXT_CHUNKS,
            "score_threshold": SIMILARITY_THRESHOLD,
            "with_payload": True
        }
        
        response = requests.post(
            f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points/search",
            json=search_payload,
            timeout=30
        )
        response.raise_for_status()
        search_result = response.json()
        
        results = []
        for point in search_result.get("result", []):
            payload = point.get("payload", {})
            results.append({
                "chunk_id": payload.get("chunk_id"),
                "text": payload.get("text"),
                "source": payload.get("source"),
                "score": point.get("score")
            })
        
        # If no results found, try with relaxed threshold (fallback search)
        if not results:
            logger.info(f"No results with threshold {SIMILARITY_THRESHOLD}, trying with relaxed threshold {SIMILARITY_THRESHOLD_RELAXED}")
            search_payload["score_threshold"] = SIMILARITY_THRESHOLD_RELAXED
            search_payload["limit"] = MAX_CONTEXT_CHUNKS + 3
            
            response = requests.post(
                f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points/search",
                json=search_payload,
                timeout=30
            )
            response.raise_for_status()
            search_result = response.json()
            
            for point in search_result.get("result", []):
                payload = point.get("payload", {})
                results.append({
                    "chunk_id": payload.get("chunk_id"),
                    "text": payload.get("text"),
                    "source": payload.get("source"),
                    "score": point.get("score")
                })
        
        return results
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        return []


def generate_response(query, context_chunks):
    """Generate response using local LLM via chat endpoint"""
    try:
        # Build context from chunks - frame it as company knowledge base, not as separate context
        knowledge_base = "\n\n".join([c['text'] for c in context_chunks])
        
        user_message = f"""{query}"""
        
        # Call Ollama chat endpoint (more reliable than /api/generate)
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": CHAT_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": """You are a warm, professional, and knowledgeable digital receptionist for Chrysalis HRD. You represent the company with pride and ownership.

About Chrysalis HRD: We are a Learning and Development company based in India, pioneering 'Results Based Learning' where we drive organizational transformation through innovative learning solutions. We own our expertise and speak with confidence about what we offer.

YOUR THINKING PROCESS:
When someone asks about a business problem or challenge (e.g., "How can you help with X?"):
1. Identify what they're asking for (e.g., "leadership development")
2. Find the SOLUTION we offer that addresses this problem
3. Connect their need to our services with confidence
4. Explain HOW we solve this problem, not just WHAT we do

IMPORTANT GUIDELINES:
1. Speak AS an employee of Chrysalis HRD using "we" and "our" - own the information and services
2. Answer naturally and conversationally, without referencing or acknowledging any "context"
3. Use phrases like "We at Chrysalis...", "Our approach...", "We help organizations...", "Our framework..."
4. When someone asks about a business need, confidently explain how we solve it
5. Provide specific, detailed responses that demonstrate company knowledge and expertise
6. If you don't know the answer, politely say you'd like to connect them with the right team member
7. Keep responses warm, professional, and solution-focused
8. Do NOT mention sources, documents, or that you're referencing "information"
9. Be specific about frameworks, methodologies, and approaches we use
10. Emphasize our Results Based Learning philosophy and how it drives organizational transformation

KNOWLEDGE BASE OF OUR SERVICES AND SOLUTIONS:
""" + knowledge_base
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                "stream": False
            },
            timeout=600
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("message", {}).get("content", "")
    
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return f"Error generating response: {str(e)}"


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    try:
        # Check Ollama
        ollama_health = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        # Check Qdrant
        qdrant_client.get_collections()
        
        return jsonify({
            "status": "healthy",
            "provider": PROVIDER,
            "chat_model": CHAT_MODEL,
            "embedding_model": EMBEDDING_MODEL
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/query", methods=["POST"])
def query():
    """Query the RAG system"""
    try:
        data = request.json
        user_query = data.get("query")
        metadata_filter = data.get("metadata_filter", {})
        
        if not user_query:
            return jsonify({"error": "query required"}), 400
        
        logger.info(f"Processing query: {user_query[:100]}")
        
        # Search knowledge base
        relevant_chunks = search_knowledge_base(user_query)
        
        # Always try to generate a response, even with limited context
        # The model can provide general company guidance
        if not relevant_chunks:
            logger.info(f"No relevant chunks found for query: {user_query}")
            # Create a minimal context to let the model respond based on its instructions
            relevant_chunks = []
        
        # Generate response
        answer = generate_response(user_query, relevant_chunks)
        
        return jsonify({
            "query": user_query,
            "answer": answer,
            "context_chunks": relevant_chunks,
            "model": CHAT_MODEL,
            "timestamp": datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/search", methods=["POST"])
def search():
    """Search knowledge base without generating response"""
    try:
        data = request.json
        query = data.get("query")
        limit = data.get("limit", MAX_CONTEXT_CHUNKS)
        threshold = data.get("threshold", SIMILARITY_THRESHOLD)
        
        if not query:
            return jsonify({"error": "query required"}), 400
        
        logger.info(f"Searching for: {query[:100]}")
        
        # Expand query for better semantic matching
        expanded_query = expand_query(query)
        
        # Get query embedding
        query_embedding = get_embedding(expanded_query)
        if not query_embedding:
            return jsonify({"error": "Failed to generate query embedding"}), 500
        
        # Search Qdrant
        search_result = qdrant_client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=threshold
        )
        
        results = []
        for point in search_result:
            results.append({
                "chunk_id": point.payload.get("chunk_id"),
                "text": point.payload.get("text"),
                "source": point.payload.get("source"),
                "doc_id": point.payload.get("doc_id"),
                "score": point.score,
                "metadata": point.payload.get("metadata", {})
            })
        
        return jsonify({
            "query": query,
            "results": results,
            "result_count": len(results),
            "timestamp": datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error searching: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/config", methods=["GET"])
def config():
    """Get RAG configuration"""
    return jsonify({
        "provider": PROVIDER,
        "chat_model": CHAT_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "similarity_threshold_relaxed": SIMILARITY_THRESHOLD_RELAXED,
        "max_context_chunks": MAX_CONTEXT_CHUNKS,
        "qdrant_collection": QDRANT_COLLECTION
    }), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 4002))
    app.run(host="0.0.0.0", port=port, debug=False)
