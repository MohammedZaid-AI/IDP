from __future__ import annotations

import json
from math import ceil
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from database.db import SessionLocal
from database.repository import analytics_payload, dashboard_metrics, get_document_detail, list_documents, list_pending_reviews


BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

pages_router = APIRouter(tags=["pages"])


@pages_router.get("/")
def root(request: Request) -> RedirectResponse:
    return RedirectResponse(url="/dashboard")


@pages_router.get("/dashboard")
def dashboard_page(request: Request):
    with SessionLocal() as session:
        metrics = dashboard_metrics(session)
        analytics = analytics_payload(session)
        documents, _ = list_documents(session, page=1, page_size=8)
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "page_title": "Dashboard",
                "metrics": metrics,
                "analytics": analytics,
                "documents": documents,
            },
        )


@pages_router.get("/upload")
def upload_page(request: Request):
    return templates.TemplateResponse(
        request,
        "upload.html",
        {
            "page_title": "Upload Documents",
        },
    )


@pages_router.get("/history")
def history_page(request: Request):
    params = request.query_params
    page = int(params.get("page", 1))
    page_size = int(params.get("page_size", 10))
    with SessionLocal() as session:
        documents, total = list_documents(
            session,
            search=params.get("search"),
            document_type=params.get("document_type"),
            status=params.get("status"),
            sort=params.get("sort", "created_at"),
            page=page,
            page_size=page_size,
        )
        return templates.TemplateResponse(
            request,
            "history.html",
            {
                "page_title": "Document History",
                "documents": documents,
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": max(1, ceil(total / page_size)) if page_size else 1,
            },
        )


@pages_router.get("/review")
def review_page(request: Request):
    selected_id = request.query_params.get("id")
    with SessionLocal() as session:
        pending = list_pending_reviews(session)
        selected_document = None
        if selected_id:
            selected_document = get_document_detail(session, int(selected_id))
        if selected_document is None and pending:
            selected_document = get_document_detail(session, pending[0].id)
        return templates.TemplateResponse(
            request,
            "review.html",
            {
                "page_title": "Review Queue",
                "pending_documents": pending,
                "selected_document": selected_document,
                "selected_json": json.loads(selected_document.json_output or "{}") if selected_document else {},
            },
        )


@pages_router.get("/analytics")
def analytics_page(request: Request):
    with SessionLocal() as session:
        metrics = dashboard_metrics(session)
        analytics = analytics_payload(session)
        return templates.TemplateResponse(
            request,
            "analytics.html",
            {
                "page_title": "Analytics",
                "metrics": metrics,
                "analytics": analytics,
            },
        )


@pages_router.get("/settings")
def settings_page(request: Request):
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "page_title": "Settings",
        },
    )
