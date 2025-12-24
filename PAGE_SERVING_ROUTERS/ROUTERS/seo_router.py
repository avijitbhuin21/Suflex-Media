"""
SEO Router - Serves robots.txt and sitemap.xml for search engine optimization.
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response
from datetime import datetime

router = APIRouter()


@router.get("/robots.txt", response_class=PlainTextResponse)
async def serve_robots_txt():
    """
    Serve robots.txt file to control search engine crawling.
    Blocks admin pages, API endpoints, login page, and landing page.
    """
    robots_content = """# robots.txt for Suflex Media
# https://suflexmedia.com

User-agent: *
Allow: /

# Block admin pages
Disallow: /admin/
Disallow: /admin-homepage
Disallow: /admin-users
Disallow: /admin-blogs
Disallow: /admin-case-studies
Disallow: /admin-pdf-downloads

# Block API endpoints
Disallow: /api/

# Block login page
Disallow: /login

# Block landing pages (campaign-specific)
Disallow: /ghostwriting-landing
Disallow: /lp/book-v1
Disallow: /lp/linkedin-v1

# Sitemap location
Sitemap: https://suflexmedia.com/sitemap.xml
"""
    return PlainTextResponse(content=robots_content, media_type="text/plain")


@router.get("/sitemap.xml")
async def serve_sitemap_xml():
    """
    Dynamically generate sitemap.xml with all public pages.
    Includes static pages, service pages, and should eventually include blog posts.
    """
    base_url = "https://suflexmedia.com"
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Define all public pages with their priority and change frequency
    pages = [
        # Main pages (high priority)
        {"loc": "/", "priority": "1.0", "changefreq": "weekly"},
        {"loc": "/about", "priority": "0.8", "changefreq": "monthly"},
        {"loc": "/contact", "priority": "0.8", "changefreq": "monthly"},
        {"loc": "/case-studies", "priority": "0.8", "changefreq": "weekly"},
        {"loc": "/blogs", "priority": "0.9", "changefreq": "daily"},
        
        # Service pages (medium-high priority)
        {"loc": "/ghostwriting", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/linkedin-branding", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/content-writing", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/performance-marketing", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/website-development", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/seo", "priority": "0.7", "changefreq": "monthly"},
        
        # Legal pages (low priority)
        {"loc": "/cancellation-and-refund-policy", "priority": "0.3", "changefreq": "yearly"},
        {"loc": "/terms-of-service", "priority": "0.3", "changefreq": "yearly"},
        {"loc": "/privacy-policy", "priority": "0.3", "changefreq": "yearly"},
    ]
    
    # Build XML sitemap
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for page in pages:
        xml_content += "  <url>\n"
        xml_content += f"    <loc>{base_url}{page['loc']}</loc>\n"
        xml_content += f"    <lastmod>{current_date}</lastmod>\n"
        xml_content += f"    <changefreq>{page['changefreq']}</changefreq>\n"
        xml_content += f"    <priority>{page['priority']}</priority>\n"
        xml_content += "  </url>\n"
    
    xml_content += "</urlset>"
    
    return Response(content=xml_content, media_type="application/xml")
