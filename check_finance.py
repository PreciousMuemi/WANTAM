from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Count total chunks
total = sb.table('documents').select('id', count='exact').execute()
print(f'Total chunks in database: {total.count}')

# Count Finance Bill chunks
finance = sb.table('documents').select('id', count='exact').ilike('source_url','%Finance%').execute()
print(f'Finance Bill chunks: {finance.count}')

# Get all Finance Bill IDs and check embeddings
all_finance = sb.table('documents').select('id,chunk_id,embedding').ilike('source_url','%Finance%').order('chunk_id').execute()
with_embedding = [d for d in all_finance.data if d['embedding'] is not None]
without_embedding = [d for d in all_finance.data if d['embedding'] is None]

print(f'\nFinance Bill WITH embeddings: {len(with_embedding)}')
print(f'Finance Bill WITHOUT embeddings: {len(without_embedding)}')

if with_embedding:
    print(f'Sample WITH embedding - chunk_id: {with_embedding[0]["chunk_id"]}')
if without_embedding:
    print(f'Sample WITHOUT embedding - chunk_id: {without_embedding[0]["chunk_id"]}')
