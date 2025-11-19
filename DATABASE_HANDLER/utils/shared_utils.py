from typing import Dict, Any, List, Optional, Union, Tuple, Callable
import asyncpg
import re
import json
from fastapi import HTTPException


async def execute_query(database_url: str, query: str, *args, fetch_one: bool = False, fetch_all: bool = True) -> Optional[Union[asyncpg.Record, List[asyncpg.Record]]]:
    """
    Execute a database query with automatic connection handling
    
    Args:
        database_url: PostgreSQL connection URL
        query: SQL query string
        *args: Query parameters
        fetch_one: Return single row
        fetch_all: Return all rows (default)
    
    Returns:
        Query results or None
    """
    conn = await asyncpg.connect(database_url)
    try:
        if fetch_one:
            result = await conn.fetchrow(query, *args)
        elif fetch_all:
            result = await conn.fetch(query, *args)
        else:
            await conn.execute(query, *args)
            result = None
        return result
    except asyncpg.PostgresError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        await conn.close()


def generate_slug(title: str) -> str:
    """
    Generate a URL-friendly slug from a title
    
    Args:
        title: The title string to convert to slug
    
    Returns:
        URL-safe slug string
    """
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


async def ensure_unique_slug(conn: asyncpg.Connection, slug: str, table: str, exclude_id: Optional[str] = None) -> str:
    """
    Ensure slug is unique by appending counter if needed
    
    Args:
        conn: Database connection
        slug: Base slug to check
        table: Table name to check against
        exclude_id: ID to exclude from uniqueness check (for updates)
    
    Returns:
        Unique slug string
    """
    query = f"SELECT id FROM {table} WHERE slug = $1 AND isdeleted = FALSE"
    params = [slug]
    
    if exclude_id:
        query += " AND id != $2"
        params.append(exclude_id)
    
    existing = await conn.fetchrow(query, *params)
    
    if not existing:
        return slug
    
    original_slug = slug
    counter = 1
    while existing:
        slug = f"{original_slug}-{counter}"
        params[0] = slug
        existing = await conn.fetchrow(query, *params)
        counter += 1
    
    return slug


def serialize_record(record: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """
    Serialize database record to JSON-compatible format
    
    Args:
        record: Database record dictionary
        fields: List of field names to serialize
    
    Returns:
        Serialized dictionary with isoformat dates
    """
    result = {}
    for field in fields:
        value = record.get(field)
        if hasattr(value, 'isoformat'):
            result[field] = value.isoformat()
        else:
            result[field] = value
    return result


def build_dynamic_update_query(table: str, data: Dict[str, Any], id_field: str = "id") -> Tuple[List[str], List[Any], int]:
    """
    Build dynamic UPDATE query from provided data fields
    
    Args:
        table: Table name
        data: Dictionary of fields to update
        id_field: Name of ID field (default: "id")
    
    Returns:
        Tuple of (query_string, values_list, param_count)
    """
    update_fields = []
    update_values = []
    param_count = 1
    
    for key, value in data.items():
        if value is not None:
            update_fields.append(f"{key} = ${param_count}")
            if isinstance(value, dict):
                update_values.append(json.dumps(value))
            else:
                update_values.append(value)
            param_count += 1
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_fields.append("updated_at = CURRENT_TIMESTAMP")
    
    return update_fields, update_values, param_count


async def handle_database_errors(func: Callable) -> Callable:
    """
    Decorator for consistent database error handling
    """
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except asyncpg.PostgresError as e:
            raise HTTPException(status_code=500, detail="Database error occurred")
        except Exception as e:
            raise HTTPException(status_code=500, detail="Internal server error")
    return wrapper