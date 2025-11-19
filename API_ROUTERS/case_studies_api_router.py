import logging
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncpg
import json
from DATABASE_HANDLER.auth import require_admin
from DATABASE_HANDLER.utils.shared_utils import generate_slug, ensure_unique_slug
from config import config, StatusConstants, ContentTypeConstants

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Case Studies Management"])

DATABASE_URL = config.DATABASE_URL

class CreateCaseStudyRequest(BaseModel):
    blog: Dict[str, Any]
    status: str = StatusConstants.DRAFT
    keyword: Optional[Dict[str, Any]] = None
    preview: Optional[Dict[str, Any]] = None
    editors_choice: Optional[str] = 'N'
    slug: Optional[str] = None
    redirect_url: Optional[str] = None

class UpdateCaseStudyRequest(BaseModel):
    blog: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    keyword: Optional[Dict[str, Any]] = None
    preview: Optional[Dict[str, Any]] = None
    editors_choice: Optional[str] = None
    slug: Optional[str] = None
    redirect_url: Optional[str] = None

@router.get("/case-studies")
async def get_case_studies(include_deleted: bool = Query(False, description="Include soft-deleted case studies")):
    """
    Get all case studies
    By default excludes soft-deleted entries
    Set include_deleted=true to show all case studies including deleted ones
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        if include_deleted:
            query = f"""
                SELECT id, blog, status, date, keyword, preview, slug, type, redirect_url, isdeleted, created_at, updated_at
                FROM case_studies
                WHERE type = '{ContentTypeConstants.CASE_STUDY}'
                ORDER BY date DESC
            """
        else:
            query = f"""
                SELECT id, blog, status, date, keyword, preview, slug, type, redirect_url, isdeleted, created_at, updated_at
                FROM case_studies
                WHERE isdeleted = FALSE AND type = '{ContentTypeConstants.CASE_STUDY}'
                ORDER BY date DESC
            """
        
        case_studies = await conn.fetch(query)
        await conn.close()
        
        case_studies_list = [
            {
                "id": str(case_study['id']),
                "blog": case_study['blog'],
                "status": case_study['status'],
                "date": case_study['date'].isoformat() if case_study['date'] else None,
                "keyword": case_study['keyword'],
                "preview": case_study['preview'],
                "slug": case_study['slug'],
                "type": case_study['type'],
                "redirect_url": case_study['redirect_url'],
                "isdeleted": case_study['isdeleted'],
                "created_at": case_study['created_at'].isoformat() if case_study['created_at'] else None,
                "updated_at": case_study['updated_at'].isoformat() if case_study['updated_at'] else None
            }
            for case_study in case_studies
        ]
        
        return {"status": "success", "case_studies": case_studies_list, "count": len(case_studies_list)}
        
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in get_case_studies: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in get_case_studies: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/case-studies", status_code=201)
async def create_case_study(case_study_data: CreateCaseStudyRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Create a new case study
    Requires case study content as JSONB
    Optional fields: status, keyword, redirect_url
    """
    logger.info(f"Creating new case study with status: {case_study_data.status}")
    
    if not case_study_data.blog:
        raise HTTPException(status_code=400, detail="Case study content is required")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        case_study_content = case_study_data.blog.copy() if case_study_data.blog else {}
        content_type = case_study_content.get('contentType', ContentTypeConstants.CASE_STUDY)
        
        new_case_study = await conn.fetchrow(
            """
            INSERT INTO case_studies (blog, status, keyword, preview, editors_choice, slug, type, redirect_url, isdeleted)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, FALSE)
            RETURNING id, blog, status, date, keyword, preview, editors_choice, slug, type, redirect_url, isdeleted, created_at, updated_at
            """,
            json.dumps(case_study_content),
            case_study_data.status,
            json.dumps(case_study_data.keyword),
            json.dumps(case_study_data.preview) if case_study_data.preview else None,
            case_study_data.editors_choice,
            case_study_data.slug,
            content_type,
            case_study_data.redirect_url
        )
        
        await conn.close()
        
        logger.info(f"Case study created successfully with ID: {new_case_study['id']}")
        return {
            "status": "success",
            "message": "Case study created successfully",
            "case_study": {
                "id": str(new_case_study['id']),
                "blog": new_case_study['blog'],
                "status": new_case_study['status'],
                "date": new_case_study['date'].isoformat() if new_case_study['date'] else None,
                "keyword": new_case_study['keyword'],
                "preview": new_case_study['preview'],
                "slug": new_case_study['slug'],
                "type": new_case_study['type'],
                "redirect_url": new_case_study['redirect_url'],
                "isdeleted": new_case_study['isdeleted'],
                "created_at": new_case_study['created_at'].isoformat() if new_case_study['created_at'] else None,
                "updated_at": new_case_study['updated_at'].isoformat() if new_case_study['updated_at'] else None
            }
        }
        
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in create_case_study: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in create_case_study: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/case-studies/{case_study_id}")
async def update_case_study(case_study_id: str, case_study_data: UpdateCaseStudyRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Update an existing case study
    Only updates provided fields (partial update)
    Cannot update soft-deleted case studies
    """
    logger.info(f"Updating case study ID: {case_study_id}")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        existing_case_study = await conn.fetchrow(
            "SELECT id, isdeleted FROM case_studies WHERE id = $1",
            case_study_id
        )
        
        if not existing_case_study:
            await conn.close()
            raise HTTPException(status_code=404, detail="Case study not found")
        
        if existing_case_study['isdeleted']:
            await conn.close()
            raise HTTPException(status_code=400, detail="Cannot update deleted case study")
        
        update_fields = []
        update_values = []
        param_count = 1
        
        if case_study_data.blog is not None:
            update_fields.append(f"blog = ${param_count}")
            update_values.append(json.dumps(case_study_data.blog))
            param_count += 1
        
        if case_study_data.status is not None:
            update_fields.append(f"status = ${param_count}")
            update_values.append(case_study_data.status)
            param_count += 1
        
        if case_study_data.keyword is not None:
            update_fields.append(f"keyword = ${param_count}")
            update_values.append(json.dumps(case_study_data.keyword))
            param_count += 1
        
        if case_study_data.preview is not None:
            update_fields.append(f"preview = ${param_count}")
            update_values.append(json.dumps(case_study_data.preview))
            param_count += 1
        
        if case_study_data.slug is not None:
            update_fields.append(f"slug = ${param_count}")
            update_values.append(case_study_data.slug)
            param_count += 1
        
        if case_study_data.editors_choice is not None:
            update_fields.append(f"editors_choice = ${param_count}")
            update_values.append(case_study_data.editors_choice)
            param_count += 1
        
        if case_study_data.redirect_url is not None:
            update_fields.append(f"redirect_url = ${param_count}")
            update_values.append(case_study_data.redirect_url)
            param_count += 1
        
        if not update_fields:
            await conn.close()
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_fields.append(f"updated_at = CURRENT_TIMESTAMP")
        update_values.append(case_study_id)
        
        query = f"""
            UPDATE case_studies
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, blog, status, date, keyword, preview, slug, type, redirect_url, isdeleted, created_at, updated_at
        """
        
        updated_case_study = await conn.fetchrow(query, *update_values)
        await conn.close()
        
        logger.info(f"Case study updated successfully: {case_study_id}")
        return {
            "status": "success",
            "message": "Case study updated successfully",
            "case_study": {
                "id": str(updated_case_study['id']),
                "blog": updated_case_study['blog'],
                "status": updated_case_study['status'],
                "date": updated_case_study['date'].isoformat() if updated_case_study['date'] else None,
                "keyword": updated_case_study['keyword'],
                "preview": updated_case_study['preview'],
                "slug": updated_case_study['slug'],
                "type": updated_case_study['type'],
                "redirect_url": updated_case_study['redirect_url'],
                "isdeleted": updated_case_study['isdeleted'],
                "created_at": updated_case_study['created_at'].isoformat() if updated_case_study['created_at'] else None,
                "updated_at": updated_case_study['updated_at'].isoformat() if updated_case_study['updated_at'] else None
            }
        }
        
    except HTTPException:
        raise
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in update_case_study: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in update_case_study: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.patch("/case-studies/{case_study_id}")
async def partial_update_case_study(case_study_id: str, case_study_data: UpdateCaseStudyRequest, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Partial update of an existing case study (alias for PUT endpoint)
    Only updates provided fields
    Cannot update soft-deleted case studies
    """
    return await update_case_study(case_study_id, case_study_data)

@router.delete("/case-studies/{case_study_id}")
async def delete_case_study(case_study_id: str, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Permanently delete a case study from the database
    This action cannot be undone
    """
    logger.warning(f"Permanently deleting case study ID: {case_study_id}")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        case_study = await conn.fetchrow(
            "SELECT id FROM case_studies WHERE id = $1",
            case_study_id
        )
        
        if not case_study:
            await conn.close()
            raise HTTPException(status_code=404, detail="Case study not found")
        
        await conn.execute(
            "DELETE FROM case_studies WHERE id = $1",
            case_study_id
        )
        
        await conn.close()
        
        logger.info(f"Case study permanently deleted successfully: {case_study_id}")
        return {
            "status": "success",
            "message": "Case study deleted successfully"
        }
        
    except HTTPException:
        raise
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in delete_case_study: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in delete_case_study: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/case-studies/{case_study_id}/restore")
async def restore_case_study(case_study_id: str, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Restore a soft-deleted case study
    Sets isdeleted back to FALSE
    """
    logger.info(f"Restoring case study ID: {case_study_id}")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        case_study = await conn.fetchrow(
            "SELECT id, isdeleted FROM case_studies WHERE id = $1",
            case_study_id
        )
        
        if not case_study:
            await conn.close()
            raise HTTPException(status_code=404, detail="Case study not found")
        
        if not case_study['isdeleted']:
            await conn.close()
            raise HTTPException(status_code=400, detail="Case study is not deleted")
        
        await conn.execute(
            """
            UPDATE case_studies
            SET isdeleted = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            case_study_id
        )
        
        await conn.close()
        
        logger.info(f"Case study restored successfully: {case_study_id}")
        return {
            "status": "success",
            "message": "Case study restored successfully"
        }
        
    except HTTPException:
        raise
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in restore_case_study: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in restore_case_study: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin_save_case_study")
async def admin_save_case_study(request: Request, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Save case study from admin panel (Draft or Publish)
    Receives complete case study data from frontend and saves to database
    Preserves all original JSON key names
    Generates slug from title field
    """
    try:
        data = await request.json()
        
        logger.debug("=" * 80)
        logger.debug("RECEIVED CASE STUDY DATA FROM FRONTEND:")
        logger.debug(json.dumps(data, indent=2))
        logger.debug(f"Data keys: {list(data.keys())}")
        logger.debug(f"Status field: {data.get('blogStatus', 'NOT FOUND')}")
        logger.debug("=" * 80)
        
        case_study_title = data.get('blogTitle', '')
        if not case_study_title:
            raise HTTPException(status_code=400, detail="Case study title is required")
        
        case_study_id = data.get('blog_id')
        reason = data.get('reason', 'create')
        
        slug = generate_slug(case_study_title)
        case_study_status = data.get('blogStatus', StatusConstants.DRAFT)
        content_type = data.get('contentType', ContentTypeConstants.CASE_STUDY)
        
        data['contentType'] = content_type
        
        conn = await asyncpg.connect(DATABASE_URL)
        
        try:
            if reason == 'update' and case_study_id:
                existing_case_study = await conn.fetchrow(
                    "SELECT id, slug FROM case_studies WHERE id = $1 AND isdeleted = FALSE",
                    case_study_id
                )
                
                if not existing_case_study:
                    raise HTTPException(status_code=404, detail="Case study not found for update")
                
                existing_slug = existing_case_study['slug']
                if slug != existing_slug:
                    existing_slug_record = await conn.fetchrow(
                        "SELECT id FROM case_studies WHERE slug = $1 AND id != $2 AND isdeleted = FALSE",
                        slug,
                        case_study_id
                    )
                    
                    if existing_slug_record:
                        original_slug = slug
                        counter = 1
                        while existing_slug_record:
                            slug = f"{original_slug}-{counter}"
                            existing_slug_record = await conn.fetchrow(
                                "SELECT id FROM case_studies WHERE slug = $1 AND id != $2 AND isdeleted = FALSE",
                                slug,
                                case_study_id
                            )
                            counter += 1
                        logger.info(f"Generated unique slug: {slug}")
                
                preview_data = data.get('previewData')
                
                updated_case_study = await conn.fetchrow(
                    """
                    UPDATE case_studies
                    SET blog = $1, status = $2, preview = $3, editors_choice = $4, slug = $5, type = $6, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $7
                    RETURNING id, blog, status, date, keyword, preview, editors_choice, slug, type, redirect_url, isdeleted, created_at, updated_at
                    """,
                    json.dumps(data),
                    case_study_status,
                    json.dumps(preview_data) if preview_data else None,
                    data.get('editors_choice', 'N'),
                    slug,
                    content_type,
                    case_study_id
                )
                
                if not updated_case_study:
                    raise HTTPException(status_code=404, detail="Case study not found for update")
                
                case_study_id = str(updated_case_study['id'])
                case_study_url = f"{config.BACKEND_URL}/case-study/{slug}"
                
                logger.info(f"Case study updated successfully - ID: {case_study_id}, slug: {slug}, status: {case_study_status}, type: {content_type}, URL: {case_study_url}")
                
                return {
                    "status": "success",
                    "message": f"Case study {'published' if case_study_status == StatusConstants.PUBLISHED else 'updated'} successfully",
                    "blog_id": case_study_id,
                    "slug": slug,
                    "url": case_study_url
                }
            else:
                existing_case_study = await conn.fetchrow(
                    "SELECT id FROM case_studies WHERE slug = $1 AND isdeleted = FALSE",
                    slug
                )
                
                if existing_case_study:
                    original_slug = slug
                    counter = 1
                    while existing_case_study:
                        slug = f"{original_slug}-{counter}"
                        existing_case_study = await conn.fetchrow(
                            "SELECT id FROM case_studies WHERE slug = $1 AND isdeleted = FALSE",
                            slug
                        )
                        counter += 1
                    logger.info(f"Generated unique slug: {slug}")
            
                preview_data = data.get('previewData')
                
                new_case_study = await conn.fetchrow(
                    """
                    INSERT INTO case_studies (blog, status, preview, editors_choice, slug, type, isdeleted)
                    VALUES ($1, $2, $3, $4, $5, $6, FALSE)
                    RETURNING id, blog, status, date, keyword, preview, editors_choice, slug, type, redirect_url, isdeleted, created_at, updated_at
                    """,
                    json.dumps(data),
                    case_study_status,
                    json.dumps(preview_data) if preview_data else None,
                    data.get('editors_choice', 'N'),
                    slug,
                    content_type
                )
                
                case_study_id = str(new_case_study['id'])
                case_study_url = f"{config.BACKEND_URL}/case-study/{slug}"
                
                logger.info(f"Case study saved successfully - ID: {case_study_id}, slug: {slug}, status: {case_study_status}, type: {content_type}, URL: {case_study_url}")
                
                return {
                    "status": "success",
                    "message": f"Case study {'published' if case_study_status == StatusConstants.PUBLISHED else 'saved as draft'} successfully",
                    "blog_id": case_study_id,
                    "slug": slug,
                    "url": case_study_url
                }
            
        finally:
            await conn.close()
        
    except HTTPException:
        raise
    except asyncpg.UniqueViolationError:
        logger.warning("Slug already exists")
        raise HTTPException(status_code=400, detail="A case study with this title already exists")
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in admin_save_case_study: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in admin_save_case_study: {e}")
        raise HTTPException(status_code=500, detail=str(e))