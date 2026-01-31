"""
FastAPI application entry point.
Auto-Blog SEO Monster - Multi-tenant AI content generation system.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.database import init_db, close_db

# Import routers
from app.api import auth, tenants, agents, sources, publishers, posts, tasks, public, schedules

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-tenant AI-powered blog content generation with SEO optimization",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Event handlers
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")

    # Initialize database (create tables if needed)
    if settings.DEBUG:
        logger.info("Initializing database...")
        await init_db()

    # Fix admin user tenant association if needed
    try:
        from app.database import AsyncSessionLocal
        from app.models.tenant import Tenant
        from app.models.user import User
        from sqlalchemy import select

        logger.info("Checking admin user tenant association...")

        async with AsyncSessionLocal() as db:
            # First get the admin user to see their current tenant_id
            result = await db.execute(
                select(User).where(User.email == "admin@legitio.pl")
            )
            admin = result.scalar_one_or_none()

            if admin:
                logger.info(f"Found admin user: {admin.email}, tenant_id: {admin.tenant_id}")

                if admin.tenant_id is None:
                    # Get Legitio tenant
                    result = await db.execute(
                        select(Tenant).where(Tenant.slug == "legitio")
                    )
                    tenant = result.scalar_one_or_none()

                    if tenant:
                        admin.tenant_id = tenant.id
                        admin.role = "admin"
                        await db.commit()
                        logger.info(f"Fixed admin user: associated with tenant {tenant.name}")
                    else:
                        logger.warning("Legitio tenant not found!")
                else:
                    logger.info(f"Admin already has tenant: {admin.tenant_id}")
            else:
                logger.info("No admin@legitio.pl user found")
    except Exception as e:
        logger.warning(f"Could not fix admin user: {e}")

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Application shutdown complete")


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(public.router, prefix=settings.API_PREFIX)  # Public endpoints first (no auth)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(tenants.router, prefix=settings.API_PREFIX)
app.include_router(agents.router, prefix=settings.API_PREFIX)
app.include_router(sources.router, prefix=settings.API_PREFIX)
app.include_router(sources.tenant_router, prefix=settings.API_PREFIX)  # Tenant-level /sources
app.include_router(publishers.router, prefix=settings.API_PREFIX)
app.include_router(publishers.tenant_router, prefix=settings.API_PREFIX)  # Tenant-level /publishers
app.include_router(posts.router, prefix=settings.API_PREFIX)
app.include_router(tasks.router, prefix=settings.API_PREFIX)
app.include_router(schedules.router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

