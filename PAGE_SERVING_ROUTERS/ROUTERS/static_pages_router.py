from fastapi import APIRouter
from fastapi.responses import FileResponse
from typing import Dict

router = APIRouter()

STATIC_PAGES: Dict[str, str] = {
    "/about": "PAGE_SERVING_ROUTERS/PAGES/about_us.html",
    "/content-writing": "PAGE_SERVING_ROUTERS/PAGES/Content_writing.html",
    "/ghostwriting": "PAGE_SERVING_ROUTERS/PAGES/Book_writing.html",
    "/": "PAGE_SERVING_ROUTERS/PAGES/home.html",
    "/landing": "PAGE_SERVING_ROUTERS/PAGES/landing_page.html",
    "/linkedin-branding": "PAGE_SERVING_ROUTERS/PAGES/LinkedIn_branding.html",
    "/performance-marketing": "PAGE_SERVING_ROUTERS/PAGES/Performance_marketing.html",
    "/portfolio": "PAGE_SERVING_ROUTERS/PAGES/portfolio.html",
    "/seo": "PAGE_SERVING_ROUTERS/PAGES/SEO.html",
    "/website-development": "PAGE_SERVING_ROUTERS/PAGES/Website_development.html",
    "/contact": "PAGE_SERVING_ROUTERS/PAGES/contact_us.html",
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