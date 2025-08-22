import os
from supabase import create_client, Client
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_ANON_KEY")
        self._client: Optional[Client] = None
        
    def get_client(self) -> Client:
        if self._client is None:
            if not self.url or not self.key:
                raise ValueError("Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_ANON_KEY")
            
            self._client = create_client(self.url, self.key)
            logger.info("Supabase client initialized successfully")
        
        return self._client

# Global client instance
supabase_client = SupabaseClient()
# Don't initialize supabase at import time - let it be lazy-loaded