import asyncpg
import os
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv("POSTGRES_CONNECTION_URL")

async def get_blog_data():
    """
    Fetch blog data from the database for the three sections:
    1. Editor's Choice (carousel)
    2. Latest Gossip (3 most recent blogs)
    3. Read More (all other blogs with pagination)
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Fetch all published blogs of type 'BLOG'
        all_blogs_query = """
            SELECT id, blog, date, created_at, editors_choice, slug, type
            FROM blogs
            WHERE isdeleted = FALSE
            ORDER BY created_at DESC
        """
        all_blogs = await conn.fetch(all_blogs_query)

        await conn.close()

        processed_blogs = []
        for blog in all_blogs:
            blog_content = blog['blog']
            if isinstance(blog_content, str):
                blog_content = json.loads(blog_content)

            title = blog_content.get('blogTitle', 'Untitled Blog')
            summary = blog_content.get('blogSummary', '')
            if not summary:
                content = blog_content.get('blogContent', {})
                if isinstance(content, dict) and 'content' in content:
                    content_items = content['content']
                    for item in content_items:
                        if item.get('type') == 'paragraph' and item.get('data', {}).get('content'):
                            summary = item['data']['content']
                            break
                elif isinstance(content, str):
                    summary = content
            
            summary = summary[:150] + '...' if len(summary) > 150 else summary
            
            processed_blogs.append({
                'id': blog['id'],
                'title': title,
                'summary': summary,
                'created_at': blog['created_at'].strftime('%B %d, %Y') if blog['created_at'] else '',
                'slug': blog['slug'],
                'category': blog_content.get('blogCategory', 'General'),
                'editors_choice': blog['editors_choice'] == 'Y',
                'cover_image': extract_blog_image(blog_content)
            })

        # Separate blogs into the three sections
        editors_choice_data = [b for b in processed_blogs if b['editors_choice']]
        
        # All other blogs that are not editor's choice
        other_blogs = [b for b in processed_blogs if not b['editors_choice']]
        
        latest_gossip_data = other_blogs[:3]
        read_more_data = other_blogs[3:]

        return editors_choice_data, latest_gossip_data, read_more_data

    except Exception as e:
        print(f"Error fetching blogs: {e}")
        return [], [], []


def extract_blog_image(blog_content):
    """
    Extract the cover image URL from the blog content.
    The image is expected to be the first block of type 'image'.
    """
    if 'mainImageUrl' in blog_content and blog_content['mainImageUrl']:
        return blog_content['mainImageUrl']
    
    if 'blog_cover_image' in blog_content and blog_content['blog_cover_image']:
        return blog_content['blog_cover_image'].get('url')
        
    if 'blogContent' in blog_content and 'blocks' in blog_content['blogContent']:
        for block in blog_content['blogContent']['blocks']:
            if block['type'] == 'image':
                return block['data']['file']['url']
    return None


def generate_editors_choice_card_html(blog):
    """
    Generate HTML for a single Editor's Choice blog card.
    """
    return f'''
        <div class="blog-card editors-choice-card" onclick="window.location.href='/blog/{blog['slug']}'">
            <div class="editors-choice-card-image-container">
                <img src="{blog['cover_image']}" alt="{blog['title']}" class="editors-choice-card-image">
            </div>
            <div class="editors-choice-card-content">
                <h3 class="blog-title">{blog['title']}</h3>
                <p class="blog-summary">{blog['summary']}</p>
                <div class="blog-footer">
                    <p class="blog-date">Suflex Media • {blog['created_at']}</p>
                </div>
            </div>
        </div>
    '''


def generate_blog_card_html(blog, color_index):
    """
    Generate HTML for a single blog card based on the existing structure
    """
    return f'''
        <div class="blog-card" data-category="{blog['category']}" onclick="window.location.href='/blog/{blog['slug']}'">
            <div class="blog-card-header">
                <div class="blog-dot" style="background-color: {get_blog_color(color_index)}"></div>
                <span class="blog-read-time">5 mins read</span>
            </div>
            <h3 class="blog-title">{blog['title']}</h3>
            <p class="blog-date">{blog['created_at']} • {blog['category']}</p>
            <p class="blog-description">{blog['summary']}</p>
            <div class="blog-footer">
                <a href="/blog/{blog['slug']}" class="blog-arrow-link">
                    <div class="blog-arrow">
                        <svg viewBox="0 24 24" fill="none">
                            <path d="M5 12h14m-7-7l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                </a>
            </div>
        </div>
    '''

def get_blog_color(index):
    """
    Get color based on index to match existing color pattern
    """
    colors = ['#22c55e', '#ef4444', '#06b6d4', '#22c55e', '#eab308', '#3b82f6', '#22c55e', '#ec4899', '#06b6d4', '#eab308', '#a855f7', '#22c55e']
    return colors[index % len(colors)]

async def get_blogs_html():
    """
    Generate the HTML content for the blogs_landing.html page with dynamic content
    for all three sections.
    """
    editors_choice_data, latest_gossip_data, read_more_data = await get_blog_data()

    # Generate HTML for Editor's Choice carousel
    editors_choice_html = ""
    for blog in editors_choice_data:
        editors_choice_html += generate_editors_choice_card_html(blog)

    # Generate HTML for Latest Gossip
    latest_gossips_html = ""
    for i, blog in enumerate(latest_gossip_data):
        latest_gossips_html += generate_blog_card_html(blog, i)

    # Generate HTML for Read More
    read_more_html = ""
    for i, blog in enumerate(read_more_data):
        # Start color index from 3 to avoid repeating colors from latest gossips
        read_more_html += generate_blog_card_html(blog, i + 3)

    return editors_choice_html, latest_gossips_html, read_more_html, editors_choice_data[:3]


async def get_home_insights_html(editors_choice_data):
    """
    Generate the HTML content for the home page with top 3 editor's choice blogs
    """
    # Generate HTML for top 3 editor's choice blogs in home page style
    home_insights_html = ""
    for i, blog in enumerate(editors_choice_data):
        home_insights_html += generate_home_insight_card_html(blog, i)
    return home_insights_html


def generate_home_insight_card_html(blog, index):
    """
    Generate HTML for a single insight card on the home page based on the existing structure
    """
    # Map index to color markers: 0=green, 1=pink, 2=orange
    colors = ['green', 'pink', 'orange']
    color_class = colors[index % len(colors)] if index < len(colors) else 'green'
    
    return f'''
                    <div class="insight-card">
                        <div class="card-top">
                            <span class="color-marker {color_class}"></span>
                            <span class="read-time">5 mins read</span>
                        </div>
                        <h3>{blog['title']}</h3>
                        <p>{blog['summary']}</p>
                        <div class="card-content-bottom">
                            <a href="/blog/{blog['slug']}">
                                <img src="/icons/black_arrow.svg" alt="Read more" class="card-arrow-icon">
                            </a>
                        </div>
                    </div>'''

if __name__ == "__main__":
    import asyncio
    
    async def main():
        editors_choice_html, latest_gossips_html, read_more_html, top_editors_choice_data = await get_blogs_html()
        home_insights_html = await get_home_insights_html(top_editors_choice_data)
        
        print("Generated Editor's Choice HTML:\n", editors_choice_html)
        print("Generated Latest Gossips HTML:\n", latest_gossips_html)
        print("Generated Read More HTML:\n", read_more_html)
        print("Generated home insights HTML:\n", home_insights_html)

    asyncio.run(main())