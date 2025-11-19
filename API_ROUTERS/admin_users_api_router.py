from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Dict, Any
import asyncpg
import os
from dotenv import load_dotenv
from DATABASE_HANDLER.utils.General_Functions import sha256_hash
from DATABASE_HANDLER.auth import require_admin

load_dotenv()

router = APIRouter(prefix="/api", tags=["Admin Users Management"])

DATABASE_URL = os.getenv("POSTGRES_CONNECTION_URL")

class CreateAdminUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class UpdatePasswordRequest(BaseModel):
    password: str

class UpdateStatusRequest(BaseModel):
    active: bool

@router.get("/admin-users")
async def get_admin_users(current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Get all admin users with their details
    Returns list of users without sensitive password information
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        users = await conn.fetch(
            """
            SELECT id, username, email, active, created_at, updated_at 
            FROM admin_users 
            ORDER BY created_at DESC
            """
        )
        
        await conn.close()
        
        users_list = [
            {
                "id": str(user['id']),
                "username": user['username'],
                "email": user['email'],
                "active": user['active'],
                "created_at": user['created_at'].isoformat() if user['created_at'] else None,
                "updated_at": user['updated_at'].isoformat() if user['updated_at'] else None
            }
            for user in users
        ]
        
        return {"status": "success", "users": users_list}
        
    except asyncpg.PostgresError as e:
        print(f"✗ Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin-users")
async def create_admin_user(user_data: CreateAdminUserRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Create a new admin user
    Hashes email and password before storing
    Sets active status to True by default
    """
    print(f"Creating new admin user - Username: {user_data.username}, Email: {user_data.email}")
    
    hashed_email = sha256_hash(user_data.email)
    hashed_password = sha256_hash(user_data.password)
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        existing_user = await conn.fetchrow(
            "SELECT id FROM admin_users WHERE email = $1 OR username = $2",
            hashed_email,
            user_data.username
        )
        
        if existing_user:
            await conn.close()
            raise HTTPException(status_code=400, detail="User with this email or username already exists")
        
        new_user = await conn.fetchrow(
            """
            INSERT INTO admin_users (username, email, password, active) 
            VALUES ($1, $2, $3, TRUE) 
            RETURNING id, username, email, active, created_at
            """,
            user_data.username,
            hashed_email,
            hashed_password
        )
        
        await conn.close()
        
        print(f"✓ Admin user created successfully: {user_data.username}")
        return {
            "status": "success",
            "message": "Admin user created successfully",
            "user": {
                "id": str(new_user['id']),
                "username": new_user['username'],
                "email": user_data.email,
                "active": new_user['active'],
                "created_at": new_user['created_at'].isoformat()
            }
        }
        
    except HTTPException:
        raise
    except asyncpg.PostgresError as e:
        print(f"✗ Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/admin-users/{user_id}")
async def update_admin_user_password(user_id: str, password_data: UpdatePasswordRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Update admin user password
    Does not require old password - direct password reset
    """
    print(f"Updating password for user ID: {user_id}")
    
    hashed_password = sha256_hash(password_data.password)
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        user = await conn.fetchrow(
            "SELECT id, username FROM admin_users WHERE id = $1",
            user_id
        )
        
        if not user:
            await conn.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        await conn.execute(
            """
            UPDATE admin_users 
            SET password = $1, updated_at = CURRENT_TIMESTAMP 
            WHERE id = $2
            """,
            hashed_password,
            user_id
        )
        
        await conn.close()
        
        print(f"✓ Password updated successfully for user: {user['username']}")
        return {
            "status": "success",
            "message": "Password updated successfully"
        }
        
    except HTTPException:
        raise
    except asyncpg.PostgresError as e:
        print(f"✗ Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/admin-users/{user_id}")
async def delete_admin_user(user_id: str, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Delete an admin user
    Permanently removes the user from the database
    """
    print(f"Deleting user ID: {user_id}")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        user = await conn.fetchrow(
            "SELECT username FROM admin_users WHERE id = $1",
            user_id
        )
        
        if not user:
            await conn.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        await conn.execute(
            "DELETE FROM admin_users WHERE id = $1",
            user_id
        )
        
        await conn.close()
        
        print(f"✓ User deleted successfully: {user['username']}")
        return {
            "status": "success",
            "message": "User deleted successfully"
        }
        
    except HTTPException:
        raise
    except asyncpg.PostgresError as e:
        print(f"✗ Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.patch("/admin-users/{user_id}/status")
async def update_admin_user_status(user_id: str, status_data: UpdateStatusRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Activate or deactivate an admin user
    When deactivated, user cannot login
    When activated, user can login normally
    """
    print(f"Updating status for user ID: {user_id} to {'active' if status_data.active else 'inactive'}")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        user = await conn.fetchrow(
            "SELECT username FROM admin_users WHERE id = $1",
            user_id
        )
        
        if not user:
            await conn.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        await conn.execute(
            """
            UPDATE admin_users 
            SET active = $1, updated_at = CURRENT_TIMESTAMP 
            WHERE id = $2
            """,
            status_data.active,
            user_id
        )
        
        await conn.close()
        
        status_text = "activated" if status_data.active else "deactivated"
        print(f"✓ User {status_text} successfully: {user['username']}")
        return {
            "status": "success",
            "message": f"User {status_text} successfully"
        }
        
    except HTTPException:
        raise
    except asyncpg.PostgresError as e:
        print(f"✗ Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")