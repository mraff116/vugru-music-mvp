import os
import logging
from typing import Optional, List
from datetime import datetime
import uuid
from supabase import Client
from fastapi import HTTPException

from auth.supabase_client import supabase

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.client: Client = supabase
        self.bucket_name = "music-tracks"
        self.ensure_bucket_exists()
    
    def ensure_bucket_exists(self):
        """Ensure the storage bucket exists"""
        try:
            buckets = self.client.storage.list_buckets()
            bucket_exists = any(b.name == self.bucket_name for b in buckets)
            
            if not bucket_exists:
                logger.warning(f"Storage bucket '{self.bucket_name}' does not exist. Please create it manually in Supabase dashboard.")
                # Don't try to create automatically due to RLS policies
                
        except Exception as e:
            logger.error(f"Error checking bucket existence: {str(e)}")
    
    async def upload_track(self, file_data: bytes, user_id: str, filename: str) -> str:
        """Upload a track to Supabase storage"""
        try:
            # Create unique file path
            file_extension = filename.split('.')[-1] if '.' in filename else 'mp3'
            unique_filename = f"{user_id}/{uuid.uuid4()}.{file_extension}"
            
            # Upload to Supabase storage
            response = self.client.storage.from_(self.bucket_name).upload(
                path=unique_filename,
                file=file_data,
                file_options={"content-type": "audio/mpeg"}
            )
            
            # Get signed URL for private bucket (1 year expiry)
            signed_url_response = self.client.storage.from_(self.bucket_name).create_signed_url(
                path=unique_filename,
                expires_in=31536000  # 1 year in seconds
            )
            
            if signed_url_response and 'signedURL' in signed_url_response:
                logger.info(f"Track uploaded successfully: {unique_filename}")
                return signed_url_response['signedURL']
            else:
                # Fallback to public URL if signed URL fails
                url_response = self.client.storage.from_(self.bucket_name).get_public_url(unique_filename)
                return url_response
            
        except Exception as e:
            logger.error(f"Error uploading track: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to upload track")
    
    async def delete_track(self, file_path: str) -> bool:
        """Delete a track from storage"""
        try:
            self.client.storage.from_(self.bucket_name).remove([file_path])
            logger.info(f"Track deleted: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting track: {str(e)}")
            return False
    
    async def get_signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Get a signed URL for private file access"""
        try:
            response = self.client.storage.from_(self.bucket_name).create_signed_url(
                path=file_path,
                expires_in=expires_in
            )
            return response.get("signedURL", "")
        except Exception as e:
            logger.error(f"Error creating signed URL: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get file URL")

# Create singleton instance
storage_service = StorageService()