from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import events, invitations, users

def _resolve_frontend_dir() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in (
        here.parent / "frontend",  # Docker: /app/frontend
        here.parent.parent.parent.parent / "frontend",  # Repo root (local dev)
    ):
        if candidate.is_dir():
            return candidate
    return here.parent.parent.parent.parent / "frontend"


FRONTEND_DIR = _resolve_frontend_dir()

app = FastAPI(
    title=settings.gateway_title,
    description=(
        "Production-ready Event Scheduling API (calendar-style).\n\n"
        "**Architecture:** Public API Gateway → private microservices "
        "(user-service, event-service, invitation-service).\n\n"
        "Internal services are not exposed on the host network; only this gateway "
        "is reachable from outside Docker."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(events.router)
app.include_router(invitations.router)

if FRONTEND_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {
        "status": "healthy",
        "service": "api-gateway",
        "upstream": {
            "user_service": settings.user_service_url,
            "event_service": settings.event_service_url,
            "invitation_service": settings.invitation_service_url,
        },
    }


@app.get("/", include_in_schema=False)
async def root():
    if FRONTEND_DIR.is_dir():
        return RedirectResponse(url="/ui/")
    return {
        "message": "Event Scheduling API Gateway",
        "docs": "/docs",
        "health": "/health",
    }
