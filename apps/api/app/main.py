"""FastAPI application entry point."""

from fastapi import FastAPI

from app.core.api import configure_api
from app.core.config import settings
from app.modules.alerts.router import router as alerts_router
from app.modules.assistant.router import router as assistant_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.insights.router import router as insights_router
from app.modules.laboratory.router import router as laboratory_router
from app.modules.medications.router import router as medications_router
from app.modules.monitoring.router import router as monitoring_router
from app.modules.patients.router import router as patients_router
from app.modules.rag.router import router as rag_router
from app.modules.reports.router import router as reports_router
from app.modules.safety.router import router as safety_router
from app.modules.search.router import router as search_router
from app.modules.symptoms.router import router as symptoms_router
from app.modules.timeline.router import router as timeline_router

app = FastAPI(title=settings.APP_NAME, version="1.0.0")
configure_api(app)

routers = [
    auth_router,
    patients_router,
    reports_router,
    laboratory_router,
    symptoms_router,
    medications_router,
    timeline_router,
    monitoring_router,
    alerts_router,
    insights_router,
    assistant_router,
    search_router,
    rag_router,
    safety_router,
    audit_router,
]

for router in routers:
    app.include_router(router, prefix="/v1")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Return the application health status."""
    return {"status": "ok", "env": settings.ENV}
