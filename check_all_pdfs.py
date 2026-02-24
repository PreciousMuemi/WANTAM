from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Get unique documents
docs = sb.table('documents').select('source_url').execute()
unique_urls = list(set([d['source_url'] for d in docs.data]))

print(f"Total unique documents: {len(unique_urls)}\n")

# Check each document
for url in sorted(unique_urls):
    # Get count and embedding status
    all_chunks = sb.table('documents').select('id,embedding').eq('source_url', url).execute()
    with_emb = [c for c in all_chunks.data if c['embedding'] is not None]
    without_emb = [c for c in all_chunks.data if c['embedding'] is None]
    
    # Extract doc name
    doc_name = url.split('\\')[-1] if '\\' in url else url.split('/')[-1]
    
    status = "✓" if len(without_emb) == 0 else "✗"
    print(f"{status} {doc_name[:60]}")
    print(f"   Total: {len(all_chunks.data)} | With: {len(with_emb)} | Without: {len(without_emb)}")
