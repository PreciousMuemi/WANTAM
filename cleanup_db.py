from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print("Deleting all chunks without embeddings...")

# Get all chunks without embeddings
result = sb.table('documents').select('id').is_('embedding', 'null').execute()
print(f"Found {len(result.data)} chunks without embeddings")

# Delete them
if result.data:
    ids_to_delete = [r['id'] for r in result.data]
    # Delete in batches of 100
    for i in range(0, len(ids_to_delete), 100):
        batch = ids_to_delete[i:i+100]
        sb.table('documents').delete().in_('id', batch).execute()
        print(f"Deleted batch {i//100 + 1}: {len(batch)} chunks")

# Verify
remaining = sb.table('documents').select('id', count='exact').is_('embedding', 'null').execute()
print(f"\nRemaining chunks without embeddings: {remaining.count}")

total = sb.table('documents').select('id', count='exact').execute()
print(f"Total chunks in database: {total.count}")
