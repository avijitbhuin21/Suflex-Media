from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(prefix="/lp", tags=["Landing Pages"])


@router.get("/linkedin-v1")
async def get_linkedin_v1_page():
    return FileResponse("PAGE_SERVING_ROUTERS/PAGES/linkedin_v1.html")


@router.get("/book-v1")
async def get_book_v1_page():
    return FileResponse("PAGE_SERVING_ROUTERS/PAGES/book_v1.html")
