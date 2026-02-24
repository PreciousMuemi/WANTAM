#!/usr/bin/env python3
"""
Re-embed existing chunks with Gemini embeddings
Reads chunks from extracted_chunks/chunks.json and stores with Gemini embeddings
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from tqdm import tqdm
from supabase import create_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def load_chunks(json_path: str = "extracted_chunks/chunks.json") -> List[Dict[str, Any]]:
    """Load chunks from JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        logger.info(f"Loaded {len(chunks)} chunks from {json_path}")
        return chunks
    except FileNotFoundError:
        logger.error(f"Chunk file not found: {json_path}")
        return []

def generate_embeddings_gemini(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate Gemini embeddings for chunks."""
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set")
        return []
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
    except ImportError:
        logger.error("google-generativeai not installed. Run: pip install google-generativeai")
        return []
    
    embedded_chunks = []
    
    for chunk in tqdm(chunks, desc="Generating Gemini embeddings"):
        try:
            # Generate embedding
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=chunk['text']
            )
            embedding = result['embedding']
            
            # Add embedding to chunk
            chunk['embedding'] = embedding
            embedded_chunks.append(chunk)
        
        except Exception as e:
            logger.error(f"Error embedding chunk {chunk.get('chunk_id')}: {e}")
            continue
    
    logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")
    return embedded_chunks

def upload_to_supabase(chunks: List[Dict[str, Any]]) -> bool:
    """Upload embedded chunks to Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase credentials not set")
        return False
    
    if not chunks:
        logger.error("No chunks to upload")
        return False
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Batch insert
        batch_size = 100
        for i in tqdm(range(0, len(chunks), batch_size), desc="Uploading to Supabase"):
            batch = chunks[i:i + batch_size]
            
            # Prepare data for Supabase
            records = []
            for chunk in batch:
                records.append({
                    'source_url': chunk.get('source_url'),
                    'document_title': chunk.get('document_title'),
                    'chunk_id': chunk.get('chunk_id'),
                    'text': chunk.get('text'),
                    'page_number': chunk.get('page_number'),
                    'token_count': chunk.get('token_count'),
                    'embedding': chunk.get('embedding')
                })
            
            supabase.table("documents").insert(records).execute()
            logger.info(f"Uploaded batch {i//batch_size + 1}")
        
        logger.info(f"Successfully uploaded {len(chunks)} embedded chunks to Supabase")
        return True
    
    except Exception as e:
        logger.error(f"Error uploading to Supabase: {e}")
        return False

def main():
    """Main pipeline."""
    print("=" * 60)
    print("Re-embedding Chunks with Gemini")
    print("=" * 60)
    
    # Load chunks
    print("\n[1/3] Loading chunks from JSON...")
    chunks = load_chunks()
    if not chunks:
        logger.error("No chunks to process")
        return False
    
    # Generate embeddings
    print("\n[2/3] Generating Gemini embeddings...")
    embedded_chunks = generate_embeddings_gemini(chunks)
    if not embedded_chunks:
        logger.error("Failed to generate embeddings")
        return False
    
    # Upload to Supabase
    print("\n[3/3] Uploading to Supabase...")
    success = upload_to_supabase(embedded_chunks)
    
    print("\n" + "=" * 60)
    if success:
        print("SUCCESS! Chunks re-embedded and uploaded.")
        print(f"Total: {len(embedded_chunks)} chunks with 3072-dim Gemini embeddings")
    else:
        print("FAILED! Check logs above for errors.")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    main()
