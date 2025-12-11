import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.exceptions import HTTPException
import uvicorn
from contextlib import asynccontextmanager

from config import config
from DATABASE_HANDLER import initialize_database
from DATABASE_HANDLER.connection_pool import db_pool
from PAGE_SERVING_ROUTERS.ROUTERS.static_pages_router import router as static_pages_router
from PAGE_SERVING_ROUTERS.ROUTERS.blogs_router import router as blogs_router
from PAGE_SERVING_ROUTERS.ROUTERS.error_router import router as error_router
from PAGE_SERVING_ROUTERS.ROUTERS.login_router import router as login_router
from PAGE_SERVING_ROUTERS.ROUTERS.admin_homepage_router import router as admin_homepage_router
from PAGE_SERVING_ROUTERS.ROUTERS.admin_users_router import router as admin_users_router
from PAGE_SERVING_ROUTERS.ROUTERS.admin_blogs_router import router as admin_blogs_router
from PAGE_SERVING_ROUTERS.ROUTERS.admin_case_studies_router import router as admin_case_studies_router
from PAGE_SERVING_ROUTERS.ROUTERS.Blog_Creator_router import router as blog_creator_router
from PAGE_SERVING_ROUTERS.ROUTERS.case_study_router import router as case_study_router
from API_ROUTERS.login_api_router import router as login_api_router
from API_ROUTERS.admin_users_api_router import router as admin_users_api_router
from API_ROUTERS.serve_images_api_router import router as serve_images_api_router
from API_ROUTERS.blogs_api_router import router as blogs_api_router
from API_ROUTERS.case_studies_api_router import router as case_studies_api_router
from API_ROUTERS.contact_us_api_router import router as contact_us_api_router
from PAGE_SERVING_ROUTERS.ROUTERS.seo_router import router as seo_router


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events (startup and shutdown).
    Initializes database and connection pool on startup, closes pool on shutdown.
    """
    logger.info("Initializing database...")
    try:
        await initialize_database()
        logger.info("Database initialized successfully!")
    except UnicodeEncodeError:
        logger.warning("Database initialized successfully! (Unicode characters may not display correctly in the console)")
    
    logger.info("Initializing database connection pool...")
    await db_pool.initialize(min_size=config.DB_POOL_MIN_SIZE, max_size=config.DB_POOL_MAX_SIZE)
    logger.info("Database connection pool initialized!")
    
    yield
    
    logger.info("Closing database connection pool...")
    await db_pool.close()
    logger.info("Database connection pool closed!")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache headers middleware for static assets
@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    # Add long cache headers for static assets
    if any(path.startswith(p) for p in ['/css/', '/js/', '/images/', '/icons/', '/fonts/']):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


app.mount("/css", StaticFiles(directory="PAGE_SERVING_ROUTERS/CSS"), name="css")
app.mount("/icons", StaticFiles(directory="PAGE_SERVING_ROUTERS/ICONS"), name="icons")
app.mount("/images", StaticFiles(directory="PAGE_SERVING_ROUTERS/IMAGES"), name="images")
app.mount("/js", StaticFiles(directory="PAGE_SERVING_ROUTERS/JS"), name="js")
app.mount("/pages", StaticFiles(directory="PAGE_SERVING_ROUTERS/PAGES"), name="pages")
app.mount("/fonts", StaticFiles(directory="PAGE_SERVING_ROUTERS/FONTS"), name="fonts")

app.include_router(static_pages_router)
app.include_router(blogs_router)
app.include_router(error_router)
app.include_router(login_router)
app.include_router(admin_homepage_router)
app.include_router(admin_users_router)
app.include_router(admin_blogs_router)
app.include_router(admin_case_studies_router)
app.include_router(blog_creator_router)
app.include_router(case_study_router)
app.include_router(login_api_router)
app.include_router(admin_users_api_router)
app.include_router(serve_images_api_router)
app.include_router(blogs_api_router)
app.include_router(contact_us_api_router)
app.include_router(case_studies_api_router)
app.include_router(seo_router)

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: HTTPException):
    return FileResponse("PAGE_SERVING_ROUTERS/PAGES/404.html", status_code=404)

if __name__ == "__main__":
    uvicorn.run("app:app", host=config.API_HOST, port=config.API_PORT, reload=True)
