# Katiba AI - RAG Pipeline for Kenyan Law

A complete Retrieval Augmented Generation (RAG) system that helps citizens understand Kenyan law using vector embeddings and Claude AI.

## Architecture

```
User Question
    ↓
[Embedding] (OpenAI text-embedding-3-small)
    ↓
[Vector Search] (Supabase pgvector similarity)
    ↓
[Retrieved Chunks] (Top 5 most relevant documents)
    ↓
[Claude API] (Generate contextual answer with system prompt)
    ↓
Answer + Source Citations
```

## Features

- 🔍 **Vector Search**: Fast semantic search using pgvector in Supabase
- 🧠 **Smart Embeddings**: OpenAI's text-embedding-3-small for semantic understanding
- 🤖 **Claude AI**: Contextual answers with accurate source citations
- 📚 **Full Context Retrieval**: Returns top 5 most relevant document chunks
- 🎯 **Localized Prompts**: Tailored to explain Kenyan law in simple English
- 📊 **Batch Processing**: Process multiple queries at once
- 🎨 **Interactive Mode**: Real-time Q&A interface

## Prerequisites

1. **Supabase Project** with pgvector extension enabled
2. **OpenAI API Key** (for embeddings)
3. **Claude API Key** (from Anthropic)
4. **Python 3.8+**

## Installation

### 1. Install Python Packages

```bash
pip install -r requirements.txt
```

### 2. Set Up Supabase pgvector

Run these SQL commands in your Supabase SQL Editor:

```sql
-- Enable pgvector extension
create extension if not exists vector;

-- Add embedding column to documents table
alter table documents add column embedding vector(1536);

-- Create index for faster similarity search
create index on documents using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- Create RPC function for similarity search
create or replace function match_documents (
  query_embedding vector(1536),
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

-- Grant execute permission
grant execute on function match_documents(vector, int) to anon, authenticated;
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
OPENAI_API_KEY=sk-...
CLAUDE_API_KEY=sk-ant-...
```

## Setup

### One-Time: Generate Embeddings for Existing Documents

If you already have documents in your database (from running `pdf_scraper.py`), generate embeddings:

```bash
python katiba_rag.py setup
```

This will:

1. Fetch all documents without embeddings
2. Generate embeddings using OpenAI
3. Store embeddings in Supabase

⏱️ **Note**: This may take a while depending on the number of documents. Progress is shown with a progress bar.

## Usage

### Interactive Mode (Default)

Ask questions and get instant answers:

```bash
python katiba_rag.py
```

Example conversation:

```
🏛️  KATIBA AI - Kenyan Law Assistant
============================================================
Ask questions about Kenyan law. Type 'quit' to exit.

You: What are the basic rights of Kenyan citizens?

Katiba AI: According to the Constitution of Kenya, basic rights include...

📚 Sources:
  - Constitution of Kenya (Page 15)
    Relevance: 92.3%
    URL: https://kenyalaw.org/...
```

### Batch Processing

Process multiple questions from a file:

```bash
# From text file (one question per line)
python katiba_rag.py batch questions.txt results.json

# From JSON file
python katiba_rag.py batch questions.json results.json
```

**Input formats:**

Text file (questions.txt):

```
What is the role of Parliament?
What are workers' rights under Kenyan law?
How does the judicial system work?
```

JSON file (questions.json):

```json
[
  "What is the role of Parliament?",
  "What are workers' rights under Kenyan law?",
  "How does the judicial system work?"
]
```

**Output** (results.json):

```json
[
  {
    "question": "What is the role of Parliament?",
    "query_number": 1,
    "answer": "According to the Constitution of Kenya...",
    "sources": [
      {
        "document_title": "Constitution of Kenya",
        "source_url": "https://kenyalaw.org/...",
        "page_number": 42,
        "similarity_score": 0.923,
        "chunk_id": 127
      }
    ],
    "model": "claude-3-5-sonnet-20241022",
    "stop_reason": "end_turn"
  }
]
```

## Python API Usage

Use Katiba RAG in your own Python code:

```python
from katiba_rag import KatibaRAG

# Initialize
rag = KatibaRAG()

# Ask a question
result = rag.answer("What are my rights as a Kenyan worker?")

# Access components
print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")

# Access individual components
from katiba_rag import VectorStore, ClaudeQA

# Custom retrieval
vector_store = VectorStore()
chunks = vector_store.similarity_search("freedom of speech", top_k=3)

# Custom QA
qa = ClaudeQA()
answer = qa.answer_question("What is...", chunks)
```

