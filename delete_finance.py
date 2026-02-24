from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Delete all Finance Bill chunks
print("Deleting Finance Bill chunks...")
result = sb.table('documents').delete().ilike('source_url', '%Finance%').execute()
print(f"Deleted {len(result.data)} Finance Bill chunks")

# Verify deletion
check = sb.table('documents').select('id', count='exact').ilike('source_url','%Finance%').execute()
print(f"Remaining Finance Bill chunks: {check.count}")
