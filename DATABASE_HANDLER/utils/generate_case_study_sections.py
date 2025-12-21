import re
import json
from html import unescape


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


def get_display_category(category):
    if not category:
        return ""
    category_lower = category.lower().strip()
    if category_lower in CATEGORY_DISPLAY_MAPPING:
        return CATEGORY_DISPLAY_MAPPING[category_lower]
    return category.title()


def clean_html(html_text):
    """
    Remove HTML tags and clean up text content while preserving readability
    
    Args:
        html_text: HTML string to clean
        
    Returns:
        str: Cleaned text without HTML tags
    """
    if not html_text:
        return ""
    
    text = re.sub(r'<!--.*?-->', '', html_text, flags=re.DOTALL)
    text = re.sub(r'<meta[^>]*>', '', text)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = ' '.join(text.split())
    
    return text.strip()


def generate_case_study_card(case_study_data, index):
    """
    Generate HTML card for a case study
    
    Args:
        case_study_data: Dictionary containing case study information with 'slug', 'preview', and 'category'
        index: Position index to determine light/dark theme
        
    Returns:
        str: HTML string for the case study card
    """
    slug = case_study_data.get('slug', '')
    preview = case_study_data.get('preview', {})
    raw_category = case_study_data.get('category', '')
    
    if isinstance(preview, str):
        try:
            preview = json.loads(preview)
        except:
            preview = {}
    
    image_url = preview.get('imageUrl', '/images/Frame1.jpg')
    image_alt = preview.get('imageAlt', 'Case Study')
    blog_title = preview.get('blogTitle', 'Untitled Case Study')
    text = clean_html(preview.get('text', ''))
    project_snapshots = preview.get('projectSnapshots', [])
    
    display_category = get_display_category(raw_category)
    category_badge_html = f'<span class="case-study-badge">{display_category}</span>' if display_category else ''
    
    snapshots_html = ""
    if project_snapshots:
        snapshots_html = "<ul style='margin: 10px 0; padding-left: 20px;'>"
        for snapshot in project_snapshots:
            cleaned_snapshot = clean_html(snapshot)
            if cleaned_snapshot:
                snapshots_html += f"<li style='margin: 5px 0;'>{cleaned_snapshot}</li>"
        snapshots_html += "</ul>"
    
    card_class = "case-study-card-light" if index % 2 == 0 else "dark"
    
    html = f"""
                <div class="case-study-card {card_class}">
                    <div class="case-study-image">
                        <img src="{image_url}" alt="{image_alt}">
                    </div>
                    <div class="case-study-content">
                        {category_badge_html}
                        <h3 class="case-study-title">{blog_title}</h3>
                        <p class="case-study-description">
                            {text}
                        </p>
"""
    
    if snapshots_html:
        html += f"""
                        <div class="case-study-description">
                            {snapshots_html}
                        </div>
"""
    
    html += f"""
                        <a href="/case-study/{slug}" class="read-more-link">Read More</a>
                    </div>
                </div>
"""
    
    return html


def generate_case_studies_html(case_studies_list, start_index=0):
    """
    Generate HTML for multiple case study cards
    
    Args:
        case_studies_list: List of case study dictionaries with 'slug' and 'preview'
        start_index: Starting index for alternating light/dark theme
        
    Returns:
        str: Complete HTML string with all case study cards
    """
    html_output = ""
    for index, case_study_data in enumerate(case_studies_list, start=start_index):
        html_output += generate_case_study_card(case_study_data, index)
    
    return html_output

def generate_home_case_study_html(case_study):
    """
    Generates the HTML for the case study section on the home page.
    
    Args:
        case_study (dict): A dictionary containing the case study data.
        
    Returns:
        tuple: A tuple containing the HTML for the title, the summary, and the read more button.
    """
    if not case_study:
        return "", "", ""

    slug = case_study.get('slug')
    preview = case_study.get('preview', {})
    if isinstance(preview, str):
        try:
            preview = json.loads(preview)
        except (json.JSONDecodeError, TypeError):
            preview = {}

    image_url = preview.get('imageUrl', '/images/Man-with-bulb.svg')

    title = preview.get('blogTitle', 'Discover Our Latest Success Story')
    
    summary_points = preview.get('projectSnapshots', [])
    
    title_html = f'<h2>{title}</h2>'
    
    summary_html = '<ul>'
    for point in summary_points:
        summary_html += f'<li>{point}</li>'
    summary_html += '</ul>'

    read_more_button_html = f'<button class="read-more-btn" onclick="window.location.href=\'/case-study/{slug}\'">Read more</button>' if slug else '<button class="read-more-btn">Read more</button>'
    
    return title_html, summary_html, read_more_button_html, image_url
async def get_case_study_for_home(conn):
    """
    Fetches the Editor's Choice case study for the home page display.
    Prioritizes the case study marked as Editor's Choice,
    falls back to the most recent published case study if none is set.
    
    Args:
        conn: An asyncpg database connection object.
        
    Returns:
        A dictionary representing the case study, or None if no case study is found.
    """
    query = """
        SELECT slug, preview
        FROM case_studies
        WHERE isdeleted = FALSE
            AND status = 'published'
            AND type = 'CASE STUDY'
        ORDER BY
            CASE WHEN editors_choice = 'Y' THEN 0 ELSE 1 END,
            date DESC
        LIMIT 1
    """
    case_study = await conn.fetchrow(query)
    return case_study