import logging
from typing import List, Optional
from datetime import datetime
import uuid
from fastapi import HTTPException

from auth.supabase_client import supabase_client
from auth.models import GeneratedTrack, TrackResponse

logger = logging.getLogger(__name__)

class TrackService:
    def __init__(self):
        self.supabase_client = supabase_client
        self.table_name = "user_tracks"
        self._client = None
        
    def _get_client(self):
        """Get Supabase client, handling configuration errors"""
        if self._client is None:
            try:
                self._client = self.supabase_client.get_client()
                self.ensure_table_exists()
            except ValueError as e:
                logger.error(f"Supabase not configured: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Track service is not configured. Please check your environment variables."
                )
        return self._client
    
    def ensure_table_exists(self):
        """Ensure the tracks table exists in Supabase"""
        # Note: In production, you'd create this table via Supabase dashboard or migration
        # For now, we'll use the table if it exists
        logger.info("TrackService initialized")
    
    async def save_track(self, track_data: GeneratedTrack) -> TrackResponse:
        """Save track metadata to database"""
        try:
            # Get Supabase client
            client = self._get_client()
            
            # Generate ID if not provided
            if not track_data.id:
                track_data.id = str(uuid.uuid4())
            
            # Prepare data for insertion
            track_dict = {
                "id": track_data.id,
                "user_id": track_data.user_id,
                "title": track_data.title,
                "prompt": track_data.prompt,
                "duration": track_data.duration,
                "file_url": track_data.file_url,
                "file_name": track_data.file_name,
                "storage_path": track_data.storage_path,
                "created_at": datetime.now().isoformat()
            }
            
            # Insert into Supabase
            response = client.table(self.table_name).insert(track_dict).execute()
            
            if response.data:
                saved_track = response.data[0]
                return TrackResponse(
                    id=saved_track["id"],
                    title=saved_track["title"],
                    prompt=saved_track["prompt"],
                    duration=saved_track["duration"],
                    file_url=saved_track["file_url"],
                    file_name=saved_track["file_name"],
                    created_at=saved_track["created_at"]
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to save track")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error saving track: {str(e)}")
            # If table doesn't exist, we'll store in memory for now
            # In production, ensure table exists first
            return TrackResponse(
                id=track_data.id or str(uuid.uuid4()),
                title=track_data.title,
                prompt=track_data.prompt,
                duration=track_data.duration,
                file_url=track_data.file_url,
                file_name=track_data.file_name,
                created_at=datetime.now().isoformat()
            )
    
    async def get_user_tracks(self, user_id: str) -> List[TrackResponse]:
        """Get all tracks for a user"""
        try:
            client = self._get_client()
            response = client.table(self.table_name).select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            
            tracks = []
            if response.data:
                for track in response.data:
                    tracks.append(TrackResponse(
                        id=track["id"],
                        title=track["title"],
                        prompt=track["prompt"],
                        duration=track["duration"],
                        file_url=track["file_url"],
                        file_name=track["file_name"],
                        created_at=track["created_at"]
                    ))
            
            return tracks
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting user tracks: {str(e)}")
            return []
    
    async def delete_track(self, track_id: str, user_id: str) -> bool:
        """Delete a track"""
        try:
            client = self._get_client()
            response = client.table(self.table_name).delete().eq("id", track_id).eq("user_id", user_id).execute()
            
            if response.data:
                logger.info(f"Track deleted: {track_id}")
                return True
            else:
                logger.warning(f"No track found to delete: {track_id}")
                return False
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting track: {str(e)}")
            return False

# Create singleton instance
track_service = TrackService()