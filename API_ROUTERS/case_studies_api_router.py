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
    blogContent: Dict[str, Any]
    status: str = StatusConstants.DRAFT
    keyword: Optional[Dict[str, Any]] = None
    preview: Optional[Dict[str, Any]] = None
    editors_choice: Optional[str] = 'N'
    slug: Optional[str] = None
    redirect_url: Optional[str] = None

class UpdateCaseStudyRequest(BaseModel):
    blog: Optional[Dict[str, Any]] = None
    blogContent: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    keyword: Optional[Dict[str, Any]] = None
    preview: Optional[Dict[str, Any]] = None
    editors_choice: Optional[str] = None
    slug: Optional[str] = None
    redirect_url: Optional[str] = None
    category: Optional[str] = None

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
                SELECT id, case_study, status, date, keyword, preview, slug, type, redirect_url, pdf_url, category, editors_choice, isdeleted, created_at, updated_at
                FROM case_studies
                WHERE type = '{ContentTypeConstants.CASE_STUDY}'
                ORDER BY date DESC
            """
        else:
            query = f"""
                SELECT id, case_study, status, date, keyword, preview, slug, type, redirect_url, pdf_url, category, editors_choice, isdeleted, created_at, updated_at
                FROM case_studies
                WHERE isdeleted = FALSE AND type = '{ContentTypeConstants.CASE_STUDY}'
                ORDER BY date DESC
            """
        
        case_studies = await conn.fetch(query)
        await conn.close()
        
        case_studies_list = [
            {
                "id": str(case_study['id']),
                "blog": case_study['case_study'],
                "status": case_study['status'],
                "date": case_study['date'].isoformat() if case_study['date'] else None,
                "keyword": case_study['keyword'],
                "preview": case_study['preview'],
                "slug": case_study['slug'],
                "type": case_study['type'],
                "redirect_url": case_study['redirect_url'],
                "pdf_url": case_study['pdf_url'],
                "category": case_study['category'],
                "editors_choice": case_study['editors_choice'],
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
    
    if not case_study_data.blogContent:
        raise HTTPException(status_code=400, detail="Case study content is required")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        case_study_content = case_study_data.blogContent.copy() if case_study_data.blogContent else {}
        content_type = case_study_content.get('contentType', ContentTypeConstants.CASE_STUDY)
        
        blog_title = case_study_content.get('blogTitle')
        preview_data = case_study_data.preview
        if preview_data is None:
            preview_data = {}
        if blog_title:
            preview_data['blogTitle'] = blog_title
        
        new_case_study = await conn.fetchrow(
            """
            INSERT INTO case_studies (case_study, status, keyword, preview, editors_choice, slug, type, redirect_url, isdeleted)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, FALSE)
            RETURNING id, case_study, status, date, keyword, preview, editors_choice, slug, type, redirect_url, pdf_url, isdeleted, created_at, updated_at
            """,
            json.dumps(case_study_content),
            case_study_data.status,
            json.dumps(case_study_data.keyword),
            json.dumps(preview_data),
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
                "blog": new_case_study['case_study'],
                "status": new_case_study['status'],
                "date": new_case_study['date'].isoformat() if new_case_study['date'] else None,
                "keyword": new_case_study['keyword'],
                "preview": new_case_study['preview'],
                "slug": new_case_study['slug'],
                "type": new_case_study['type'],
                "redirect_url": new_case_study['redirect_url'],
                "pdf_url": new_case_study['pdf_url'],
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
            "SELECT id, isdeleted, case_study, preview FROM case_studies WHERE id = $1",
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
        
        blog_content = case_study_data.blog or case_study_data.blogContent
        blog_title = None
        
        if blog_content is not None:
            update_fields.append(f"case_study = ${param_count}")
            update_values.append(json.dumps(blog_content))
            param_count += 1
            blog_title = blog_content.get('blogTitle')
        else:
            current_case_study = existing_case_study['case_study']
            if current_case_study:
                blog_title = current_case_study.get('blogTitle')
        
        if case_study_data.status is not None:
            update_fields.append(f"status = ${param_count}")
            update_values.append(case_study_data.status)
            param_count += 1
        
        if case_study_data.keyword is not None:
            update_fields.append(f"keyword = ${param_count}")
            update_values.append(json.dumps(case_study_data.keyword))
            param_count += 1
        
        preview_data = case_study_data.preview
        if preview_data is None:
            preview_data = existing_case_study['preview'] or {}
        
        if blog_title:
            if preview_data is None:
                preview_data = {}
            preview_data['blogTitle'] = blog_title
            
        if preview_data is not None:
            update_fields.append(f"preview = ${param_count}")
            update_values.append(json.dumps(preview_data))
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
        
        if case_study_data.category is not None:
            update_fields.append(f"category = ${param_count}")
            update_values.append(case_study_data.category)
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
            RETURNING id, case_study, status, date, keyword, preview, slug, type, redirect_url, pdf_url, category, isdeleted, created_at, updated_at
        """
        
        updated_case_study = await conn.fetchrow(query, *update_values)
        await conn.close()
        
        logger.info(f"Case study updated successfully: {case_study_id}")
        return {
            "status": "success",
            "message": "Case study updated successfully",
            "case_study": {
                "id": str(updated_case_study['id']),
                "blog": updated_case_study['case_study'],
                "status": updated_case_study['status'],
                "date": updated_case_study['date'].isoformat() if updated_case_study['date'] else None,
                "keyword": updated_case_study['keyword'],
                "preview": updated_case_study['preview'],
                "slug": updated_case_study['slug'],
                "type": updated_case_study['type'],
                "redirect_url": updated_case_study['redirect_url'],
                "pdf_url": updated_case_study['pdf_url'],
                "category": updated_case_study['category'],
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

CATEGORY_MAPPING = {
    "linkedin-branding": "LinkedIn Branding",
    "ghostwriting": "Ghostwriting",
    "performance-marketing": "Performance Marketing",
    "website-development": "Website Development",
}

CATEGORY_DISPLAY_MAPPING = {
    "linkedin-branding": "LinkedIn Branding",
    "linkedin branding": "LinkedIn Branding",
    "linkedin_branding": "LinkedIn Branding",
    "ghostwriting": "Ghostwriting",
    "ghost writing": "Ghostwriting",
    "ghost_writing": "Ghostwriting",
    "performance-marketing": "Performance Marketing",
    "performance marketing": "Performance Marketing",
    "performance_marketing": "Performance Marketing",
    "website-development": "Website Development",
    "website development": "Website Development",
    "website_development": "Website Development",
}

def get_display_category(category: str) -> str:
    if not category:
        return ""
    category_lower = category.lower().strip()
    if category_lower in CATEGORY_DISPLAY_MAPPING:
        return CATEGORY_DISPLAY_MAPPING[category_lower]
    return category.title()

@router.get("/case-studies/paginated")
async def get_paginated_case_studies(
    page: int = Query(1, ge=1, description="Page number (starting from 1)"),
    per_page: int = Query(4, ge=1, le=20, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    Get paginated case studies for portfolio page
    Returns only published case studies with pagination
    Optionally filters by category when provided
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        offset = (page - 1) * per_page
        
        mapped_category = CATEGORY_MAPPING.get(category) if category else None
        
        if mapped_category:
            count_query = f"""
                SELECT COUNT(*)
                FROM case_studies
                WHERE isdeleted = FALSE
                    AND status = '{StatusConstants.PUBLISHED}'
                    AND type = '{ContentTypeConstants.CASE_STUDY}'
                    AND LOWER(category) = LOWER($1)
            """
            total_count = await conn.fetchval(count_query, mapped_category)
            
            query = f"""
                SELECT slug, preview, category
                FROM case_studies
                WHERE isdeleted = FALSE
                    AND status = '{StatusConstants.PUBLISHED}'
                    AND type = '{ContentTypeConstants.CASE_STUDY}'
                    AND LOWER(category) = LOWER($3)
                ORDER BY
                    CASE WHEN editors_choice = 'Y' THEN 0 ELSE 1 END,
                    date DESC
                LIMIT $1 OFFSET $2
            """
            case_studies = await conn.fetch(query, per_page, offset, mapped_category)
        else:
            count_query = f"""
                SELECT COUNT(*)
                FROM case_studies
                WHERE isdeleted = FALSE
                    AND status = '{StatusConstants.PUBLISHED}'
                    AND type = '{ContentTypeConstants.CASE_STUDY}'
            """
            total_count = await conn.fetchval(count_query)
            
            query = f"""
                SELECT slug, preview, category
                FROM case_studies
                WHERE isdeleted = FALSE
                    AND status = '{StatusConstants.PUBLISHED}'
                    AND type = '{ContentTypeConstants.CASE_STUDY}'
                ORDER BY
                    CASE WHEN editors_choice = 'Y' THEN 0 ELSE 1 END,
                    date DESC
                LIMIT $1 OFFSET $2
            """
            case_studies = await conn.fetch(query, per_page, offset)
        
        await conn.close()
        
        case_studies_list = []
        for record in case_studies:
            preview = record['preview']
            if isinstance(preview, str):
                try:
                    preview = json.loads(preview)
                except:
                    preview = {}
            
            raw_category = record['category'] or ''
            display_category = get_display_category(raw_category)
            
            case_studies_list.append({
                'slug': record['slug'],
                'preview': preview,
                'category': display_category
            })
        
        total_pages = (total_count + per_page - 1) // per_page
        
        return {
            "status": "success",
            "case_studies": case_studies_list,
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in get_paginated_case_studies: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in get_paginated_case_studies: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/case-studies/editors-choice")
async def get_editors_choice_case_studies():
    """
    Get all case studies marked as editor's choice
    Returns only published case studies with editors_choice = 'Y'
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        query = f"""
            SELECT id, case_study, status, date, keyword, preview, slug, type, redirect_url, pdf_url, category, editors_choice, isdeleted, created_at, updated_at
            FROM case_studies
            WHERE isdeleted = FALSE
            AND type = '{ContentTypeConstants.CASE_STUDY}'
            AND editors_choice = 'Y'
            ORDER BY date DESC
        """
        
        case_studies = await conn.fetch(query)
        await conn.close()
        
        case_studies_list = [
            {
                "id": str(case_study['id']),
                "blog": case_study['case_study'],
                "status": case_study['status'],
                "date": case_study['date'].isoformat() if case_study['date'] else None,
                "keyword": case_study['keyword'],
                "preview": case_study['preview'],
                "slug": case_study['slug'],
                "type": case_study['type'],
                "redirect_url": case_study['redirect_url'],
                "pdf_url": case_study['pdf_url'],
                "category": case_study['category'] or '',
                "editors_choice": case_study['editors_choice'],
                "isdeleted": case_study['isdeleted'],
                "created_at": case_study['created_at'].isoformat() if case_study['created_at'] else None,
                "updated_at": case_study['updated_at'].isoformat() if case_study['updated_at'] else None
            }
            for case_study in case_studies
        ]
        
        return {"status": "success", "case_studies": case_studies_list, "count": len(case_studies_list)}
        
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in get_editors_choice_case_studies: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in get_editors_choice_case_studies: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/case-studies/{case_study_id}/toggle-editors-choice")
async def toggle_editors_choice(case_study_id: str, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Toggle editor's choice status for a case study
    Only 1 case study can be marked as Editor's Choice at a time
    When setting a new editor's choice, the previous one is automatically unset
    """
    logger.info(f"Toggling editor's choice for case study ID: {case_study_id}")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        existing_case_study = await conn.fetchrow(
            "SELECT id, editors_choice, isdeleted FROM case_studies WHERE id = $1",
            case_study_id
        )
        
        if not existing_case_study:
            await conn.close()
            raise HTTPException(status_code=404, detail="Case study not found")
        
        if existing_case_study['isdeleted']:
            await conn.close()
            raise HTTPException(status_code=400, detail="Cannot modify deleted case study")
        
        current_status = existing_case_study['editors_choice']
        new_status = 'N' if current_status == 'Y' else 'Y'
        
        if new_status == 'Y':
            await conn.execute(
                """
                UPDATE case_studies
                SET editors_choice = 'N', updated_at = CURRENT_TIMESTAMP
                WHERE editors_choice = 'Y' AND isdeleted = FALSE AND type = $1
                """,
                ContentTypeConstants.CASE_STUDY
            )
            logger.info("Cleared previous editor's choice selection")
        
        updated_case_study = await conn.fetchrow(
            """
            UPDATE case_studies
            SET editors_choice = $1, updated_at = CURRENT_TIMESTAMP
            WHERE id = $2
            RETURNING id, case_study, status, date, keyword, preview, editors_choice, slug, type, redirect_url, pdf_url, isdeleted, created_at, updated_at
            """,
            new_status,
            case_study_id
        )
        
        await conn.close()
        
        logger.info(f"Editor's choice toggled successfully for case study: {case_study_id} to {new_status}")
        return {
            "status": "success",
            "message": f"Editor's choice {'set' if new_status == 'Y' else 'removed'} successfully",
            "editors_choice": new_status,
            "case_study": {
                "id": str(updated_case_study['id']),
                "blog": updated_case_study['case_study'],
                "status": updated_case_study['status'],
                "date": updated_case_study['date'].isoformat() if updated_case_study['date'] else None,
                "keyword": updated_case_study['keyword'],
                "preview": updated_case_study['preview'],
                "editors_choice": updated_case_study['editors_choice'],
                "slug": updated_case_study['slug'],
                "type": updated_case_study['type'],
                "redirect_url": updated_case_study['redirect_url'],
                "pdf_url": updated_case_study['pdf_url'],
                "isdeleted": updated_case_study['isdeleted'],
                "created_at": updated_case_study['created_at'].isoformat() if updated_case_study['created_at'] else None,
                "updated_at": updated_case_study['updated_at'].isoformat() if updated_case_study['updated_at'] else None
            }
        }
        
    except HTTPException:
        raise
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in toggle_editors_choice: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in toggle_editors_choice: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin_case_study_preview")
async def admin_case_study_preview(request: Request, current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Generate HTML preview for case study before saving
    Used by admin panel to preview case study content
    """
    try:
        data = await request.json()
        
        logger.debug("=" * 80)
        logger.debug("RECEIVED CASE STUDY PREVIEW REQUEST:")
        logger.debug(json.dumps(data, indent=2))
        logger.debug("=" * 80)
        
        preview_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
    <link rel="icon" type="image/png" href="/images/logo_header.png">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Case Study Preview</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                h1 {{ color: #333; }}
                h2 {{ color: #555; margin-top: 30px; }}
                .metadata {{ 
                    background: #fff; 
                    padding: 15px; 
                    border-radius: 5px; 
                    margin-bottom: 20px;
                }}
                .content {{ 
                    background: #fff; 
                    padding: 20px; 
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="metadata">
                <h1>{data.get('blogTitle', 'Untitled Case Study')}</h1>
                <p><strong>Date:</strong> {data.get('blogDate', 'N/A')}</p>
                <p><strong>Category:</strong> {data.get('blogCategory', 'N/A')}</p>
                <p><strong>Status:</strong> Preview Mode</p>
            </div>
            <div class="content">
                <div>{data.get('blogSummary', '')}</div>
            </div>
        </body>
        </html>
        """
        
        return {
            "status": "success",
            "data": preview_html
        }
        
    except Exception as e:
        logger.error(f"Error generating case study preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

        logger.error(f"Unexpected error in toggle_editors_choice: {e}")
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
                
                preview_data = data.pop('previewData', None)
                pdf_url = data.pop('pdfUrl', None)
                case_study_category = data.get('blogCategory', '')
                
                if preview_data is None:
                    preview_data = {}
                preview_data['blogTitle'] = case_study_title
                
                updated_case_study = await conn.fetchrow(
                    """
                    UPDATE case_studies
                    SET case_study = $1, status = $2, preview = $3, editors_choice = $4, slug = $5, type = $6, pdf_url = $7, category = $8, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $9
                    RETURNING id, case_study, status, date, keyword, preview, editors_choice, slug, type, redirect_url, pdf_url, category, isdeleted, created_at, updated_at
                    """,
                    json.dumps(data),
                    case_study_status,
                    json.dumps(preview_data),
                    data.get('editors_choice', 'N'),
                    slug,
                    content_type,
                    pdf_url,
                    case_study_category,
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
            
                preview_data = data.pop('previewData', None)
                pdf_url = data.pop('pdfUrl', None)
                case_study_category = data.get('blogCategory', '')
                
                if preview_data is None:
                    preview_data = {}
                preview_data['blogTitle'] = case_study_title
                
                new_case_study = await conn.fetchrow(
                    """
                    INSERT INTO case_studies (case_study, status, preview, editors_choice, slug, type, pdf_url, category, isdeleted)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, FALSE)
                    RETURNING id, case_study, status, date, keyword, preview, editors_choice, slug, type, redirect_url, pdf_url, category, isdeleted, created_at, updated_at
                    """,
                    json.dumps(data),
                    case_study_status,
                    json.dumps(preview_data),
                    data.get('editors_choice', 'N'),
                    slug,
                    content_type,
                    pdf_url,
                    case_study_category
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


class PDFDownloadFormRequest(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: str
    company_name: Optional[str] = None
    mobile_number: Optional[str] = None
    pdf_link: str


@router.post("/pdf-download-form")
async def save_pdf_download_form(form_data: PDFDownloadFormRequest):
    """
    Save PDF download form submission to database.
    Called when user fills out the download form before downloading a PDF.
    """
    logger.info(f"Saving PDF download form for email: {form_data.email}")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        await conn.execute(
            """
            INSERT INTO pdf_downloads (first_name, last_name, email, company_name, mobile_number, pdf_link)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            form_data.first_name,
            form_data.last_name or '',
            form_data.email,
            form_data.company_name or '',
            form_data.mobile_number or '',
            form_data.pdf_link
        )
        
        await conn.close()
        
        logger.info(f"PDF download form saved successfully for: {form_data.email}")
        return {
            "status": "success",
            "message": "Form submitted successfully"
        }
        
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in save_pdf_download_form: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in save_pdf_download_form: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")