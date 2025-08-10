"""Primary FastAPI application object.
Run with:  uvicorn backend.app:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from backend.core.logging import add_logging_middleware
from backend.core.settings import settings

# Routers
from backend.api.root import router as root_router
from backend.api.auth import router as auth_router
from backend.api.projects import router as projects_router
from backend.api.files import router as files_router
from backend.api.sandbox_router import router as sandbox_router
from backend.api.ai import router as ai_router


app = FastAPI()

# middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
add_logging_middleware(app)

# register routers (paths kept identical to legacy for compatibility)
for r in (
    root_router,
    auth_router,
    projects_router,
    files_router,
    sandbox_router,
    ai_router,
):
    app.include_router(r)
