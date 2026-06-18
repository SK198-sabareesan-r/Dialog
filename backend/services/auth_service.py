"""
Authentication Service - JWT token generation and Google OAuth handling
"""

import jwt
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import requests

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """Handles JWT token generation, validation, and Google OAuth"""

    def __init__(self):
        self.jwt_secret = settings.JWT_SECRET
        self.jwt_algorithm = settings.JWT_ALGORITHM
        self.jwt_expire_hours = settings.JWT_EXPIRE_HOURS
        self.google_client_id = settings.GOOGLE_CLIENT_ID
        self.google_client_secret = settings.GOOGLE_CLIENT_SECRET

        # Frontend URL hardcoded for OAuth redirects
        # PRODUCTION: Change to 'https://your-domain.com' before deployment
        self.frontend_url = 'http://localhost:3000'

    def generate_state(self) -> str:
        """Generate random state parameter for CSRF protection"""
        return secrets.token_urlsafe(32)

    def generate_google_oauth_url(self, state: str, redirect_uri: str) -> str:
        """
        Generate Google OAuth consent URL with all required scopes

        Scopes requested:
        - openid: Verify user identity
        - email: Get email address
        - profile: Get name and profile picture
        - drive.readonly: Browse and download files from Drive
        """
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"

        scopes = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/drive.readonly"
        ]

        params = {
            "client_id": self.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent"  # Force consent screen to get refresh token
        }

        query_string = "&".join([f"{k}={requests.utils.quote(str(v))}" for k, v in params.items()])
        return f"{base_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token and refresh token

        Returns:
            {
                "access_token": "ya29.xxx",
                "refresh_token": "...",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "openid email profile drive.readonly"
            }
        """
        token_url = "https://oauth2.googleapis.com/token"

        payload = {
            "code": code,
            "client_id": self.google_client_id,
            "client_secret": self.google_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }

        response = requests.post(token_url, data=payload)
        response.raise_for_status()

        return response.json()

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from Google UserInfo API

        Returns:
            {
                "id": "google_user_id",
                "email": "user@gmail.com",
                "verified_email": true,
                "name": "John Doe",
                "given_name": "John",
                "family_name": "Doe",
                "picture": "https://lh3.googleusercontent.com/...",
                "locale": "en"
            }
        """
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(userinfo_url, headers=headers)
        response.raise_for_status()

        return response.json()

    def create_jwt_token(self, user_info: Dict[str, Any], drive_token: str, refresh_token: str = "") -> str:
        now = datetime.utcnow()
        expiration = now + timedelta(hours=self.jwt_expire_hours)

        payload = {
            "sub": user_info["id"],
            "email": user_info["email"],
            "name": user_info["name"],
            "picture": user_info.get("picture", ""),
            "drive_token": drive_token,
            "drive_refresh_token": refresh_token,
            "iat": int(now.timestamp()),
            "exp": int(expiration.timestamp())
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        logger.info(f"JWT created for user: {user_info['email']}")
        return token

    def refresh_drive_token(self, refresh_token: str) -> str:
        """Exchange a Google refresh token for a new access token."""
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": self.google_client_id,
                "client_secret": self.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token

        Raises:
            jwt.ExpiredSignatureError: Token has expired
            jwt.InvalidTokenError: Token is invalid

        Returns decoded payload
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            raise
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            raise

    def extract_token_from_header(self, authorization: Optional[str]) -> Optional[str]:
        """Extract JWT token from Authorization header"""
        if not authorization:
            return None

        if not authorization.startswith("Bearer "):
            return None

        return authorization[7:]  # Remove "Bearer " prefix


# Singleton instance
auth_service = AuthService()