## System Prompt

The AI uses this system prompt (customizable in `katiba_rag.py`):

> You are Katiba AI, a helpful assistant that explains Kenyan law to ordinary citizens in plain, simple English.
>
> 1. Answer ONLY using the context provided.
> 2. If the answer is not in the context, say: "I don't have that information, but you can check kenyalaw.org"
> 3. Always cite which document/article your answer comes from.
> 4. Use simple, clear language that anyone can understand.
> 5. Break down complex legal concepts into everyday examples.
> 6. Be accurate - do not invent information.

## Configuration

Modify these settings in `katiba_rag.py`:

```python
# Change number of retrieved documents
TOP_K_RESULTS = 5  # Default: 5

# Change embedding model
EMBEDDING_MODEL = "text-embedding-3-small"  # or "text-embedding-3-large"

# Change LLM model
LLM_MODEL = "claude-3-5-sonnet-20241022"  # or "claude-3-opus-20240229"

# Modify system prompt
SYSTEM_PROMPT = """..."""
```

## Cost Optimization

### Embeddings (OpenAI)

- **text-embedding-3-small**: ~$0.02 per 1M tokens (5x cheaper)
- **text-embedding-3-large**: ~$0.13 per 1M tokens

For 10,000 documents with 500 tokens each = 5M tokens ≈ $0.10 with small model

### LLM (Claude)

- **Input**: $0.003 per 1K tokens
- **Output**: $0.015 per 1K tokens

Typical query with 5 retrieved chunks:

- Input: ~2K tokens (~$0.006)
- Output: ~200 tokens (~$0.003)
- **Total per query: ~$0.009**

## Troubleshooting

### "pgvector extension not available"

1. Enable pgvector in Supabase: Go to Extensions → Search "pgvector" → Enable
2. Run the SQL setup commands again

### "No relevant documents found"

1. Ensure embeddings have been generated (`python katiba_rag.py setup`)
2. Check that documents table has data
3. Verify `embedding` column has values

### "match_documents RPC not found"

Run the SQL setup commands to create the RPC function.

### Rate limiting from OpenAI/Claude

- Reduce batch size
- Add delays between requests
- Consider upgrading API tier

### Out of memory with large batches

Reduce batch size or process in smaller chunks:

```python
# Process in smaller batches
batch_size = 50
for i in range(0, len(queries), batch_size):
    batch = queries[i:i+batch_size]
    results.extend(batch_query_mode(batch))
```

## Performance Tips

1. **Add indexes**: pgvector indexes speed up searches significantly
2. **Chunk size**: 500 tokens balances context richness with cost
3. **Batch embeddings**: Use API's batch endpoint for large imports
4. **Cache queries**: Store frequently asked questions locally
5. **Optimize prompts**: Shorter system prompts reduce token usage

## Advanced Usage

### Custom Retrieval

```python
from katiba_rag import VectorStore

vs = VectorStore()
chunks = vs.similarity_search(
    "constitutional rights",
    top_k=10  # Get more results
)

for chunk in chunks:
    print(f"{chunk.document_title}: {chunk.similarity_score:.1%}")
```

### Fine-tuning Responses

Edit the `SYSTEM_PROMPT` for different use cases:

```python
SYSTEM_PROMPT = """You are a Kenyan law expert.
Provide detailed legal analysis...
"""
```

### Streaming Responses (Future)

Update `ClaudeQA.answer_question()` to use Claude's streaming API:

```python
with client.messages.stream(...) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

## Integration with Web Apps

### FastAPI Example

```python
from fastapi import FastAPI
from katiba_rag import KatibaRAG

app = FastAPI()
rag = KatibaRAG()

@app.post("/ask")
async def ask_question(question: str):
    result = rag.answer(question)
    return result
```

### Flask Example

```python
from flask import Flask, jsonify, request
from katiba_rag import KatibaRAG

app = Flask(__name__)
rag = KatibaRAG()

@app.route('/ask', methods=['POST'])
def ask():
    question = request.json.get('question')
    result = rag.answer(question)
    return jsonify(result)
```

## License

MIT

## Support

For issues or questions:

1. Check kenyalaw.org for official sources
2. Review logs for debugging
3. Verify Supabase configuration
4. Ensure all API keys are valid
