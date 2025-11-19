from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from typing import Dict, Any
from DATABASE_HANDLER.auth import require_admin_with_redirect

router = APIRouter()

@router.get("/admin/users")
async def get_admin_users_page(request: Request, current_user: Dict[str, Any] = Depends(require_admin_with_redirect)):
    """
    Serve the admin users management page
    """
    return FileResponse("PAGE_SERVING_ROUTERS/PAGES/admin_users.html")