"""
PDF Scraper for kenyalaw.org
Downloads PDFs, extracts text, chunks content, and stores in Supabase.
"""

import os
import json
import requests
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from urllib.parse import urljoin, urlparse
import re

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from io import BytesIO
import tiktoken
from tqdm import tqdm
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
KENYALAW_BASE_URL = "https://kenyalaw.org/kl/"
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
TESSERACT_PATH = os.getenv("TESSERACT_PATH", None)  # Set if Tesseract not in PATH

CHUNK_SIZE_TOKENS = 500
OVERLAP_TOKENS = 50
ENCODING_MODEL = "cl100k_base"  # For GPT-3.5/4

# Create output directory
OUTPUT_DIR = Path("./extracted_chunks")
OUTPUT_DIR.mkdir(exist_ok=True)


class PDFProcessor:
    """Handles PDF processing, text extraction, and chunking."""
    
    def __init__(self):
        self.tokenizer = tiktoken.get_encoding(ENCODING_MODEL)
        if TESSERACT_PATH:
            pytesseract.pytesseract.pytesseract_cmd = TESSERACT_PATH
    
    def is_scanned_pdf(self, pdf_path: str) -> bool:
        """Check if PDF is scanned (image-based) by analyzing text extraction."""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            # Check first few pages
            for page_num in range(min(3, len(doc))):
                page = doc[page_num]
                text += page.get_text()
            doc.close()
            # If less than 10% alphanumeric characters, likely scanned
            alphanumeric = sum(1 for c in text if c.isalnum())
            return (alphanumeric / max(len(text), 1)) < 0.1
        except Exception as e:
            logger.warning(f"Error checking if PDF is scanned: {e}")
            return False
    
    def extract_text_with_fitz(self, pdf_path: str) -> Dict[int, str]:
        """Extract text from PDF using PyMuPDF."""
        text_by_page = {}
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_by_page[page_num] = text
            doc.close()
            return text_by_page
        except Exception as e:
            logger.error(f"Error extracting text with PyMuPDF: {e}")
            return {}
    
    def extract_text_with_ocr(self, pdf_path: str) -> Dict[int, str]:
        """Extract text from scanned PDF using Tesseract OCR."""
        text_by_page = {}
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    # Convert PDF page to image
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Run OCR
                    text = pytesseract.image_to_string(image)
                    if text.strip():
                        text_by_page[page_num] = text
                except Exception as page_error:
                    logger.warning(f"Error processing page {page_num} with OCR: {page_error}")
            doc.close()
            return text_by_page
        except Exception as e:
            logger.error(f"Error extracting text with OCR: {e}")
            return {}
    
    def extract_text(self, pdf_path: str) -> Dict[int, str]:
        """Extract text from PDF, with OCR fallback for scanned documents."""
        logger.info(f"Checking PDF type: {pdf_path}")
        
        text_by_page = self.extract_text_with_fitz(pdf_path)
        
        # If very little text extracted, try OCR
        total_text_length = sum(len(text) for text in text_by_page.values())
        if total_text_length < 100 or self.is_scanned_pdf(pdf_path):
            logger.info(f"PDF appears to be scanned, using OCR: {pdf_path}")
            text_by_page = self.extract_text_with_ocr(pdf_path)
        
        return text_by_page
    
    def chunk_text(self, text: str, page_number: int) -> List[Dict[str, Any]]:
        """
        Split text into chunks with token overlap.
        
        Returns list of chunk dicts with page info.
        """
        # Tokenize
        tokens = self.tokenizer.encode(text)
        chunks = []
        
        start_idx = 0
        chunk_id = 0
        
        while start_idx < len(tokens):
            end_idx = min(start_idx + CHUNK_SIZE_TOKENS, len(tokens))
            chunk_tokens = tokens[start_idx:end_idx]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "page_number": page_number,
                "token_count": len(chunk_tokens)
            })
            
            # Move start index by chunk size minus overlap
            start_idx += CHUNK_SIZE_TOKENS - OVERLAP_TOKENS
            chunk_id += 1
        
        return chunks
    
    def process_pdf(self, pdf_path: str, source_url: str, document_title: str) -> List[Dict[str, Any]]:
        """Process PDF and return list of chunks with metadata."""
        logger.info(f"Processing PDF: {document_title}")
        
        all_chunks = []
        text_by_page = self.extract_text(pdf_path)
        
        if not text_by_page:
            logger.warning(f"No text extracted from {document_title}")
            return []
        
        global_chunk_id = 0
        for page_num, text in sorted(text_by_page.items()):
            page_chunks = self.chunk_text(text, page_num)
            
            for chunk in page_chunks:
                all_chunks.append({
                    "source_url": source_url,
                    "document_title": document_title,
                    "chunk_id": global_chunk_id,
                    "text": chunk["text"],
                    "page_number": chunk["page_number"],
                    "token_count": chunk["token_count"]
                })
                global_chunk_id += 1
        
        logger.info(f"Created {len(all_chunks)} chunks from {document_title}")
        return all_chunks


