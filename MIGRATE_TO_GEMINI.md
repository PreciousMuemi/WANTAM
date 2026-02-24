# Migrating from OpenAI to Gemini Embeddings

## Issue

The Supabase database was originally configured for OpenAI embeddings (1536 dimensions), but Gemini embeddings are 3072 dimensions. You need to update the database schema.

## Fix Steps

### Step 1: Update Supabase Table Schema

Run this SQL in your Supabase SQL Editor (SQL > New Query):

```sql
-- Drop old function and index
drop function if exists match_documents(vector(1536), int);
drop index if exists documents_embedding_idx;

-- Alter table to use new vector dimension
alter table documents alter column embedding set data type vector(3072);

-- Recreate index with new vector type
create index if not exists documents_embedding_idx
  on documents using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- Recreate RPC function with new vector dimension
create or replace function match_documents (
  query_embedding vector(3072),
  match_count int default 5
)
returns table (
  id bigint,
  text text,
  source_url text,
  document_title text,
  chunk_id int,
  page_number int,
  similarity float
) language sql stable
as $$
  select
    documents.id,
    documents.text,
    documents.source_url,
    documents.document_title,
    documents.chunk_id,
    documents.page_number,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where documents.embedding is not null
  order by documents.embedding <=> query_embedding
  limit match_count;
$$;

grant execute on function match_documents(vector, int) to anon, authenticated;
```

### Step 2: Delete Old Embeddings

Since the old embeddings (1536 dims) won't work with the new schema, delete them:

```sql
-- Clear old embeddings (they're 1536-dimensional and won't work)
delete from documents;
```

### Step 3: Re-embed Documents with Gemini

Run the PDF scraper to re-embed all documents with Gemini embeddings:

```bash
python pdf_scraper.py
```

This will:

- Download PDFs from kenyalaw.org
- Extract text with OCR fallback
- Generate 3072-dimensional embeddings using Gemini
- Store in Supabase with new schema

### Step 4: Verify

Test the system:

```bash
python katiba_rag.py
```

Ask a question like: "What is the constitution?"

## Code Changes Made

- ✅ `katiba_rag.py`: Updated embedding model to `models/gemini-embedding-001`
- ✅ `katiba_rag.py`: Updated EMBEDDING_DIMENSIONS to 3072
- ✅ `supabase_setup.sql`: Updated schema to `vector(3072)`
- ✅ `supabase_setup.sql`: Updated RPC function signature

## Timeline

1. **~5 minutes**: Run SQL migrations in Supabase
2. **~2 minutes**: Delete old embeddings
3. **~10 minutes**: Re-scrape PDFs with new Gemini embeddings
4. **~1 minute**: Test with `python katiba_rag.py`

Total: ~18 minutes to complete migration
