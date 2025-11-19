import logging
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel, field_validator, ValidationError
from typing import Optional, Dict, Any, List
import asyncpg
import json
import re
from DATABASE_HANDLER.auth import require_admin
from DATABASE_HANDLER.utils.shared_utils import generate_slug, ensure_unique_slug
from config import config, StatusConstants, ContentTypeConstants

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Blogs Management"])

DATABASE_URL = config.DATABASE_URL

class CreateBlogRequest(BaseModel):
    blog: Dict[str, Any]
    status: str = StatusConstants.DRAFT
    keyword: Optional[Dict[str, Any]] = None
    editors_choice: Optional[str] = 'N'
    slug: Optional[str] = None
    redirect_url: Optional[str] = None

    @field_validator('blog')
    @classmethod
    def validate_blog_not_empty(cls, v):
        if not v or not isinstance(v, dict):
            raise ValueError('Blog content must be a non-empty dictionary')
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        valid_statuses = [StatusConstants.DRAFT, StatusConstants.PUBLISHED, StatusConstants.ARCHIVED]
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v

    @field_validator('editors_choice')
    @classmethod
    def validate_editors_choice(cls, v):
        if v is not None and v not in ['Y', 'N']:
            raise ValueError('editors_choice must be either "Y" or "N"')
        return v

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v):
        if v is not None:
            if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
                raise ValueError('Slug must be lowercase alphanumeric with hyphens only')
        return v

    @field_validator('redirect_url')
    @classmethod
    def validate_redirect_url(cls, v):
        if v is not None and v.strip():
            if not re.match(r'^https?://', v):
                raise ValueError('Redirect URL must start with http:// or https://')
        return v

class UpdateBlogRequest(BaseModel):
    blog: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    keyword: Optional[Dict[str, Any]] = None
    editors_choice: Optional[str] = None
    slug: Optional[str] = None
    redirect_url: Optional[str] = None

    @field_validator('blog')
    @classmethod
    def validate_blog_not_empty(cls, v):
        if v is not None and (not v or not isinstance(v, dict)):
            raise ValueError('Blog content must be a non-empty dictionary if provided')
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = [StatusConstants.DRAFT, StatusConstants.PUBLISHED, StatusConstants.ARCHIVED]
            if v not in valid_statuses:
                raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v

    @field_validator('editors_choice')
    @classmethod
    def validate_editors_choice(cls, v):
        if v is not None and v not in ['Y', 'N']:
            raise ValueError('editors_choice must be either "Y" or "N"')
        return v

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v):
        if v is not None and v.strip():
            if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
                raise ValueError('Slug must be lowercase alphanumeric with hyphens only')
        return v

    @field_validator('redirect_url')
    @classmethod
    def validate_redirect_url(cls, v):
        if v is not None and v.strip():
            if not re.match(r'^https?://', v):
                raise ValueError('Redirect URL must start with http:// or https://')
        return v

