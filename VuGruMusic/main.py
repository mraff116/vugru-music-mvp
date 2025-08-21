from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import asyncio
import time
import logging
from typing import Dict, Optional, List
import os
from dotenv import load_dotenv
import json
import hashlib
from datetime import datetime, timedelta
import io
import base64

# Import authentication modules
from auth.auth_service import auth_service
from auth.models import UserSignup, UserLogin, UserResponse, GeneratedTrack, TrackResponse
from auth.middleware import get_current_user_required, get_current_user_optional

# Import storage modules
from storage.storage_service import storage_service
from storage.track_service import track_service

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="VuGru Music MVP", version="1.0.0")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for rate limiting and caching
active_requests: Dict[str, bool] = {}
track_cache: Dict[str, dict] = {}

class MusicGenerationRequest(BaseModel):
    prompt: str
    duration: int
    vocals_mode: str = "instrumental"

def get_client_ip(request: Request) -> str:
    """Get client IP for rate limiting"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def clean_cache():
    """Remove expired cache entries"""
    current_time = datetime.now()
    expired_keys = []
    
    for key, data in track_cache.items():
        if current_time - data["created_at"] > timedelta(minutes=15):
            expired_keys.append(key)
    
    for key in expired_keys:
        del track_cache[key]

def enhance_music_prompt(user_prompt: str, duration: int) -> str:
    """Enhance user prompt with technical details for better generation"""
    
    # Enhance the prompt with duration and technical details
    enhanced_prompt = f"{user_prompt}. Duration: {duration} seconds. Make it instrumental only, no vocals. Ensure clean loop points for seamless playback."
    
    return enhanced_prompt.strip()

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# Authentication endpoints
@app.post("/api/auth/signup")
async def signup(user_data: UserSignup):
    """User registration endpoint"""
    return await auth_service.sign_up(user_data)

@app.post("/api/auth/signin")
async def signin(user_data: UserLogin):
    """User login endpoint"""
    return await auth_service.sign_in(user_data)

@app.post("/api/auth/signout")
async def signout(current_user: UserResponse = Depends(get_current_user_required)):
    """User logout endpoint"""
    success = await auth_service.sign_out("")
    return {"success": success}

@app.get("/api/auth/user")
async def get_user(current_user: Optional[UserResponse] = Depends(get_current_user_optional)):
    """Get current authenticated user"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return current_user

