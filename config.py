import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    Application configuration management
    Centralizes all environment variables and application constants
    """
    
    DATABASE_URL: str = os.getenv("POSTGRES_CONNECTION_URL", "")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    DB_POOL_MIN_SIZE: int = int(os.getenv("DB_POOL_MIN_SIZE", "5"))
    DB_POOL_MAX_SIZE: int = int(os.getenv("DB_POOL_MAX_SIZE", "20"))
    
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "5000"))
    
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8000")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:5000")
    
    ALLOWED_ORIGINS: list = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:8000,http://localhost:5000"
    ).split(",")
    
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")


class StatusConstants:
    """
    Status value constants for blog and case study content
    """
    DRAFT: str = "draft"
    PUBLISHED: str = "published"
    ARCHIVED: str = "archived"


class ContentTypeConstants:
    """
    Content type constants
    """
    BLOG: str = "BLOG"
    CASE_STUDY: str = "CASE STUDY"


class EditorChoiceConstants:
    """
    Editor's choice flag constants
    """
    YES: str = "Y"
    NO: str = "N"


class HTTPStatusConstants:
    """
    HTTP status code constants
    """
    OK: int = 200
    CREATED: int = 201
    NO_CONTENT: int = 204
    BAD_REQUEST: int = 400
    UNAUTHORIZED: int = 401
    FORBIDDEN: int = 403
    NOT_FOUND: int = 404
    INTERNAL_SERVER_ERROR: int = 500


class ErrorMessages:
    """
    Standardized error messages
    """
    DATABASE_ERROR: str = "Database error occurred"
    INTERNAL_SERVER_ERROR: str = "Internal server error"
    NOT_FOUND: str = "{} not found"
    ALREADY_EXISTS: str = "{} already exists"
    INVALID_INPUT: str = "Invalid input: {}"
    UNAUTHORIZED: str = "Unauthorized access"
    FORBIDDEN: str = "Insufficient permissions"
    DELETED_ITEM: str = "Cannot update deleted {}"


config = Config()