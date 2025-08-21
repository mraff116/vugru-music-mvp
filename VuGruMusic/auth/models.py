from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: datetime
    email_confirmed_at: Optional[datetime] = None

class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    expires_at: int

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None

class MusicGenerationRecord(BaseModel):
    id: Optional[str] = None
    user_id: str
    prompt: str
    duration: int
    file_url: Optional[str] = None
    created_at: Optional[datetime] = None
    credits_used: int

class GeneratedTrack(BaseModel):
    id: Optional[str] = None
    user_id: str
    title: str
    prompt: str
    duration: int
    file_url: str
    file_name: str
    storage_path: str
    created_at: Optional[datetime] = None
    
class TrackResponse(BaseModel):
    id: str
    title: str
    prompt: str
    duration: int
    file_url: str
    file_name: str
    created_at: str