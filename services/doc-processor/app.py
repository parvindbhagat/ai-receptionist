import os
import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime
import json
from pathlib import Path

# Document processing imports
try:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.partition.docx import partition_docx
except ImportError:
    partition_pdf = None
    partition_docx = None

from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "/tmp/uploads")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 52428800))  # 50MB
CHUNK_SERVICE_URL = os.getenv("CHUNK_SERVICE_URL", "http://chunk-service:4003")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Setup logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'doc'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(filepath):
    """Extract text from PDF file"""
    try:
        if partition_pdf is None:
            logger.warning("unstructured not available, using basic PDF extraction")
            # Fallback to PyPDF2
            import PyPDF2
            text = ""
            with open(filepath, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            return text
        else:
            elements = partition_pdf(filepath)
            return "\n".join([str(el) for el in elements])
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        raise


def extract_text_from_docx(filepath):
    """Extract text from DOCX file"""
    try:
        if partition_docx is None:
            from docx import Document
            doc = Document(filepath)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        else:
            elements = partition_docx(filepath)
            return "\n".join([str(el) for el in elements])
    except Exception as e:
        logger.error(f"Error extracting DOCX text: {e}")
        raise


def extract_text_from_url(url):
    """Extract text from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text(separator="\n")
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        logger.error(f"Error extracting text from URL: {e}")
        raise


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route("/process-url", methods=["POST"])
def process_url():
    """Process a URL and extract its content"""
    try:
        data = request.json
        url = data.get("url")
        doc_id = data.get("doc_id", f"url_{datetime.now().timestamp()}")
        
        if not url:
            return jsonify({"error": "URL required"}), 400
        
        logger.info(f"Processing URL: {url}")
        text = extract_text_from_url(url)
        
        # Send to chunk service
        chunk_response = requests.post(
            f"{CHUNK_SERVICE_URL}/chunk",
            json={
                "text": text,
                "doc_id": doc_id,
                "source": url,
                "metadata": {"type": "url", "url": url}
            }
        )
        
        if chunk_response.status_code != 200:
            return jsonify({"error": f"Chunking failed: {chunk_response.text}"}), 500
        
        return jsonify({
            "success": True,
            "doc_id": doc_id,
            "source": url,
            "chunks_created": chunk_response.json().get("chunk_count", 0)
        }), 200
    
    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/process-file", methods=["POST"])
def process_file():
    """Process uploaded file"""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": f"File type not allowed. Allowed: {ALLOWED_EXTENSIONS}"}), 400
        
        if len(file.read()) > MAX_FILE_SIZE:
            return jsonify({"error": f"File too large. Max: {MAX_FILE_SIZE} bytes"}), 400
        
        file.seek(0)  # Reset file pointer
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        logger.info(f"Processing file: {filename}")
        
        # Extract text based on file type
        file_ext = filename.rsplit('.', 1)[1].lower()
        
        if file_ext == 'pdf':
            text = extract_text_from_pdf(filepath)
        elif file_ext in ['docx', 'doc']:
            text = extract_text_from_docx(filepath)
        else:  # txt
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
        
        doc_id = f"file_{filename}_{datetime.now().timestamp()}"
        
        # Send to chunk service
        chunk_response = requests.post(
            f"{CHUNK_SERVICE_URL}/chunk",
            json={
                "text": text,
                "doc_id": doc_id,
                "source": filename,
                "metadata": {"type": "file", "filename": filename, "file_path": filepath}
            }
        )
        
        if chunk_response.status_code != 200:
            return jsonify({"error": f"Chunking failed: {chunk_response.text}"}), 500
        
        return jsonify({
            "success": True,
            "doc_id": doc_id,
            "filename": filename,
            "chunks_created": chunk_response.json().get("chunk_count", 0)
        }), 200
    
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/status/<doc_id>", methods=["GET"])
def get_status(doc_id):
    """Check processing status of a document"""
    try:
        return jsonify({
            "doc_id": doc_id,
            "status": "processing"
        }), 200
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 4001))
    app.run(host="0.0.0.0", port=port, debug=False)
