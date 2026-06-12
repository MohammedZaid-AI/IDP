from __future__ import annotations

from math import ceil
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from starlette.templating import Jinja2Templates

from database.crud import delete_document, get_all_documents, get_document, search_documents
from database.db import SessionLocal
from database.models import User


BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

pages_router = APIRouter(tags=["pages"])


@pages_router.get("/")
def root(request: Request) -> RedirectResponse:
    return RedirectResponse(url="/dashboard")


@pages_router.get("/dashboard")
def dashboard_page(request: Request):
    with SessionLocal() as session:
        recent_documents, _ = get_all_documents(session, page=1, page_size=5)
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "page_title": "Dashboard",
                "user_name": _resolve_user_name(request, session),
                "recent_documents": recent_documents,
            },
        )


def _resolve_user_name(request: Request, session) -> str:
    current_user = getattr(request.state, "user", None)
    if isinstance(current_user, dict):
        return str(current_user.get("name") or current_user.get("username") or "User")
    if current_user is not None:
        return str(getattr(current_user, "name", None) or getattr(current_user, "username", None) or "User")

    cookie_user = request.cookies.get("user_name")
    if cookie_user:
        return cookie_user

    user = session.execute(select(User).where(User.is_active.is_(True)).order_by(User.id)).scalars().first()
    return user.name if user else "User"


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
    pagination_params = dict(params)
    pagination_params.pop("page", None)
    pagination_query = urlencode({key: value for key, value in pagination_params.items() if value})
    with SessionLocal() as session:
        documents, total = search_documents(
            session,
            search=params.get("search") or None,
            document_type=params.get("document_type") or None,
            status=params.get("status") or None,
            date_from=params.get("date_from") or None,
            date_to=params.get("date_to") or None,
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
                "pagination_query": pagination_query,
            },
        )


@pages_router.get("/history/{document_id}")
def document_detail_page(request: Request, document_id: int):
    with SessionLocal() as session:
        document = get_document(session, document_id)
        if document is None:
            return RedirectResponse(url="/history", status_code=303)
        return templates.TemplateResponse(
            request,
            "document_detail.html",
            {
                "page_title": document.filename,
                "document": document,
            },
        )


@pages_router.post("/history/{document_id}/delete")
def delete_history_record(document_id: int):
    with SessionLocal() as session:
        delete_document(session, document_id)
    return RedirectResponse(url="/history", status_code=303)


@pages_router.get("/settings")
def settings_page(request: Request):
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "page_title": "Settings",
        },
    )
