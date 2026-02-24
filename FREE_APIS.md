# Free & Affordable API Options for Katiba AI

Since you've hit quota limits on OpenAI and Claude, here are excellent alternatives:

## 🆓 Completely Free Options

### 1. **Google Gemini (Recommended)**

- **Free tier**: 60 requests/minute, completely free
- **Cost**: Free for embedding + generation
- **Quality**: Excellent, comparable to GPT-4

**Setup:**

```bash
# 1. Get free API key from https://aistudio.google.com/apikey
# 2. Add to .env:
GEMINI_API_KEY=your-key-here
EMBEDDING_PROVIDER=gemini
LLM_PROVIDER=gemini

# 3. Install dependency:
pip install google-generativeai

# 4. Run:
python katiba_rag.py
```

### 2. **Ollama (Run Locally - Zero Cost)**

- **Cost**: FREE, runs on your computer
- **Speed**: Fast (GPU-accelerated if available)
- **Models**: Gemma 2B, Mistral 7B, neural-chat, etc.

**Setup:**

```bash
# 1. Download from https://ollama.ai
# 2. Pull a model:
ollama pull neural-chat      # Good for Q&A (7B)
# or
ollama pull mistral          # Faster, smaller (7B)

# 3. Add to .env:
EMBEDDING_PROVIDER=ollama
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=neural-chat

# 4. Start Ollama (runs in background):
ollama serve

# 5. In another terminal:
python katiba_rag.py --embedding ollama --llm ollama
```

## 💰 Low-Cost Paid Options

### 3. **Cohere** (Very Cheap)

- **Embeddings**: Free tier available
- **Cost**: $0.10 per 1M tokens for embeddings (if paid)
- **Excellent quality**

```bash
# Get free key: https://cohere.com/
pip install cohere

# Add to .env:
COHERE_API_KEY=your-key
EMBEDDING_PROVIDER=cohere
```

### 4. **Hugging Face** (Free with Inference API)

- **Free tier**: Gated models available
- **Cost**: Free for some models, paid inference available
- **Many open-source models**

```bash
# Get token: https://huggingface.co/settings/tokens
pip install huggingface-hub

# Add to .env:
HF_API_KEY=your-token
EMBEDDING_PROVIDER=huggingface
```

## 🚀 Recommended Setup (Free)

### Option A: Gemini (Cloud + Free)

```env
# .env
SUPABASE_URL=...
SUPABASE_KEY=...
GEMINI_API_KEY=your-gemini-key
EMBEDDING_PROVIDER=gemini
LLM_PROVIDER=gemini
```

Then run:

```bash
pip install google-generativeai
python katiba_rag.py
```

### Option B: Ollama Local (Completely Free)

```env
# .env
SUPABASE_URL=...
SUPABASE_KEY=...
EMBEDDING_PROVIDER=ollama
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=neural-chat
```

Then:

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Run Katiba
python katiba_rag.py --embedding ollama --llm ollama
```

### Option C: Hybrid (Best of Both)

```env
# Use free Gemini for LLM, local Ollama for embeddings
GEMINI_API_KEY=your-key
EMBEDDING_PROVIDER=ollama
LLM_PROVIDER=gemini
OLLAMA_BASE_URL=http://localhost:11434
```

```bash
python katiba_rag.py --embedding ollama --llm gemini
```

## 📊 Cost Comparison (per 10,000 queries)

| Solution         | Embedding Cost | LLM Cost | Total     | Storage  |
| ---------------- | -------------- | -------- | --------- | -------- |
| **Gemini Free**  | Free           | Free     | **FREE**  | Free     |
| **Ollama Local** | Free           | Free     | **FREE**  | Local    |
| **OpenAI**       | $0.20          | $1.50    | **$1.70** | Supabase |
| **Claude**       | $0.20          | $3.00    | **$3.20** | Supabase |
| **Cohere**       | $0.10          | N/A      | **$0.10** | Supabase |

## 🎯 Quick Start (5 minutes)

### Using Gemini (Recommended):

```bash
# 1. Install Google AI
pip install google-generativeai

# 2. Get free API key: https://aistudio.google.com/apikey

# 3. Update .env
GEMINI_API_KEY=your-key-here
EMBEDDING_PROVIDER=gemini
LLM_PROVIDER=gemini

# 4. Run
python katiba_rag.py
```

## ⚙️ All Available Providers

### Embedding Providers

- ✅ **gemini** (Free, recommended)
- ✅ **ollama** (Free local)
- ✅ **openai** (Paid, limited quota)
- ✅ **huggingface** (Free tier available)
- ✅ **cohere** (Cheap)

### LLM Providers

- ✅ **gemini** (Free, recommended)
- ✅ **ollama** (Free local)
- ✅ **claude** (Paid, out of quota)

## 🔄 Switching Providers at Runtime

```bash
# Use different combinations:
python katiba_rag.py --embedding gemini --llm gemini
python katiba_rag.py --embedding ollama --llm gemini
python katiba_rag.py --embedding ollama --llm ollama
python katiba_rag.py --embedding openai --llm claude  # When you have quota
```

## 🆘 Troubleshooting

### "GEMINI_API_KEY not found"

- Get free key: https://aistudio.google.com/apikey
- Add to `.env`: `GEMINI_API_KEY=your-key`

### "Cannot connect to ollama"

- Make sure Ollama is running: `ollama serve`
- Check port is 11434 (or set `OLLAMA_BASE_URL` in .env)

### "Model not found"

```bash
# List available Ollama models:
ollama list

# Download a model:
ollama pull neural-chat
ollama pull mistral
ollama pull llama2
```

### Rate limiting

If you get rate limited:

1. Wait a few seconds
2. Try a different provider
3. Use local Ollama (no limits)

## 📈 For Production Use

**Recommended stack:**

- **Embeddings**: Ollama locally (fastest, no cost)
- **LLM**: Gemini free tier (reliable, free)
- **Storage**: Supabase (affordable)

This costs **$0** and can handle thousands of queries!

## 🎓 Learning Resources

- Gemini Docs: https://ai.google.dev/
- Ollama Docs: https://ollama.ai/library
- Cohere Docs: https://docs.cohere.com/
- HuggingFace Docs: https://huggingface.co/docs
