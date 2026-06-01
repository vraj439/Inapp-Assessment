from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import events, invitations, users

app = FastAPI(
    title=settings.gateway_title,
    description=(
        "Production-ready Event Scheduling API (calendar-style).\n\n"
        "**Architecture:** Public API Gateway → private microservices "
        "(user-service, event-service, invitation-service).\n\n"
        "Internal services are not exposed on the host network; only this gateway "
        "is reachable from outside Docker."
    ),
    version=settings.gateway_version,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    openapi_url=settings.openapi_url,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(events.router)
app.include_router(invitations.router)

_frontend_dir = settings.resolved_frontend_dir()
if _frontend_dir is not None:
    app.mount("/ui", StaticFiles(directory=str(_frontend_dir), html=True), name="ui")


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {
        "status": "healthy",
        "service": settings.service_name,
        "upstream": {
            "user_service": settings.user_service_url,
            "event_service": settings.event_service_url,
            "invitation_service": settings.invitation_service_url,
        },
    }


@app.get("/", include_in_schema=False)
async def root():
    if _frontend_dir is not None:
        return RedirectResponse(url="/ui/")
    return {
        "message": settings.gateway_title,
        "docs": settings.docs_url,
        "health": "/health",
    }
