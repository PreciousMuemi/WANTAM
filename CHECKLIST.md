# Quick Checklist: Get Gemini RAG Working

Copy and paste the checklist below. Complete each step and check it off.

## ✓ Pre-Check
- [ ] You have Supabase URL and key in `.env`
- [ ] You have Gemini API key in `.env`
- [ ] You've run `pip install google-generativeai` (already done ✓)
- [ ] Extracted chunks exist at `extracted_chunks/chunks.json` (54 chunks)

## ✓ Step 1: Update Supabase (1 min)
- [ ] Open https://supabase.com and log in
- [ ] Go to your project dashboard
- [ ] Click **SQL Editor** on the left
- [ ] Click **New Query**
- [ ] Copy-paste SQL from [SOLUTION_SUMMARY.md](SOLUTION_SUMMARY.md) Step 1
- [ ] Click **Run**
- [ ] Verify success message appears (green checkmark)
- [ ] Go to **SQL Editor** → **New Query** again
- [ ] Paste: `delete from documents;`
- [ ] Click **Run**
- [ ] See confirmation message

## ✓ Step 2: Re-embed Chunks (3 min)
- [ ] Open PowerShell/Terminal
- [ ] Navigate: `cd "c:\Users\SOOQ ELASER\WANTAM"`
- [ ] Run: `python re_embed_gemini.py`
- [ ] Wait for all 54 chunks to embed (progress bar)
- [ ] See success message: "54 chunks with 3072-dim Gemini embeddings"

## ✓ Step 3: Test System (2 min)
- [ ] Still in PowerShell, run: `python katiba_rag.py`
- [ ] See the Katiba AI welcome message
- [ ] See "Processing question" prompt
- [ ] Type question: `What is the constitution?`
- [ ] Press Enter
- [ ] See answer with source citations
- [ ] Type: `quit` to exit

## ✓ Done!
If you completed all steps with ✓, you're ready to use Katiba AI!

---

## What Each Step Does

| Step | What | Why |
|------|------|-----|
| Step 1 | Update database schema | Database was 1536D, needs 3072D |
| Step 2 | Generate Gemini embeddings | Old embeddings won't work |
| Step 3 | Test the pipeline | Verify everything works |

---

## If Something Goes Wrong

**Error during SQL?**
→ Copy error message and check [SOLUTION_SUMMARY.md](SOLUTION_SUMMARY.md) Troubleshooting section

**Error during re-embed?**
→ Verify GEMINI_API_KEY: `$env:GEMINI_API_KEY` should show your key

**Error during test?**
→ Make sure Supabase migration completed (check database has documents)

---

## Files You Should Have

- ✅ `katiba_rag.py` - Fixed with Gemini model
- ✅ `supabase_setup.sql` - Updated schema
- ✅ `re_embed_gemini.py` - Re-embedding script
- ✅ `SOLUTION_SUMMARY.md` - Complete documentation
- ✅ `GEMINI_FIX.md` - Setup guide
- ✅ `extracted_chunks/chunks.json` - 54 chunks to embed

All files are ready to use!
