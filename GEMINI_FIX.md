## Quick Fix: Gemini to Supabase Schema Migration

You're getting this error because the database was created for OpenAI embeddings (1536 dims), but Gemini uses 3072 dims:

```
Error: 'different vector dimensions 1536 and 3072'
```

### ✅ What's Already Done

- [x] Fixed katiba_rag.py to use `models/gemini-embedding-001`
- [x] Updated embedding dimensions constant to 3072
- [x] Updated supabase_setup.sql schema

### 🔧 What You Need to Do (5 minutes)

#### Step 1: Update Supabase Schema

Go to [Supabase Console](https://supabase.com) → SQL Editor → New Query

Copy and paste this entire SQL block:

```sql
-- Drop old constraints
drop function if exists match_documents(vector(1536), int);
drop index if exists documents_embedding_idx;

-- Alter table to new dimensions
alter table documents alter column embedding set data type vector(3072);

-- Recreate index
create index if not exists documents_embedding_idx
  on documents using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- Recreate function
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

Click **Run** and wait for success message.

#### Step 2: Clear Old Embeddings

Run this in a new SQL Query:

```sql
delete from documents;
```

This clears the 1536-dimensional embeddings that won't work with the new schema.

#### Step 3: Re-embed Chunks with Gemini

In your terminal, run:

```bash
python re_embed_gemini.py
```

This will:

1. Load the 54 chunks from `extracted_chunks/chunks.json`
2. Generate 3072-dimensional embeddings using Gemini
3. Upload them to Supabase

**Expected output:**

```
============================================================
Re-embedding Chunks with Gemini
============================================================

[1/3] Loading chunks from JSON...
Loaded 54 chunks from extracted_chunks/chunks.json

[2/3] Generating Gemini embeddings...
Generating Gemini embeddings: 100%|████████| 54/54

[3/3] Uploading to Supabase...
Uploading to Supabase: 100%|████████| 54/54

============================================================
SUCCESS! Chunks re-embedded and uploaded.
Total: 54 chunks with 3072-dim Gemini embeddings
============================================================
```

#### Step 4: Test the System

```bash
python katiba_rag.py
```

Ask a question like:

```
You: What is the constitution?
```

You should now get answers with source citations!

### ✅ Summary of Changes

| Component          | Change                                                    | Why                         |
| ------------------ | --------------------------------------------------------- | --------------------------- | ------------------------------- |
| katiba_rag.py      | embedding model: `embedding-001` → `gemini-embedding-001` | Old model deprecated        |
| katiba_rag.py      | `EMBEDDING_DIMENSIONS`                                    | 384 → 3072                  | Gemini outputs 3072 dims        |
| supabase_setup.sql | Column type                                               | vector(1536) → vector(3072) | Match embedding dimensions      |
| supabase_setup.sql | RPC function                                              | Updated vector type         | Match column change             |
| Database           | Data                                                      | Clear old 1536D vectors     | They don't work with new schema |

### 🎯 Timeline

- SQL migration: ~1 minute
- Delete old embeddings: ~5 seconds
- Re-embed 54 chunks: ~2-3 minutes
- Test: ~1 minute
- **Total: ~5 minutes**

### ⚠️ If You Get Stuck

**Error during SQL migration?**

- Check Supabase console for error message
- Ensure you're in the correct database
- Try dropping each component separately

**Error during re-embedding?**

- Verify `GEMINI_API_KEY` is set: `echo $env:GEMINI_API_KEY`
- Check `extracted_chunks/chunks.json` exists and has data
- Try running just the Gemini embedding: `python test_gemini.py`

**Error running katiba_rag.py?**

- Verify Supabase migration completed
- Check database has documents: Query `select count(*) from documents;`
- Check embeddings have 3072 dimensions: Query `select array_length(embedding, 1) from documents limit 1;`

All components are ready! Just follow these 4 steps. 🚀
