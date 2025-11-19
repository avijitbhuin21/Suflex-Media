from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from typing import Dict, Any
from DATABASE_HANDLER.auth import require_admin_with_redirect

router = APIRouter()

@router.get("/admin")
async def get_admin_homepage(request: Request, current_user: Dict[str, Any] = Depends(require_admin_with_redirect)):
    return FileResponse("PAGE_SERVING_ROUTERS/PAGES/admin_homepage.html")