class PDFDownloader:
    """Handles downloading PDFs from URLs."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def download_pdf(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Download PDF from URL and return local path."""
        try:
            logger.info(f"Downloading: {url}")
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Generate filename if not provided
            if not filename:
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path) or "document.pdf"
                # Ensure .pdf extension
                if not filename.lower().endswith('.pdf'):
                    filename += '.pdf'
            
            filepath = OUTPUT_DIR / filename
            
            # Download with progress
            total_size = int(response.headers.get('content-length', 0))
            with open(filepath, 'wb') as f:
                if total_size > 0:
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc=filename) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            pbar.update(len(chunk))
                else:
                    f.write(response.content)
            
            logger.info(f"Downloaded to: {filepath}")
            return str(filepath)
        
        except requests.RequestException as e:
            logger.error(f"Error downloading {url}: {e}")
            return None
    
    def close(self):
        """Close session."""
        self.session.close()


class SupabaseManager:
    """Handles Supabase operations."""
    
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables required")
        
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self._ensure_table()
    
    def _ensure_table(self):
        """Ensure documents table exists."""
        try:
            # Try to query the table to check if it exists
            self.client.table("documents").select("COUNT(*)").limit(1).execute()
            logger.info("Documents table exists")
        except Exception as e:
            logger.warning(f"Table check failed: {e}")
    
    def insert_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """Insert chunks into Supabase."""
        if not chunks:
            return True
        
        try:
            # Supabase has a batch insert limit, process in batches
            batch_size = 1000
            for i in tqdm(range(0, len(chunks), batch_size), desc="Uploading chunks"):
                batch = chunks[i:i + batch_size]
                response = self.client.table("documents").insert(batch).execute()
                logger.info(f"Inserted batch of {len(batch)} chunks")
            
            logger.info(f"Successfully uploaded {len(chunks)} chunks to Supabase")
            return True
        
        except Exception as e:
            logger.error(f"Error inserting chunks to Supabase: {e}")
            return False
    
    def check_existing_url(self, source_url: str) -> bool:
        """Check if URL already exists in database."""
        try:
            response = self.client.table("documents").select("source_url").eq(
                "source_url", source_url
            ).limit(1).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.warning(f"Error checking existing URL: {e}")
            return False


def fetch_pdf_urls_from_kenyalaw() -> List[tuple[str, str]]:
    """
    Fetch PDF URLs from kenyalaw.org.
    Returns list of (url, title) tuples.
    
    Note: You may need to customize this based on the actual structure of kenyalaw.org
    """
    pdf_urls = []
    
    try:
        logger.info("Fetching PDF list from kenyalaw.org")
        response = requests.get(KENYALAW_BASE_URL, timeout=30)
        response.raise_for_status()
        
        # Find all PDF links (adjust pattern based on actual HTML structure)
        # This is a basic example - adapt based on actual kenyalaw.org structure
        pdf_pattern = r'href=(["\'])([^"\']*\.pdf[^"\']*)\1[^>]*>([^<]+)<'
        matches = re.findall(pdf_pattern, response.text, re.IGNORECASE)
        
        for _, url, title in matches:
            full_url = urljoin(KENYALAW_BASE_URL, url)
            pdf_urls.append((full_url, title.strip()))
        
        logger.info(f"Found {len(pdf_urls)} PDF URLs")
        return pdf_urls
    
    except Exception as e:
        logger.error(f"Error fetching PDF URLs: {e}")
        return []


