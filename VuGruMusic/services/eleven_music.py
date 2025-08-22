import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ElevenLabsMusicService:
    """Service class for interacting with ElevenLabs Music API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        
    async def generate_music(
        self, 
        prompt: str, 
        duration_seconds: int,
        mode: str = "instrumental"
    ) -> bytes:
        """
        Generate music using ElevenLabs API
        
        Args:
            prompt: Text description of the music to generate
            duration_seconds: Length of the track in seconds (20-60)
            mode: Generation mode ('instrumental' or 'vocals')
            
        Returns:
            Audio data as bytes
            
        Raises:
            httpx.HTTPError: If the API request fails
            httpx.TimeoutException: If the request times out
        """
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "music_length_ms": duration_seconds * 1000,  # Convert to milliseconds
            "model_id": "music_v1"
        }
        
        logger.info(f"Generating music: {duration_seconds}s, mode: {mode}")
        logger.debug(f"Prompt: {prompt}")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/music",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 429:
                raise httpx.HTTPError("Rate limit exceeded")
            elif response.status_code == 401:
                raise httpx.HTTPError("Invalid API key")
            elif response.status_code != 200:
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise httpx.HTTPError(error_msg)
            
            return response.content
    
    async def get_credits(self) -> Dict[str, Any]:
        """
        Get remaining API credits
        
        Returns:
            Dictionary containing credit information
        """
        headers = {
            "xi-api-key": self.api_key
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/user/subscription",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get credits: {response.status_code}")
                return {"error": "Unable to fetch credit information"}
    
    def validate_duration(self, duration: int) -> bool:
        """Validate that duration is within acceptable range"""
        return 10 <= duration <= 60
    
    def sanitize_prompt(self, prompt: str) -> str:
        """Sanitize and clean the prompt text"""
        if not prompt or not isinstance(prompt, str):
            return ""
        
        # Remove potentially problematic characters
        sanitized = prompt.strip()
        
        # Limit length
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000] + "..."
        
        return sanitized
