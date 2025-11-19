from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import asyncpg
import os
from dotenv import load_dotenv
from DATABASE_HANDLER.utils.General_Functions import sha256_hash
from DATABASE_HANDLER.auth import create_access_token

load_dotenv()

router = APIRouter(prefix="/api", tags=["Authentication"])

DATABASE_URL = os.getenv("POSTGRES_CONNECTION_URL")

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/login")
async def login(credentials: LoginRequest):
    """
    API endpoint to handle user login
    Accepts email and password from frontend
    Hashes credentials and checks against database
    Returns JWT access token for API authentication
    """
    print(f"Login attempt - Email: {credentials.email}")
    print(f"Login attempt - Password: {credentials.password}")
    
    hashed_email = sha256_hash(credentials.email)
    hashed_password = sha256_hash(credentials.password)
    
    print(f"Hashed Email: {hashed_email}")
    print(f"Hashed Password: {hashed_password}")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        user = await conn.fetchrow(
            "SELECT * FROM admin_users WHERE email = $1 AND password = $2",
            hashed_email,
            hashed_password
        )
        
        await conn.close()
        
        if user:
            if not user['active']:
                print(f"Login failed - Account is deactivated: {user['username']}")
                raise HTTPException(status_code=403, detail="Account is deactivated. Please contact administrator.")
            
            access_token = create_access_token(
                data={
                    "user_id": str(user['id']),
                    "username": user['username'],
                    "role": "admin"
                }
            )
            
            print(f"Login successful for user: {user['username']}")
            return {
                "status": "success",
                "message": "Login successful",
                "email": credentials.email,
                "username": user['username'],
                "hashed_email": hashed_email,
                "hashed_password": hashed_password,
                "access_token": access_token,
                "token_type": "bearer"
            }
        else:
            print("Login failed - Invalid credentials")
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
    except asyncpg.PostgresError as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

class AutoLoginRequest(BaseModel):
    hashed_email: str
    hashed_password: str

@router.post("/auto-login")
async def auto_login(credentials: AutoLoginRequest):
    """
    API endpoint to handle automatic login using stored hashed credentials
    Accepts hashed email and password from localStorage
    Validates directly against database without additional hashing
    Returns JWT access token for API authentication
    """
    print(f"Auto-login attempt with hashed credentials")
    print(f"Hashed Email: {credentials.hashed_email}")
    print(f"Hashed Password: {credentials.hashed_password}")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        user = await conn.fetchrow(
            "SELECT * FROM admin_users WHERE email = $1 AND password = $2",
            credentials.hashed_email,
            credentials.hashed_password
        )
        
        await conn.close()
        
        if user:
            if not user['active']:
                print(f"Auto-login failed - Account is deactivated: {user['username']}")
                raise HTTPException(status_code=403, detail="Account is deactivated. Please contact administrator.")
            
            access_token = create_access_token(
                data={
                    "user_id": str(user['id']),
                    "username": user['username'],
                    "role": "admin"
                }
            )
            
            print(f"Auto-login successful for user: {user['username']}")
            return {
                "status": "success",
                "message": "Auto-login successful",
                "username": user['username'],
                "hashed_email": credentials.hashed_email,
                "hashed_password": credentials.hashed_password,
                "access_token": access_token,
                "token_type": "bearer"
            }
        else:
            print("Auto-login failed - Invalid credentials")
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except asyncpg.PostgresError as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")