def load_pdf_urls_from_file(file_path: str) -> List[tuple[str, str]]:
    """
    Load PDF URLs from a local file.

    Format per line:
    - url
    - url|Title of Document
    Lines starting with # are ignored.
    """
    urls: List[tuple[str, str]] = []
    path = Path(file_path)
    if not path.exists():
        return urls

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" in line:
                    url, title = line.split("|", 1)
                    urls.append((url.strip(), title.strip()))
                else:
                    urls.append((line, "Untitled Document"))
        return urls
    except Exception as e:
        logger.error(f"Error reading PDF URLs file {file_path}: {e}")
        return []


def load_local_pdfs(local_dir: str) -> List[tuple[str, str]]:
    """
    Load local PDF file paths from a directory.
    Returns list of (file_path, title).
    """
    paths: List[tuple[str, str]] = []
    folder = Path(local_dir)
    if not folder.exists() or not folder.is_dir():
        return paths

    for pdf in sorted(folder.glob("*.pdf")):
        title = pdf.stem.replace("_", " ")
        paths.append((str(pdf), title))
    return paths


def main():
    """Main processing pipeline."""
    
    # Initialize components
    downloader = PDFDownloader()
    processor = PDFProcessor()
    
    try:
        supabase_manager = SupabaseManager()
        use_supabase = True
    except ValueError as e:
        logger.warning(f"Supabase not configured: {e}. Saving to JSON only.")
        use_supabase = False
    
    # Collect PDFs from all sources
    pdf_urls = []
    
    # 1. Check local PDF directory first (highest priority)
    local_dir = os.getenv("PDF_LOCAL_DIR", "")
    if local_dir:
        local_pdfs = load_local_pdfs(local_dir)
        pdf_urls.extend(local_pdfs)
        logger.info(f"Found {len(local_pdfs)} PDFs in local directory")
    
    # 2. Add PDFs from URLs file
    urls_file = os.getenv("PDF_URLS_FILE", "pdf_urls.txt")
    file_urls = load_pdf_urls_from_file(urls_file)
    pdf_urls.extend(file_urls)
    if file_urls:
        logger.info(f"Found {len(file_urls)} PDFs from {urls_file}")
    
    # 3. Add PDFs from web scraping (optional, commented out for now)
    # web_urls = fetch_pdf_urls_from_kenyalaw()
    # pdf_urls.extend(web_urls)
    # if web_urls:
    #     logger.info(f"Found {len(web_urls)} PDFs from web scraping")
    
    if not pdf_urls:
        logger.warning("No PDFs found. Add URLs to pdf_urls.txt, set PDF_URLS_FILE, or set PDF_LOCAL_DIR.")
        pdf_urls = []
    
    all_chunks = []
    
    # Process each PDF
    with tqdm(total=len(pdf_urls), desc="Processing PDFs") as pbar:
        for url, title in pdf_urls:
            pbar.set_description(f"Processing: {title[:30]}")
            
            try:
                # Check if already processed
                if use_supabase and supabase_manager.check_existing_url(url):
                    logger.info(f"URL already in database, skipping: {url}")
                    pbar.update(1)
                    continue
                
                # Download PDF (or use local file)
                pdf_path = None
                local_path = Path(url)
                if url.startswith("file://"):
                    pdf_path = url.replace("file://", "")
                elif local_path.exists():
                    pdf_path = str(local_path)
                else:
                    pdf_path = downloader.download_pdf(url)
                    if not pdf_path:
                        pbar.update(1)
                        continue
                
                # Process PDF
                chunks = processor.process_pdf(pdf_path, url, title)
                all_chunks.extend(chunks)
                
                # Clean up downloaded file (skip for local files)
                try:
                    if not Path(pdf_path).exists() or not local_path.exists():
                        os.remove(pdf_path)
                except:
                    pass
            
            except Exception as e:
                logger.error(f"Error processing {title}: {e}")
            
            finally:
                pbar.update(1)
    
    # Save to JSON
    json_path = OUTPUT_DIR / "chunks.json"
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(all_chunks)} chunks to {json_path}")
    except Exception as e:
        logger.error(f"Error saving JSON: {e}")
    
    # Upload to Supabase
    if use_supabase and all_chunks:
        supabase_manager.insert_chunks(all_chunks)
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info(f"Processing complete!")
    logger.info(f"Total chunks created: {len(all_chunks)}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"{'='*50}")
    
    downloader.close()


if __name__ == "__main__":
    main()
