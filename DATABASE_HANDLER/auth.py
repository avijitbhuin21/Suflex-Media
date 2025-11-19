from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from config import config
import jwt as pyjwt

JWT_SECRET_KEY = config.JWT_SECRET_KEY
JWT_ALGORITHM = config.JWT_ALGORITHM
JWT_EXPIRATION_HOURS = config.JWT_EXPIRATION_HOURS

security = HTTPBearer()


class TokenData(BaseModel):
    """
    Token payload data structure
    """
    user_id: str
    username: str
    role: str
    exp: datetime


class LoginRequest(BaseModel):
    """
    Login request structure
    """
    username: str
    password: str


class TokenResponse(BaseModel):
    """
    Token response structure
    """
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def hash_password(password: str) -> str:
    """
    Hash password using SHA256
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password string
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored hashed password
    
    Returns:
        True if password matches, False otherwise
    """
    return hash_password(plain_password) == hashed_password


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Payload data to encode in token
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = pyjwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT access token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = pyjwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer credentials from request
    
    Returns:
        User data from token payload
    
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    user_id = payload.get("user_id")
    username = payload.get("username")
    role = payload.get("role")
    
    if not user_id or not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": user_id,
        "username": username,
        "role": role
    }


async def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency to require admin role for protected routes
    
    Args:
        current_user: Current authenticated user data
    
    Returns:
        User data if admin role verified
    
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin role required."
        )
    
    return current_user


async def optional_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[Dict[str, Any]]:
    """
    Optional authentication dependency for routes that can work with or without auth
    
    Args:
        credentials: Optional HTTP Bearer credentials
    
    Returns:
        User data if authenticated, None otherwise
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

async def require_admin_with_redirect(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Dict[str, Any]:
    """
    Dependency to require admin role for protected page routes with redirect to login
    
    Args:
        request: FastAPI request object
        credentials: Optional HTTP Bearer credentials
    
    Returns:
        User data if admin role verified
    
    Raises:
        RedirectResponse: Redirects to login page if authentication fails
    """
    if credentials is None:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        
        user_id = payload.get("user_id")
        username = payload.get("username")
        role = payload.get("role")
        
        if not user_id or not username:
            return RedirectResponse(url="/login", status_code=303)
        
        if role != "admin":
            return RedirectResponse(url="/login", status_code=303)
        
        return {
            "user_id": user_id,
            "username": username,
            "role": role
        }
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)