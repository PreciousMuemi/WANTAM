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

def generate_embeddings_gemini(chunks: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate Gemini embeddings for chunks.

    Returns (embedded_chunks, remaining_chunks).
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set")
        return [], []
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
    except ImportError:
        logger.error("google-generativeai not installed. Run: pip install google-generativeai")
        return [], []
    
    embedded_chunks: List[Dict[str, Any]] = []
    remaining_chunks: List[Dict[str, Any]] = []
    
    for index, chunk in enumerate(tqdm(chunks, desc="Generating Gemini embeddings")):
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
            message = str(e)
            logger.error(f"Error embedding chunk {chunk.get('chunk_id')}: {e}")
            if "429" in message or "quota" in message.lower():
                logger.error("Quota exceeded. Stopping early to avoid partial uploads.")
                remaining_chunks = chunks[index:]
                break
            continue
    
    logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")
    return embedded_chunks, remaining_chunks

def _delete_existing_for_sources(supabase, source_urls: List[str]) -> None:
    """Delete existing rows for the provided source URLs to avoid duplicates."""
    if not source_urls:
        return
    batch_size = 50
    for i in range(0, len(source_urls), batch_size):
        batch = source_urls[i:i + batch_size]
        supabase.table("documents").delete().in_("source_url", batch).execute()
        logger.info(f"Deleted existing rows for {len(batch)} source URLs")


def upload_to_supabase(chunks: List[Dict[str, Any]], source_urls: List[str]) -> bool:
    """Upload embedded chunks to Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase credentials not set")
        return False
    
    if not chunks:
        logger.error("No chunks to upload")
        return False
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Remove existing rows for these source URLs to avoid duplicates
        _delete_existing_for_sources(supabase, source_urls)
        
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
    chunks_file = os.getenv("CHUNKS_FILE", "extracted_chunks/chunks.json")
    chunks = load_chunks(chunks_file)
    if not chunks:
        logger.error("No chunks to process")
        return False

    # Optional filter by source URL substring(s)
    source_filter = os.getenv("EMBED_SOURCE_FILTER", "").strip()
    if source_filter:
        filters = [s.strip().lower() for s in source_filter.split(",") if s.strip()]
        filtered = []
        for c in chunks:
            url = (c.get("source_url") or "").lower()
            if any(f in url for f in filters):
                filtered.append(c)
        logger.info(f"Filtered chunks by EMBED_SOURCE_FILTER ({filters}): {len(filtered)} of {len(chunks)}")
        chunks = filtered
    
    # Generate embeddings
    print("\n[2/3] Generating Gemini embeddings...")
    embedded_chunks, remaining_chunks = generate_embeddings_gemini(chunks)
    if not embedded_chunks:
        logger.error("Failed to generate embeddings")
        return False
    
    # Upload to Supabase
    print("\n[3/3] Uploading to Supabase...")
    # Avoid uploading partial documents if we hit quota
    embedded_sources = {c.get('source_url') for c in embedded_chunks if c.get('source_url')}
    remaining_sources = {c.get('source_url') for c in remaining_chunks if c.get('source_url')}
    complete_sources = sorted(embedded_sources - remaining_sources)

    upload_chunks = [c for c in embedded_chunks if c.get('source_url') in complete_sources]

    if remaining_chunks:
        pending_chunks = remaining_chunks + [c for c in embedded_chunks if c.get('source_url') in remaining_sources]
        pending_path = Path("extracted_chunks/pending_chunks.json")
        with open(pending_path, "w", encoding="utf-8") as f:
            json.dump(pending_chunks, f, ensure_ascii=False, indent=2)
        logger.warning(f"Saved {len(pending_chunks)} pending chunks to {pending_path}")

    if not upload_chunks:
        logger.error("No complete documents to upload (quota likely exceeded).")
        return False

    success = upload_to_supabase(upload_chunks, complete_sources)
    
    print("\n" + "=" * 60)
    if success:
        print("SUCCESS! Chunks re-embedded and uploaded.")
        print(f"Total: {len(upload_chunks)} chunks with 3072-dim Gemini embeddings")
    else:
        print("FAILED! Check logs above for errors.")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    main()
