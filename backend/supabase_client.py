import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://mynmldhqiflptjmhsuoq.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

try:
    if SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    else:
        # Fallback para desarrollo sin key configurada en env
        supabase = None
except Exception as e:
    print(f"[Supabase Client] Warning initializing client: {e}")
    supabase = None
