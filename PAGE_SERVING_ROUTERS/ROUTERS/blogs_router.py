from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv
from DATABASE_HANDLER.utils import get_blogs_html # Import the new function

load_dotenv()

router = APIRouter()

@router.get("/blogs", response_class=HTMLResponse)
async def get_blogs(request: Request):
    # Get dynamic blog content
    editors_choice_html, latest_gossips_html, read_more_html, _ = await get_blogs_html()

    # Read the original HTML file
    with open("PAGE_SERVING_ROUTERS/PAGES/blogs_landing.html", "r", encoding="utf-8") as file:
        html_content = file.read()

    # Replace the placeholders with dynamic content
    html_content = html_content.replace(
        '<div id="dynamic-editors-choice-content"></div>',
        editors_choice_html
    )
    html_content = html_content.replace(
        '<div id="dynamic-latest-gossip-content"></div>',
        latest_gossips_html
    )
    html_content = html_content.replace(
        '<div id="dynamic-read-more-content"></div>',
        read_more_html
    )

    return HTMLResponse(content=html_content)