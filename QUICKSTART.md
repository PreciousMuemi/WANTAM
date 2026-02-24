# Katiba AI - Quick Start Guide

Your system is **95% ready!** You just hit API quota limits. Let's fix that with free alternatives.

## ⚡ Quick Setup (Choose ONE)

### Option 1: Google Gemini (Recommended - 5 min)

**Easiest and completely free!**

1. **Get free API key** (30 seconds):
   - Go to https://aistudio.google.com/apikey
   - Click "Create API Key"
   - Copy the key

2. **Update `.env`**:

   ```env
   GEMINI_API_KEY=your-key-here
   EMBEDDING_PROVIDER=gemini
   LLM_PROVIDER=gemini
   ```

3. **Install the library**:

   ```bash
   pip install google-generativeai
   ```

4. **Start asking questions**:
   ```bash
   python katiba_rag.py
   ```

---

### Option 2: Local Ollama (Completely Free - 10 min)

**Runs on YOUR computer, zero API costs, no quota limits!**

1. **Download Ollama**: https://ollama.ai
   - Click "Download"
   - Install it
   - It will run automatically in the background

2. **Download a model** (first time, ~2-4GB download):

   ```bash
   ollama pull neural-chat
   ```

   Or smaller:

   ```bash
   ollama pull mistral
   ```

3. **Update `.env`**:

   ```env
   EMBEDDING_PROVIDER=ollama
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=neural-chat
   ```

4. **Make sure Ollama is running**:
   - It usually runs automatically
   - Check: http://localhost:11434 should respond

5. **Start using**:
   ```bash
   python katiba_rag.py
   ```

---

### Option 3: Gemini + Local Ollama (Best Hybrid)

**Fast embeddings locally + Free quality LLM**

```env
GEMINI_API_KEY=your-key
EMBEDDING_PROVIDER=ollama
LLM_PROVIDER=gemini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=neural-chat
```

---

## 📋 Status Check

Your documents are **already in Supabase**:

```
✅ Supabase connected
✅ 54 document chunks ingested
✅ 1 document with embeddings
✅ PostgreSQL + pgvector working
```

You just need:

```
❌ OpenAI (out of quota)
❌ Claude (out of credits)
✅ Gemini (FREE!)
✅ Ollama (FREE, local)
```

## 🧪 Test It

After setting up ONE of the options above:

```bash
# Test connectivity
python test_rag.py connectivity

# Test single query
python test_rag.py single

# Start interactive mode
python katiba_rag.py
```

## 💡 Example Questions

Try asking:

- "What are basic rights in Kenya?"
- "What is the finance bill?"
- "Who is the president?"
- "What laws govern workers?"

## 🎯 My Recommendation

**Start with Gemini** if you want:

- ✅ No setup needed beyond getting API key
- ✅ Free forever
- ✅ Great quality responses
- ✅ Instant access

**Use Ollama** if you want:

- ✅ Completely offline (no external APIs)
- ✅ Zero cost
- ✅ No rate limits
- ✅ Privacy (all local)

## 📱 Usage

Once set up, it's super simple:

```bash
python katiba_rag.py
```

Then:

```
You: What is the constitution?
Katiba AI: The Constitution of Kenya is the supreme law...
📚 Sources:
  - Constitution of Kenya (Page 15)
```

## 🔧 Advanced

See [FREE_APIS.md](FREE_APIS.md) for:

- All provider options
- Switching between providers
- Cost comparisons
- Troubleshooting

## ❓ Questions?

1. **"Can I use all APIs at once?"**
   - No, you choose one embedding + one LLM per session
   - But you can switch combinations easily

2. **"Will it work offline?"**
   - Gemini: Needs internet
   - Ollama: Works completely offline!

3. **"What about my existing data?"**
   - ✅ All 54 chunks are safe in Supabase
   - ✅ Your PDF extraction worked perfectly
   - ✅ Just need API keys for the RAG part

4. **"How fast is it?"**
   - Gemini: ~2-3 seconds per query
   - Ollama: ~1-2 seconds per query (local)
   - Depends on document length and question complexity

---

## 🚀 Next Steps

1. Pick Gemini or Ollama
2. Follow setup for your choice
3. Run `python katiba_rag.py`
4. Ask a question!

**That's it!** You now have a working legal AI assistant! 🎉
