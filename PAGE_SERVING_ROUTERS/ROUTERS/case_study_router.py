import asyncpg
import json
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
DATABASE_URL = os.getenv("POSTGRES_CONNECTION_URL")


def sanitize_html_preserve_formatting(html_content: str) -> str:
    """
    Sanitize HTML content while preserving text formatting (bold, italic, underline)
    Converts inline styled spans to semantic HTML tags
    """
    if not html_content:
        return ""
    
    content = html_content
    
    content = re.sub(r'<!--StartFragment-->', '', content)
    content = re.sub(r'<!--EndFragment-->', '', content)
    content = re.sub(r'<meta[^>]*?>', '', content)
    content = re.sub(r'<br\s+class=[^>]*?>', '<br>', content)
    content = re.sub(r'<div[^>]*?></div>', '', content)
    content = re.sub(r'<div[^>]*?>', '', content)
    content = re.sub(r'</div>', '', content)
    
    content = re.sub(r'<b[^>]*?style="font-weight:normal;"[^>]*?>', '', content)
    content = re.sub(r'<b[^>]*?>', '', content)
    content = re.sub(r'</b>', '', content)
    
    def convert_styled_span(match):
        style = match.group(1) if match.lastindex >= 1 else ''
        inner_content = match.group(2) if match.lastindex >= 2 else ''
        
        if not inner_content:
            return ''
        
        tags_open = []
        tags_close = []
        
        if 'font-weight: 700' in style or 'font-weight:700' in style:
            tags_open.append('<strong>')
            tags_close.insert(0, '</strong>')
        
        if 'font-style: italic' in style or 'font-style:italic' in style:
            tags_open.append('<em>')
            tags_close.insert(0, '</em>')
        
        if 'text-decoration: underline' in style or 'text-decoration:underline' in style:
            tags_open.append('<u>')
            tags_close.insert(0, '</u>')
        
        if tags_open:
            return ''.join(tags_open) + inner_content + ''.join(tags_close)
        return inner_content
    
    content = re.sub(
        r'<span[^>]*?style="([^"]*?)"[^>]*?>(.*?)</span>',
        convert_styled_span,
        content,
        flags=re.DOTALL
    )
    
    content = re.sub(r'<span[^>]*?>(.*?)</span>', r'\1', content, flags=re.DOTALL)
    
    content = re.sub(r'&nbsp;', ' ', content)
    content = re.sub(r'&amp;', '&', content)
    content = re.sub(r'&lt;', '<', content)
    content = re.sub(r'&gt;', '>', content)
    content = re.sub(r'&quot;', '"', content)
    
    content = re.sub(r'\s+', ' ', content)
    content = content.strip()
    
    return content


