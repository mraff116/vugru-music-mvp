from typing import Optional, Tuple
from fastapi import HTTPException, status
import logging

from .supabase_client import supabase
from .models import UserSignup, UserLogin, AuthResponse, UserResponse

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.supabase = supabase

    async def sign_up(self, user_data: UserSignup) -> AuthResponse:
        """Create a new user account"""
        try:
            logger.info(f"Attempting to sign up user: {user_data.email}")
            
            # Sign up with Supabase Auth
            response = self.supabase.auth.sign_up({
                "email": user_data.email,
                "password": user_data.password,
                "options": {
                    "data": {
                        "full_name": user_data.full_name or ""
                    }
                }
            })
            
            logger.info(f"Supabase response: user={bool(response.user)}, session={bool(response.session)}")
            
            if not response.user:
                logger.error("No user returned from Supabase")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user account"
                )
            
            user = UserResponse(
                id=response.user.id,
                email=response.user.email or "",
                full_name=response.user.user_metadata.get("full_name") if response.user.user_metadata else None,
                created_at=response.user.created_at,
                email_confirmed_at=response.user.email_confirmed_at
            )
            
            # Handle case where session might be None (email confirmation required)
            if response.session:
                auth_response = AuthResponse(
                    user=user,
                    access_token=response.session.access_token or "",
                    refresh_token=response.session.refresh_token or "",
                    expires_at=response.session.expires_at or 0
                )
            else:
                logger.warning("No session returned - user created but may need email confirmation")
                # For development, create a basic auth response 
                auth_response = AuthResponse(
                    user=user,
                    access_token="temp_token_" + user.id,  # Temporary token for dev
                    refresh_token="",
                    expires_at=0
                )
            
            logger.info(f"User signed up successfully: {user_data.email}")
            return auth_response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Signup error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Signup failed: {str(e)}"
            )

    async def sign_in(self, user_data: UserLogin) -> AuthResponse:
        """Sign in an existing user"""
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": user_data.email,
                "password": user_data.password
            })
            
            if not response.user or not response.session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            user = UserResponse(
                id=response.user.id,
                email=response.user.email or "",
                full_name=response.user.user_metadata.get("full_name") if response.user.user_metadata else None,
                created_at=response.user.created_at,
                email_confirmed_at=response.user.email_confirmed_at
            )
            
            auth_response = AuthResponse(
                user=user,
                access_token=response.session.access_token or "",
                refresh_token=response.session.refresh_token or "",
                expires_at=response.session.expires_at or 0
            )
            
            logger.info(f"User signed in successfully: {user_data.email}")
            return auth_response
            
        except Exception as e:
            logger.error(f"Signin error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

    async def get_current_user(self, access_token: str) -> Optional[UserResponse]:
        """Get current user from access token"""
        try:
            # Get user from access token
            user = self.supabase.auth.get_user(access_token)
            if not user or not user.user:
                return None
            
            return UserResponse(
                id=user.user.id,
                email=user.user.email or "",
                full_name=user.user.user_metadata.get("full_name") if user.user.user_metadata else None,
                created_at=user.user.created_at,
                email_confirmed_at=user.user.email_confirmed_at
            )
            
        except Exception as e:
            logger.error(f"Error getting current user: {str(e)}")
            return None

    async def sign_out(self, access_token: str) -> bool:
        """Sign out user"""
        try:
            self.supabase.auth.sign_out()
            logger.info("User signed out successfully")
            return True
        except Exception as e:
            logger.error(f"Signout error: {str(e)}")
            return False

# Global auth service instance
auth_service = AuthService()