# PDF Scraper for kenyalaw.org

A robust Python script that downloads PDFs from Kenya Law, extracts text with OCR fallback, chunks content intelligently, and stores in Supabase.

## Features

- ✅ **PDF Download**: Downloads PDFs from kenyalaw.org with progress tracking
- ✅ **Dual Text Extraction**: PyMuPDF for regular PDFs, Tesseract OCR fallback for scanned documents
- ✅ **Smart Chunking**: Splits text into 500-token segments with 50-token overlap using GPT tokenizer
- ✅ **Structured Output**: Saves chunks as JSON with metadata (URL, title, chunk ID, page number)
- ✅ **Supabase Integration**: Uploads chunks to Supabase with batch processing
- ✅ **Error Handling**: Comprehensive logging and error recovery
- ✅ **Progress Tracking**: tqdm progress bars for downloads and processing

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Tesseract OCR (Required for scanned PDFs)

**Windows:**

```bash
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
# Run installer with default settings, typically installs to:
# C:\Program Files\Tesseract-OCR
```

**macOS:**

```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt-get install tesseract-ocr
```

## Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key

# Optional: Tesseract Path (if not in system PATH)
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### 2. Create Supabase Table

Log into Supabase and create a `documents` table with the following schema:

```sql
create table documents (
  id bigint primary key generated always as identity,
  created_at timestamp with time zone default now(),
  source_url text not null,
  document_title text not null,
  chunk_id integer not null,
  text text not null,
  page_number integer not null,
  token_count integer
);

-- Create index for faster queries
create index documents_source_url_idx on documents(source_url);
```

## Usage

### Basic Usage

```bash
python pdf_scraper.py
```

The script will:

1. Fetch PDF URLs from kenyalaw.org
2. Download each PDF
3. Extract text (with OCR fallback)
4. Create overlapping chunks
5. Save to `extracted_chunks/chunks.json`
6. Upload to Supabase (if configured)

### Processing Custom URLs

Edit the `main()` function to add custom PDF URLs:

```python
# Replace this line in fetch_pdf_urls_from_kenyalaw():
pdf_urls = [
    ("https://kenyalaw.org/path/to/document1.pdf", "Constitution of Kenya"),
    ("https://kenyalaw.org/path/to/document2.pdf", "Penal Code"),
]
```

## Output

### JSON Structure

Each chunk is saved as:

```json
{
  "source_url": "https://kenyalaw.org/...",
  "document_title": "Document Title",
  "chunk_id": 0,
  "text": "Extracted text content...",
  "page_number": 0,
  "token_count": 487
}
```

### Chunks File

- **Location**: `extracted_chunks/chunks.json`
- **Format**: JSON array of chunk objects
- **Can be used for**: LLM fine-tuning, vector embeddings, RAG systems

## Troubleshooting

### Tesseract Not Found

If you get "pytesseract.TesseractNotFoundError":

1. Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki
2. Set `TESSERACT_PATH` in `.env` to your installation directory

### No PDFs Extracted from kenyalaw.org

The URL pattern in `fetch_pdf_urls_from_kenyalaw()` may need adjustment:

```python
# Add logging to see HTML structure
response = requests.get(KENYALAW_BASE_URL)
print(response.text[:2000])  # Print first 2000 chars
```

Then adjust the regex pattern accordingly.

### Supabase Connection Error

- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Check your Supabase project URL at https://supabase.com/dashboard
- Verify table exists: `documents`
- Check table permissions allow inserts

### Out of Memory with Large PDFs

For very large PDFs, adjust `CHUNK_SIZE_TOKENS`:

```python
CHUNK_SIZE_TOKENS = 300  # Smaller chunks
OVERLAP_TOKENS = 30
```

## Performance Notes

- **Token counting**: Uses `cl100k_base` encoding (GPT-3.5/4)
- **Chunk overlap**: 50 tokens provides context continuity
- **Batch upload**: 1000 chunks per Supabase transaction
- **OCR processing**: ~2-5 seconds per page depending on image quality

## Security Considerations

- Never commit `.env` file with real credentials
- Use Supabase service role key in production environments
- Consider rate limiting for large bulk downloads
- Validate URLs before processing

## Advanced Usage

### Custom Token Encoding

Change the encoding model to match your LLM:

```python
ENCODING_MODEL = "cl100k_base"  # GPT-3.5/4
# Options: "o200k_base" (GPT-4 Turbo), "gpt2" (legacy)
```

### Running as Background Job

```bash
nohup python pdf_scraper.py > scraper.log 2>&1 &
# or use a task scheduler (Windows Task Scheduler, cron, etc.)
```

## License

MIT
