# Supabase Setup Guide

## Step 1: Enable pgvector Extension

1. Go to https://supabase.com/dashboard
2. Select your project
3. Go to **SQL Editor** in the left sidebar
4. Click **New Query**
5. Run this command:

```sql
create extension if not exists vector;
```

## Step 2: Get Your API Keys

1. In your project, go to **Settings → API**
2. Look for these keys:
   - **Project URL**: `https://your-project-id.supabase.co`
   - **anon public**: This is the publishable key (public, safe to share)
   - **service_role secret**: This is the secret key (KEEP THIS PRIVATE!)

3. Update your `.env` file:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-service-role-secret-key-here
```

## Step 3: Create Database Table

1. Go to **SQL Editor**
2. Click **New Query**
3. Copy and paste the entire contents of `supabase_setup.sql`
4. Click **Run**

You should see success messages for each command.

## Step 4: Verify Setup

Run the connectivity test:

```bash
python test_rag.py connectivity
```

You should see:

- ✅ Connected to Supabase
- ✅ Connected to OpenAI
- ✅ Connected to Claude

## Step 5: Generate Embeddings

Once verified, generate embeddings for your documents:

```bash
python katiba_rag.py setup
```

This will:

1. Fetch all documents from the database
2. Generate embeddings using OpenAI
3. Store embeddings in Supabase

## Troubleshooting

### "Invalid API key"

- Make sure you're using the **service_role** key, not the anon key
- Double-check for any extra spaces in your `.env` file
- Restart your terminal after editing `.env`

### "pgvector extension not found"

- Run: `create extension if not exists vector;` in SQL Editor
- Wait a few seconds and try again

### "Table does not exist"

- Run the SQL from `supabase_setup.sql` in SQL Editor
- Make sure to execute ALL commands in the file

### Rate limiting

- OpenAI has rate limits. If you get rate limit errors:
  - Wait a minute before trying again
  - For large batches, use the batch API (documented in RAG_SETUP.md)

### Out of Memory

- Large PDFs can use lots of memory
- Process PDFs in smaller batches
- Reduce chunk size if needed
