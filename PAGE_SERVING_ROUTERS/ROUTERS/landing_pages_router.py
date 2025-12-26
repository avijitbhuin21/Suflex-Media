from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import os
    
load_dotenv(override=True)

router = APIRouter(prefix="/lp", tags=["Landing Pages"])


@router.get("/linkedin-v1")
async def get_linkedin_v1_page():
    data = open("PAGE_SERVING_ROUTERS/PAGES/linkedin_v1.html", "r", encoding="utf-8").read()
    data = data.replace("[[[linkedin_v1_url]]]", os.getenv("LINKEDIN_V1_URL", "https://calendly.com/suflex-media/linkedin-strategy-call"))
    return HTMLResponse(content=data)


@router.get("/book-v1")
async def get_book_v1_page():
    data = open("PAGE_SERVING_ROUTERS/PAGES/book_v1.html", "r", encoding="utf-8").read()
    data = data.replace("[[[book_v1_url]]]", os.getenv("BOOK_V1_URL", "https://calendly.com/sahil-suflexmedia/30min"))
    return HTMLResponse(content=data)