@app.post("/api/generate_music")
async def generate_music(
    request_data: MusicGenerationRequest, 
    request: Request,
    current_user: UserResponse = Depends(get_current_user_required)
):
    """Generate music using ElevenLabs API"""
    client_ip = get_client_ip(request)
    
    # Check if there's already an active request for this IP
    if client_ip in active_requests and active_requests[client_ip]:
        raise HTTPException(
            status_code=429,
            detail="A music generation request is already in progress. Please wait for it to complete."
        )
    
    # Validate duration
    if not (10 <= request_data.duration <= 60):
        raise HTTPException(
            status_code=400,
            detail="Duration must be between 10 and 60 seconds"
        )
    
    # Get API key
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("ElevenLabs API key not found")
        raise HTTPException(
            status_code=500,
            detail="Music generation service is not configured properly"
        )
    
    # Mark this IP as having an active request
    active_requests[client_ip] = True
    
    try:
        # Use the user's prompt directly or enhance it slightly
        prompt = enhance_music_prompt(
            user_prompt=request_data.prompt,
            duration=request_data.duration
        )
        
        logger.info(f"Generating music - Duration: {request_data.duration}s, IP: {client_ip}")
        logger.info(f"Prompt: {prompt}")
        
        # Prepare API request
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        # ElevenLabs Music API payload
        payload = {
            "prompt": prompt,
            "music_length_ms": request_data.duration * 1000,  # Convert seconds to milliseconds
            "model_id": "music_v1"
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                # Make request to ElevenLabs Music API
                response = await client.post(
                    "https://api.elevenlabs.io/v1/music",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 429:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit reached. Please try again in a minute."
                    )
                elif response.status_code == 401:
                    error_data = response.json()
                    if "quota_exceeded" in str(error_data):
                        # Parse the quota error message
                        message = error_data.get("detail", {}).get("message", "")
                        logger.error(f"Quota exceeded: {message}")
                        
                        # Try to extract credit info from the message
                        import re
                        credits_match = re.search(r"You have (\d+) credits remaining, while (\d+) credits are required", message)
                        if credits_match:
                            remaining = int(credits_match.group(1))
                            required = int(credits_match.group(2))
                            # Calculate suggested duration based on credits
                            # Rough estimate: 788 credits for 35 seconds = ~22.5 credits per second
                            credits_per_second = 22.5
                            max_duration = int(remaining / credits_per_second)
                            
                            raise HTTPException(
                                status_code=402,
                                detail=f"Not enough credits. You have {remaining} credits but need {required} for {request_data.duration} seconds. Try a shorter duration (max ~{max_duration} seconds)."
                            )
                        else:
                            raise HTTPException(
                                status_code=402,
                                detail=f"Not enough credits for this request. Try a shorter duration (20 seconds or less)."
                            )
                    else:
                        logger.error(f"Authentication error: {response.text}")
                        raise HTTPException(
                            status_code=401,
                            detail="Authentication failed. Please check your API key."
                        )
                elif response.status_code != 200:
                    logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to generate music. Please try again."
                    )
                
                # Get the audio data
                audio_data = response.content
                
                # Create a unique ID for caching
                track_id = hashlib.md5(f"{prompt}_{request_data.duration}_{time.time()}".encode()).hexdigest()[:8]
                filename = f"vugru_track_{track_id}.mp3"
                
                # Save to Supabase storage if user is authenticated
                file_url = None
                storage_path = None
                if current_user:
                    try:
                        storage_path = f"{current_user.id}/{track_id}.mp3"
                        file_url = await storage_service.upload_track(
                            file_data=audio_data,
                            user_id=current_user.id,
                            filename=filename
                        )
                        
                        # Save track metadata to database
                        track_data = GeneratedTrack(
                            user_id=current_user.id,
                            title=request_data.prompt[:100],  # Use first 100 chars of prompt as title
                            prompt=prompt,
                            duration=request_data.duration,
                            file_url=file_url or "",
                            file_name=filename,
                            storage_path=storage_path
                        )
                        await track_service.save_track(track_data)
                        logger.info(f"Track saved to storage and database for user {current_user.id}")
                    except Exception as e:
                        logger.error(f"Failed to save track to storage: {str(e)}")
                        # Continue even if storage fails
                
                # Cache the track
                clean_cache()
                track_cache[track_id] = {
                    "audio_data": audio_data,
                    "prompt": prompt,
                    "duration": request_data.duration,
                    "created_at": datetime.now(),
                    "filename": filename
                }
                
                # Clean prompt for header (remove newlines and limit length)
                clean_prompt = prompt.replace('\n', ' ').replace('\r', ' ')[:500]
                
                # Return audio as streaming response
                return StreamingResponse(
                    iter([audio_data]),
                    media_type="audio/mpeg",
                    headers={
                        "Content-Disposition": f"attachment; filename={filename}",
                        "X-Track-ID": track_id,
                        "X-Prompt": clean_prompt,
                        "X-Storage-URL": file_url or ""
                    }
                )
                
            except httpx.TimeoutException:
                logger.error("Request to ElevenLabs API timed out")
                raise HTTPException(
                    status_code=504,
                    detail="Music generation timed out. Please try again with a shorter duration."
                )
            except httpx.RequestError as e:
                logger.error(f"Request error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to connect to music generation service."
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again."
        )
    finally:
        # Always remove the active request flag
        active_requests[client_ip] = False

@app.get("/api/track/{track_id}")
async def get_cached_track(track_id: str):
    """Retrieve a cached track by ID"""
    clean_cache()
    
    if track_id not in track_cache:
        raise HTTPException(
            status_code=404,
            detail="Track not found or has expired"
        )
    
    track_data = track_cache[track_id]
    
    return StreamingResponse(
        iter([track_data["audio_data"]]),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"attachment; filename={track_data['filename']}"
        }
    )

@app.get("/api/recent_tracks")
async def get_recent_tracks():
    """Get list of recent tracks"""
    clean_cache()
    
    tracks = []
    for track_id, data in sorted(track_cache.items(), key=lambda x: x[1]["created_at"], reverse=True)[:5]:
        tracks.append({
            "id": track_id,
            "filename": data["filename"],
            "duration": data["duration"],
            "prompt": data["prompt"][:100] + "..." if len(data["prompt"]) > 100 else data["prompt"],
            "created_at": data["created_at"].isoformat()
        })
    
    return {"tracks": tracks}

@app.get("/api/user_tracks")
async def get_user_tracks(current_user: UserResponse = Depends(get_current_user_required)) -> List[TrackResponse]:
    """Get all tracks for the authenticated user"""
    tracks = await track_service.get_user_tracks(current_user.id)
    return tracks

@app.delete("/api/user_tracks/{track_id}")
async def delete_user_track(track_id: str, current_user: UserResponse = Depends(get_current_user_required)):
    """Delete a track for the authenticated user"""
    success = await track_service.delete_track(track_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Track not found or access denied")
    
    # Also try to delete from storage
    # Storage path would be user_id/track_id.mp3
    storage_path = f"{current_user.id}/{track_id}.mp3"
    await storage_service.delete_track(storage_path)
    
    return {"message": "Track deleted successfully"}

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main page"""
    try:
        with open("static/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