@router.get("/blogs")
async def get_blogs(include_deleted: bool = Query(False, description="Include soft-deleted blogs")):
    """
    Get all blogs
    By default excludes soft-deleted entries
    Set include_deleted=true to show all blogs including deleted ones
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        if include_deleted:
            query = """
                SELECT id, blog, status, date, keyword, slug, type, redirect_url, isdeleted, created_at, updated_at
                FROM blogs
                WHERE type = '{ContentTypeConstants.BLOG}'
                ORDER BY date DESC
            """
        else:
            query = """
                SELECT id, blog, status, date, keyword, slug, type, redirect_url, isdeleted, created_at, updated_at
                FROM blogs
                WHERE isdeleted = FALSE AND type = '{ContentTypeConstants.BLOG}'
                ORDER BY date DESC
            """
        
        blogs = await conn.fetch(query)
        await conn.close()
        
        blogs_list = [
            {
                "id": str(blog['id']),
                "blog": blog['blog'],
                "status": blog['status'],
                "date": blog['date'].isoformat() if blog['date'] else None,
                "keyword": blog['keyword'],
                "category": blog['blog'].get('blogCategory', 'General') if isinstance(blog['blog'], dict) else json.loads(blog['blog']).get('blogCategory', 'General'),
                "slug": blog['slug'],
                "type": blog['type'],
                "redirect_url": blog['redirect_url'],
                "isdeleted": blog['isdeleted'],
                "created_at": blog['created_at'].isoformat() if blog['created_at'] else None,
                "updated_at": blog['updated_at'].isoformat() if blog['updated_at'] else None
            }
            for blog in blogs
        ]
        
        return {"status": "success", "blogs": blogs_list, "count": len(blogs_list)}
        
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in get_blogs: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in get_blogs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/blogs", status_code=201)
async def create_blog(blog_data: CreateBlogRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Create a new blog
    Requires blog content as JSONB
    Optional fields: status, keyword, redirect_url
    """
    logger.info(f"Creating new blog with status: {blog_data.status}")
    
    if not blog_data.blog:
        raise HTTPException(status_code=400, detail="Blog content is required")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Extract the type from blog data if it exists
        blog_content = blog_data.blog.copy() if blog_data.blog else {}
        content_type = blog_content.get('contentType', ContentTypeConstants.BLOG)
        
        new_blog = await conn.fetchrow(
            """
            INSERT INTO blogs (blog, status, keyword, editors_choice, slug, type, redirect_url, isdeleted)
            VALUES ($1, $2, $3, $4, $5, $6, $7, FALSE)
            RETURNING id, blog, status, date, keyword, editors_choice, slug, type, redirect_url, isdeleted, created_at, updated_at
            """,
            json.dumps(blog_content),
            blog_data.status,
            json.dumps(blog_data.keyword),
            blog_data.editors_choice,
            blog_data.slug,
            content_type,
            blog_data.redirect_url
        )
        
        await conn.close()
        
        logger.info(f"Blog created successfully with ID: {new_blog['id']}")
        return {
            "status": "success",
            "message": "Blog created successfully",
            "blog": {
                "id": str(new_blog['id']),
                "blog": new_blog['blog'],
                "status": new_blog['status'],
                "date": new_blog['date'].isoformat() if new_blog['date'] else None,
                "keyword": new_blog['keyword'],
                "category": new_blog['blog'].get('blogCategory', 'General') if isinstance(new_blog['blog'], dict) else json.loads(new_blog['blog']).get('blogCategory', 'General'),
                "slug": new_blog['slug'],
                "type": new_blog['type'],
                "redirect_url": new_blog['redirect_url'],
                "isdeleted": new_blog['isdeleted'],
                "created_at": new_blog['created_at'].isoformat() if new_blog['created_at'] else None,
                "updated_at": new_blog['updated_at'].isoformat() if new_blog['updated_at'] else None
            }
        }
        
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in create_blog: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in create_blog: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/blogs/{blog_id}")
async def update_blog(blog_id: str, blog_data: UpdateBlogRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Update an existing blog
    Only updates provided fields (partial update)
    Cannot update soft-deleted blogs
    """
    logger.info(f"Updating blog ID: {blog_id}")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        existing_blog = await conn.fetchrow(
            "SELECT id, isdeleted FROM blogs WHERE id = $1",
            blog_id
        )
        
        if not existing_blog:
            await conn.close()
            raise HTTPException(status_code=404, detail="Blog not found")
        
        if existing_blog['isdeleted']:
            await conn.close()
            raise HTTPException(status_code=400, detail="Cannot update deleted blog")
        
        update_fields = []
        update_values = []
        param_count = 1
        
        if blog_data.blog is not None:
            update_fields.append(f"blog = ${param_count}")
            update_values.append(json.dumps(blog_data.blog))
            param_count += 1
        
        if blog_data.status is not None:
            update_fields.append(f"status = ${param_count}")
            update_values.append(blog_data.status)
            param_count += 1
        
        if blog_data.keyword is not None:
            update_fields.append(f"keyword = ${param_count}")
            update_values.append(json.dumps(blog_data.keyword))
            param_count += 1
        
        if blog_data.slug is not None:
            update_fields.append(f"slug = ${param_count}")
            update_values.append(blog_data.slug)
            param_count += 1
        
        if blog_data.editors_choice is not None:
            update_fields.append(f"editors_choice = ${param_count}")
            update_values.append(blog_data.editors_choice)
            param_count += 1
        
        if blog_data.redirect_url is not None:
            update_fields.append(f"redirect_url = ${param_count}")
            update_values.append(blog_data.redirect_url)
            param_count += 1
        
        if not update_fields:
            await conn.close()
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_fields.append(f"updated_at = CURRENT_TIMESTAMP")
        update_values.append(blog_id)
        
        query = f"""
            UPDATE blogs
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, blog, status, date, keyword, slug, type, redirect_url, isdeleted, created_at, updated_at
        """
        
        updated_blog = await conn.fetchrow(query, *update_values)
        await conn.close()
        
        logger.info(f"Blog updated successfully: {blog_id}")
        return {
            "status": "success",
            "message": "Blog updated successfully",
            "blog": {
                "id": str(updated_blog['id']),
                "blog": updated_blog['blog'],
                "status": updated_blog['status'],
                "date": updated_blog['date'].isoformat() if updated_blog['date'] else None,
                "keyword": updated_blog['keyword'],
                "category": updated_blog['blog'].get('blogCategory', 'General') if isinstance(updated_blog['blog'], dict) else json.loads(updated_blog['blog']).get('blogCategory', 'General'),
                "slug": updated_blog['slug'],
                "type": updated_blog['type'],
                "redirect_url": updated_blog['redirect_url'],
                "isdeleted": updated_blog['isdeleted'],
                "created_at": updated_blog['created_at'].isoformat() if updated_blog['created_at'] else None,
                "updated_at": updated_blog['updated_at'].isoformat() if updated_blog['updated_at'] else None
            }
        }
        
    except HTTPException:
        raise
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in update_blog: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in update_blog: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.patch("/blogs/{blog_id}")
async def partial_update_blog(blog_id: str, blog_data: UpdateBlogRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Partial update of an existing blog (alias for PUT endpoint)
    Only updates provided fields
    Cannot update soft-deleted blogs
    """
    return await update_blog(blog_id, blog_data)

@router.delete("/blogs/{blog_id}")
async def delete_blog(blog_id: str, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Permanently delete a blog from the database
    This action cannot be undone
    """
    logger.warning(f"Permanently deleting blog ID: {blog_id}")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        blog = await conn.fetchrow(
            "SELECT id FROM blogs WHERE id = $1",
            blog_id
        )
        
        if not blog:
            await conn.close()
            raise HTTPException(status_code=404, detail="Blog not found")
        
        await conn.execute(
            "DELETE FROM blogs WHERE id = $1",
            blog_id
        )
        
        await conn.close()
        
        logger.info(f"Blog permanently deleted successfully: {blog_id}")
        return {
            "status": "success",
            "message": "Blog deleted successfully"
        }
        
    except HTTPException:
        raise
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in delete_blog: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in delete_blog: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/blogs/{blog_id}/restore")
async def restore_blog(blog_id: str, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Restore a soft-deleted blog
    Sets isdeleted back to FALSE
    """
    logger.info(f"Restoring blog ID: {blog_id}")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        blog = await conn.fetchrow(
            "SELECT id, isdeleted FROM blogs WHERE id = $1",
            blog_id
        )
        
        if not blog:
            await conn.close()
            raise HTTPException(status_code=404, detail="Blog not found")
        
        if not blog['isdeleted']:
            await conn.close()
            raise HTTPException(status_code=400, detail="Blog is not deleted")
        
        await conn.execute(
            """
            UPDATE blogs
            SET isdeleted = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            blog_id
        )
        
        await conn.close()
        
        logger.info(f"Blog restored successfully: {blog_id}")
        return {
            "status": "success",
            "message": "Blog restored successfully"
        }
        
    except HTTPException:
        raise
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in restore_blog: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in restore_blog: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin_save_blog")
async def admin_save_blog(request: Request, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Save blog from admin panel (Draft or Publish)
    Receives complete blog data from frontend and saves to database
    Preserves all original JSON key names
    Generates slug from title field
    """
    try:
        data = await request.json()
        
        logger.debug("=" * 80)
        logger.debug("RECEIVED BLOG DATA FROM FRONTEND:")
        logger.debug(json.dumps(data, indent=2))
        logger.debug(f"Data keys: {list(data.keys())}")
        logger.debug(f"Status field: {data.get('blogStatus', 'NOT FOUND')}")
        logger.debug("=" * 80)
        
        blog_title = data.get('blogTitle', '')
        if not blog_title:
            raise HTTPException(status_code=400, detail="Blog title is required")
        
        # Check if this is an update request
        blog_id = data.get('blog_id')
        reason = data.get('reason', 'create')  # 'create' or 'update'
        
        slug = generate_slug(blog_title)
        blog_status = data.get('blogStatus', StatusConstants.DRAFT)
        content_type = data.get('contentType', ContentTypeConstants.BLOG)
        
        # Add the content type to the blog data for storage
        data['contentType'] = content_type
        
        conn = await asyncpg.connect(DATABASE_URL)
        
        try:
            if reason == 'update' and blog_id:
                # Check if the blog exists and is not deleted
                existing_blog = await conn.fetchrow(
                    "SELECT id, slug FROM blogs WHERE id = $1 AND isdeleted = FALSE",
                    blog_id
                )
                
                if not existing_blog:
                    raise HTTPException(status_code=404, detail="Blog not found for update")
                
                # Check if the slug is being changed and if the new slug already exists
                existing_slug = existing_blog['slug']
                if slug != existing_slug:
                    # Check if the new slug already exists for a different blog
                    existing_slug_record = await conn.fetchrow(
                        "SELECT id FROM blogs WHERE slug = $1 AND id != $2 AND isdeleted = FALSE",
                        slug,
                        blog_id
                    )
                    
                    if existing_slug_record:
                        original_slug = slug
                        counter = 1
                        while existing_slug_record:
                            slug = f"{original_slug}-{counter}"
                            existing_slug_record = await conn.fetchrow(
                                "SELECT id FROM blogs WHERE slug = $1 AND id != $2 AND isdeleted = FALSE",
                                slug,
                                blog_id
                            )
                            counter += 1
                        logger.info(f"Generated unique slug: {slug}")
                
                # Update existing blog
                updated_blog = await conn.fetchrow(
                    """
                    UPDATE blogs
                    SET blog = $1, status = $2, editors_choice = $3, slug = $4, type = $5, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $6
                    RETURNING id, blog, status, date, keyword, editors_choice, slug, type, redirect_url, isdeleted, created_at, updated_at
                    """,
                    json.dumps(data),
                    blog_status,
                    data.get('editors_choice', 'N'),
                    slug,
                    content_type,
                    blog_id
                )
                
                if not updated_blog:
                    raise HTTPException(status_code=404, detail="Blog not found for update")
                
                blog_id = str(updated_blog['id'])
                blog_url = f"{config.BACKEND_URL}/blog/{slug}"
                
                logger.info(f"Blog updated successfully - ID: {blog_id}, slug: {slug}, status: {blog_status}, type: {content_type}, URL: {blog_url}")
                
                return {
                    "status": "success",
                    "message": f"Blog {'published' if blog_status == StatusConstants.PUBLISHED else 'updated'} successfully",
                    "blog_id": blog_id,
                    "slug": slug,
                    "url": blog_url
                }
            else:
                slug = await ensure_unique_slug(conn, slug, "blogs")
                
                new_blog = await conn.fetchrow(
                    """
                    INSERT INTO blogs (blog, status, editors_choice, slug, type, isdeleted)
                    VALUES ($1, $2, $3, $4, $5, FALSE)
                    RETURNING id, blog, status, date, keyword, editors_choice, slug, type, redirect_url, isdeleted, created_at, updated_at
                    """,
                    json.dumps(data),
                    blog_status,
                    data.get('editors_choice', 'N'),
                    slug,
                    content_type
                )
                
                blog_id = str(new_blog['id'])
                blog_url = f"{config.BACKEND_URL}/blog/{slug}"
                
                logger.info(f"Blog saved successfully - ID: {blog_id}, slug: {slug}, status: {blog_status}, type: {content_type}, URL: {blog_url}")
                
                return {
                    "status": "success",
                    "message": f"Blog {'published' if blog_status == StatusConstants.PUBLISHED else 'saved as draft'} successfully",
                    "blog_id": blog_id,
                    "slug": slug,
                    "url": blog_url
                }
            
        finally:
            await conn.close()
        
    except HTTPException:
        raise
    except asyncpg.UniqueViolationError:
        logger.warning("Slug already exists")
        raise HTTPException(status_code=400, detail="A blog with this title already exists")
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in admin_save_blog: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in admin_save_blog: {e}")
        raise HTTPException(status_code=500, detail=str(e))

