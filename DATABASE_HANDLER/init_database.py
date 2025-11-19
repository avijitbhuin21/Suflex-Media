import os
import logging
import asyncpg
from dotenv import load_dotenv
from .utils import sha256_hash

logger = logging.getLogger(__name__)
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("POSTGRES_CONNECTION_URL")

async def ensure_admin_user(conn):
    """
    Ensure the default admin user exists in the database.
    Creates the admin user if it doesn't already exist.
    """
    try:
        admin_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM admin_users WHERE username = $1)",
            "admin"
        )
        
        if admin_exists:
            logger.info("Admin user already exists")
        else:
            await conn.execute(
                """
                INSERT INTO admin_users (email, username, password)
                VALUES ($1, $2, $3)
                """,
                sha256_hash("admin@gmail.com"),
                "admin",
                sha256_hash("admin")
            )
            logger.info("Default admin user created successfully")
            
    except asyncpg.PostgresError as e:
        logger.error(f"Error ensuring admin user: {e}")
        raise

async def initialize_database():
    """
    Initialize the database by running the SQL file.
    Creates tables if they don't exist.
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        sql_file_path = os.path.join(os.path.dirname(__file__), 'init_db.sql')
        with open(sql_file_path, 'r') as f:
            sql_script = f.read()
        
        sql_script = sql_script.strip()
        if sql_script == "":
            logger.warning("No SQL commands found in init_db.sql")
            logger.info("Database tables initialized successfully (no changes made)")
        else:
            logger.info("SQL script loaded successfully")
            await conn.execute(sql_script)
            logger.info("Database tables initialized successfully")

            await ensure_admin_user(conn)
            logger.info("Admin user check completed")
        
        await conn.close()
        
    except FileNotFoundError:
        logger.error("Error: init_db.sql file not found")
        raise
    except asyncpg.PostgresError as e:
        logger.error(f"Database error during initialization: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}")
        raise