def strip_html_tags(html_content: str) -> str:
    """
    Remove HTML tags from content and return plain text
    DEPRECATED: Use sanitize_html_preserve_formatting() instead
    """
    if not html_content:
        return ""
    
    clean_text = re.sub(r'<[^>]+>', '', html_content)
    clean_text = re.sub(r'&nbsp;', ' ', clean_text)
    clean_text = re.sub(r'&amp;', '&', clean_text)
    clean_text = re.sub(r'&lt;', '<', clean_text)
    clean_text = re.sub(r'&gt;', '>', clean_text)
    clean_text = re.sub(r'&quot;', '"', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    return clean_text.strip()


def parse_blog_json(blog_json_str: str) -> Dict[str, Any]:
    """
    Parse the blog JSON string into a dictionary
    """
    try:
        return json.loads(blog_json_str)
    except (json.JSONDecodeError, TypeError):
        return {}


def format_date(date_str: str) -> tuple[str, str]:
    """
    Format date string to human-readable format and ISO format
    Returns tuple of (formatted_date, iso_date)
    """
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        formatted = date_obj.strftime("%B %d, %Y")
        iso = date_obj.strftime("%Y-%m-%d")
        return formatted, iso
    except:
        return "Unknown Date", "2025-01-01"


def generate_head_section(blog_data: Dict[str, Any], case_study_date: str) -> str:
    """
    Generate the HTML head section with meta tags, SEO, and structured data
    """
    title = blog_data.get('seoTitle', blog_data.get('blogTitle', 'Case Study'))
    description = blog_data.get('seoMetaDescription', blog_data.get('seoTitle', ''))
    image_url = blog_data.get('mainImageUrl', 'https://picsum.photos/1920/1080/?random=123')
    formatted_date, iso_date = format_date(case_study_date)
    
    return f"""<!doctype html>
<html lang="en">

<head>
    <meta charset="utf-8" />
    <title>{title}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />

    <meta name="description" content="{description}" />
    <meta property="og:title" content="{title}" />
    <meta property="og:description" content="{description}" />
    <meta property="og:type" content="article" />
    <meta property="og:image" content="{image_url}" />
    <meta property="twitter:card" content="summary_large_image" />
    <meta property="twitter:title" content="{title}" />
    <meta property="twitter:description" content="{description}" />
    <meta property="twitter:image" content="{image_url}" />

    <link rel="preconnect" href="https://fonts.googleapis.com" crossorigin />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
        href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700;800;900&family=Source+Sans+Pro:wght@300;400;600;700&display=swap"
        rel="stylesheet" />
    <link rel="stylesheet" href="/css/case_study.css" />

    <script type="application/ld+json">
        {{
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "{title}",
            "datePublished": "{iso_date}",
            "description": "{description}",
            "image": ["{image_url}"],
            "articleSection": "CASE STUDY"
        }}
  </script>
</head>

<body>
    <a href="#main" class="visually-hidden">Skip to content</a>

    <main id="main" class="wrap" role="main" aria-labelledby="title">"""


def generate_article_header(blog_data: Dict[str, Any], case_study_date: str) -> str:
    """
    Generate the article header section with kicker, title, and date
    """
    title = blog_data.get('blogTitle', 'Case Study')
    content_type = blog_data.get('contentType', 'Case Study')
    formatted_date, iso_date = format_date(case_study_date)
    
    return f"""
        <header class="article-header">
            <span class="kicker" aria-label="Content type">
                <span class="dot" aria-hidden="true"></span>
                {content_type}
            </span>
            <h1 id="title" class="title">{title}</h1>
            <div class="meta">
                <span>Published: <time datetime="{iso_date}">{formatted_date}</time></span>
            </div>
        </header>"""


def generate_hero_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the hero section with featured image and caption
    """
    image_url = blog_data.get('mainImageUrl', 'https://picsum.photos/1920/1080/?random=123')
    image_alt = blog_data.get('mainImageAlt', 'Case study featured image')
    title = blog_data.get('blogTitle', 'Case Study')
    
    return f"""
        <section class="hero" aria-label="Featured image">
            <figure>
                <img src="{image_url}"
                    alt="{image_alt}" />
                <figcaption>{title}</figcaption>
            </figure>
        </section>"""


def generate_summary_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the summary/lead section
    """
    preview_data = blog_data.get('previewData', {})
    summary = preview_data.get('summary', '')
    clean_summary = sanitize_html_preserve_formatting(summary)
    
    if not clean_summary:
        return ""
    
    return f"""
        <section aria-label="Summary">
            <div class="lead">
                {clean_summary}
            </div>
        </section>"""


def generate_vision_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the vision section
    """
    structured_content = blog_data.get('structuredContent', {})
    vision_html = structured_content.get('theVision', '')
    vision_text = sanitize_html_preserve_formatting(vision_html)
    
    if not vision_text:
        return ""
    
    return f"""
        <section class="section" aria-label="Vision">
            <h2>The Vision</h2>
            <div class="prose">
                {vision_text}
            </div>
        </section>"""


def generate_process_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the process section with intro, steps, and conclusion
    """
    structured_content = blog_data.get('structuredContent', {})
    our_process = structured_content.get('ourProcess', {})
    
    if not our_process:
        return ""
    
    intro_html = our_process.get('intro', '')
    intro_text = sanitize_html_preserve_formatting(intro_html)
    
    steps = our_process.get('steps', [])
    steps_html = ""
    for step in steps:
        step_text = sanitize_html_preserve_formatting(step)
        if step_text:
            steps_html += f"                    <li>{step_text}</li>\n"
    
    conclusion_html = our_process.get('conclusion', '')
    conclusion_text = sanitize_html_preserve_formatting(conclusion_html)
    
    if not intro_text and not steps_html and not conclusion_text:
        return ""
    
    section = f"""
        <section class="section" aria-label="Our process">
            <h2>Our Process</h2>
            <div class="process">"""
    
    if intro_text:
        section += f"""
                {intro_text}"""
    
    if steps_html:
        section += f"""
                <ol class="steps">
{steps_html}                </ol>"""
    
    if conclusion_text:
        section += f"""
                {conclusion_text}"""
    
    section += """
            </div>
        </section>"""
    
    return section


def generate_story_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the story section with dynamic h3 subsections
    """
    structured_content = blog_data.get('structuredContent', {})
    the_story = structured_content.get('theStory', [])
    
    if not the_story:
        return ""
    
    section = f"""
        <section class="section" aria-label="The story we told">
            <h2>The Story We Told</h2>
            <div class="prose">"""
    
    for item in the_story:
        if item.get('type') == 'h3':
            title = item.get('title', '')
            content_html = item.get('content', '')
            content_text = sanitize_html_preserve_formatting(content_html)
            
            if title and content_text:
                section += f"""
                <h3>{title}</h3>
                {content_text}
"""
    
    section += """            </div>
        </section>"""
    
    return section


def generate_result_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the result section
    """
    structured_content = blog_data.get('structuredContent', {})
    result_html = structured_content.get('theResult', '')
    result_text = sanitize_html_preserve_formatting(result_html)
    
    if not result_text:
        return ""
    
    section = f"""
        <section class="section" aria-label="Result">
            <h2>The Result</h2>
            <div class="result">
                {result_text}
            </div>
        </section>"""
    
    return section


def generate_impact_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the impact section with list items
    """
    structured_content = blog_data.get('structuredContent', {})
    the_impact = structured_content.get('theImpact', [])
    
    if not the_impact:
        return ""
    
    section = f"""
        <section class="section" aria-label="Impact">
            <h2>The Impact</h2>
            <ul class="impact-list">"""
    
    for impact_item_html in the_impact:
        impact_text = sanitize_html_preserve_formatting(impact_item_html)
        if impact_text:
            section += f"""
                <li class="impact-item">
                    <span>{impact_text}</span>
                </li>"""
    
    section += """
            </ul>
        </section>"""
    
    return section


def generate_footer_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the footer section
    """
    title = blog_data.get('blogTitle', 'Case Study')
    
    return f"""
        <footer class="page-footer">
            © 2025 • Case Study • {title}
        </footer>
    </main>
</body>

</html>"""


def assemble_case_study_html(case_study_data: Dict[str, Any]) -> str:
    """
    Main orchestrator function that assembles all HTML sections into complete page
    """
    blog_json_str = case_study_data.get('blog', '{}')
    blog_data = parse_blog_json(blog_json_str)
    case_study_date = case_study_data.get('date', '')
    
    html_parts = [
        generate_head_section(blog_data, case_study_date),
        generate_article_header(blog_data, case_study_date),
        generate_hero_section(blog_data),
        generate_summary_section(blog_data),
        generate_vision_section(blog_data),
        generate_process_section(blog_data),
        generate_story_section(blog_data),
        generate_result_section(blog_data),
        generate_impact_section(blog_data),
        generate_footer_section(blog_data)
    ]
    
    return ''.join(html_parts)


async def fetch_case_study(identifier: str, by_slug: bool = True) -> Optional[Dict[str, Any]]:
    """
    Fetch case study from database by ID or slug
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        if by_slug:
            query = """
                SELECT id, slug, blog, status, type, date, keyword, preview, 
                       editors_choice, redirect_url, isdeleted, created_at, updated_at
                FROM case_studies
                WHERE slug = $1 AND isdeleted = FALSE
                LIMIT 1
            """
        else:
            query = """
                SELECT id, slug, blog, status, type, date, keyword, preview, 
                       editors_choice, redirect_url, isdeleted, created_at, updated_at
                FROM case_studies
                WHERE id = $1 AND isdeleted = FALSE
                LIMIT 1
            """
        
        case_study = await conn.fetchrow(query, identifier)
        await conn.close()
        
        if case_study:
            return {
                "id": str(case_study['id']),
                "slug": case_study['slug'],
                "blog": case_study['blog'],
                "status": case_study['status'],
                "type": case_study['type'],
                "date": case_study['date'].isoformat() if case_study['date'] else None,
                "keyword": case_study['keyword'],
                "preview": case_study['preview'],
                "editors_choice": case_study['editors_choice'],
                "redirect_url": case_study['redirect_url'],
                "isdeleted": case_study['isdeleted'],
                "created_at": case_study['created_at'].isoformat() if case_study['created_at'] else None,
                "updated_at": case_study['updated_at'].isoformat() if case_study['updated_at'] else None
            }
        
        return None
        
    except asyncpg.PostgresError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/case-study/{slug}", response_class=HTMLResponse)
async def get_case_study_by_slug(slug: str):
    """
    FastAPI route handler to serve case study by slug
    """
    case_study_data = await fetch_case_study(slug, by_slug=True)
    
    if not case_study_data:
        raise HTTPException(status_code=404, detail="Case study not found")
    
    if case_study_data.get('status') != 'published':
        raise HTTPException(status_code=404, detail="Case study not available")
    
    html_content = assemble_case_study_html(case_study_data)
    return HTMLResponse(content=html_content, status_code=200)


@router.get("/case-study/id/{case_study_id}", response_class=HTMLResponse)
async def get_case_study_by_id(case_study_id: str):
    """
    FastAPI route handler to serve case study by ID
    """
    case_study_data = await fetch_case_study(case_study_id, by_slug=False)
    
    if not case_study_data:
        raise HTTPException(status_code=404, detail="Case study not found")
    
    if case_study_data.get('status') != 'published':
        raise HTTPException(status_code=404, detail="Case study not available")
    
    html_content = assemble_case_study_html(case_study_data)
    return HTMLResponse(content=html_content, status_code=200)