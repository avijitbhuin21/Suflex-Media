from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, HTMLResponse
from typing import Dict, Optional
import asyncpg
import os
import json

from DATABASE_HANDLER.utils.generate_blog_sections import get_blogs_html, get_home_insights_html
from DATABASE_HANDLER.utils.generate_case_study_sections import generate_case_studies_html, get_case_study_for_home, generate_home_case_study_html
from config import config

router = APIRouter()
DATABASE_URL = os.getenv("POSTGRES_CONNECTION_URL")

STATIC_PAGES: Dict[str, str] = {
    "/about": "PAGE_SERVING_ROUTERS/PAGES/about_us.html",
    "/content-writing": "PAGE_SERVING_ROUTERS/PAGES/Content_writing.html",
    "/ghostwriting": "PAGE_SERVING_ROUTERS/PAGES/Book_writing.html",
    "/linkedin-branding": "PAGE_SERVING_ROUTERS/PAGES/LinkedIn_branding.html",
    "/performance-marketing": "PAGE_SERVING_ROUTERS/PAGES/Performance_marketing.html",
    "/seo": "PAGE_SERVING_ROUTERS/PAGES/SEO.html",
    "/website-development": "PAGE_SERVING_ROUTERS/PAGES/Website_development.html",
    "/contact": "PAGE_SERVING_ROUTERS/PAGES/contact_us.html",
    "/cancellation-and-refund-policy": "PAGE_SERVING_ROUTERS/PAGES/cancellation_and_refund_policy.html",
    "/terms-of-service": "PAGE_SERVING_ROUTERS/PAGES/terms_of_service.html",
    "/privacy-policy": "PAGE_SERVING_ROUTERS/PAGES/privacy_policy.html",
    "/admin/pdf-downloads": "PAGE_SERVING_ROUTERS/PAGES/admin_pdf_downloads.html",
    "/thank-you": "PAGE_SERVING_ROUTERS/PAGES/thank_you.html"
}
def create_page_route(route_path: str, html_file: str):
    """
    Factory function to create a static page route handler
    
    Args:
        route_path: The URL path for the route
        html_file: The file path to the HTML file to serve
        
    Returns:
        Async function that returns FileResponse
    """
    async def page_handler():
        return FileResponse(html_file)
    return page_handler



for route_path, html_file in STATIC_PAGES.items():
    router.add_api_route(
        route_path,
        create_page_route(route_path, html_file),
        methods=["GET"],
        name=f"serve_{route_path.replace('/', '_').strip('_')}_page"
    )

CATEGORY_MAPPING = {
    "linkedin-branding": "LinkedIn Branding",
    "ghostwriting": "Ghostwriting",
    "performance-marketing": "Performance Marketing",
    "website-development": "Website Development",
}

@router.get("/case-studies", response_class=HTMLResponse)
async def get_portfolio_page(category: Optional[str] = Query(None, description="Filter case studies by category")):
    """
    Serve portfolio page with dynamically fetched case studies
    Optionally filters by category when provided
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        per_page = 4
        
        mapped_category = CATEGORY_MAPPING.get(category) if category else None
        
        if mapped_category:
            query = """
                SELECT slug, preview, category
                FROM case_studies
                WHERE isdeleted = FALSE
                    AND status = 'published'
                    AND type = 'CASE STUDY'
                    AND LOWER(category) = LOWER($2)
                ORDER BY
                    CASE WHEN editors_choice = 'Y' THEN 0 ELSE 1 END,
                    date DESC
                LIMIT $1
            """
            case_studies = await conn.fetch(query, per_page, mapped_category)
            
            count_query = """
                SELECT COUNT(*)
                FROM case_studies
                WHERE isdeleted = FALSE
                    AND status = 'published'
                    AND type = 'CASE STUDY'
                    AND LOWER(category) = LOWER($1)
            """
            total_count = await conn.fetchval(count_query, mapped_category)
        else:
            query = """
                SELECT slug, preview, category
                FROM case_studies
                WHERE isdeleted = FALSE
                    AND status = 'published'
                    AND type = 'CASE STUDY'
                ORDER BY
                    CASE WHEN editors_choice = 'Y' THEN 0 ELSE 1 END,
                    date DESC
                LIMIT $1
            """
            case_studies = await conn.fetch(query, per_page)
            
            count_query = """
                SELECT COUNT(*)
                FROM case_studies
                WHERE isdeleted = FALSE
                    AND status = 'published'
                    AND type = 'CASE STUDY'
            """
            total_count = await conn.fetchval(count_query)
        
        await conn.close()
        
        case_studies_list = []
        for record in case_studies:
            preview = record['preview']
            if isinstance(preview, str):
                try:
                    preview = json.loads(preview)
                except:
                    preview = {}
            
            case_studies_list.append({
                'slug': record['slug'],
                'preview': preview,
                'category': record['category'] if record['category'] else ''
            })
        
        case_studies_html = generate_case_studies_html(case_studies_list)
        
        total_pages = (total_count + per_page - 1) // per_page
        
        with open("PAGE_SERVING_ROUTERS/PAGES/portfolio.html", "r", encoding="utf-8") as file:
            html_content = file.read()
        
        html_content = html_content.replace(
            '<!-- CASE STUDIES WILL BE INSERTED HERE DYNAMICALLY -->',
            case_studies_html
        )
        
        html_content = html_content.replace(
            '<!-- PAGINATION WILL BE GENERATED DYNAMICALLY -->',
            f'<span style="display:none" id="totalPages">{total_pages}</span>'
        )
        
        category_value = category if category else ''
        html_content = html_content.replace(
            '<!-- CATEGORY FILTER WILL BE INSERTED HERE -->',
            f'<span style="display:none" id="currentCategory">{category_value}</span>'
        )
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        print(f"Error loading portfolio page: {e}")
        return FileResponse("PAGE_SERVING_ROUTERS/PAGES/portfolio.html")

@router.get("/", response_class=HTMLResponse)
async def get_homepage():
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        _, _, _, _, _, blog_home_data = await get_blogs_html()
        home_insights_html = await get_home_insights_html(blog_home_data)

        latest_case_study = await get_case_study_for_home(conn)
        case_study_title_html, case_study_summary_html, read_more_button_html, image_url = generate_home_case_study_html(latest_case_study)

        with open("PAGE_SERVING_ROUTERS/PAGES/home.html", "r", encoding="utf-8") as file:
            html_content = file.read()
        
        html_content = html_content.replace(
            '<!-- TOP EDITOR\'S CHOICE BLOGS WILL BE INSERTED HERE DYNAMICALLY -->',
            home_insights_html
        )
        
        html_content = html_content.replace(
            '<!-- CASE STUDY TITLE WILL BE INSERTED HERE DYNAMICALLY -->',
            case_study_title_html
        )
        
        html_content = html_content.replace(
            '<!-- CASE STUDY SUMMARY WILL BE INSERTED HERE DYNAMICALLY -->',
            case_study_summary_html
        )

        html_content = html_content.replace(
            '<!-- READ MORE BUTTON WILL BE INSERTED HERE DYNAMICALLY -->',
            read_more_button_html
        )
        html_content = html_content.replace(
            '[[[imageURL]]]',
            image_url
        )

        return HTMLResponse(content=html_content)
    except Exception as e:
        print(f"Error loading homepage: {e}")
        # Fallback to serving the static file if there's an error
        return FileResponse("PAGE_SERVING_ROUTERS/PAGES/home.html")
    finally:
        if conn:
            await conn.close()