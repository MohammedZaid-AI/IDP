from __future__ import annotations

from html import escape
from math import ceil
from pathlib import Path
from urllib.parse import urlencode

import json
import logging
from datetime import datetime, date, timedelta
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, PlainTextResponse
from sqlalchemy import select
from starlette.templating import Jinja2Templates

from database.crud import (
    delete_document,
    get_all_documents,
    get_document,
    search_documents,
    list_processing_sessions,
    list_recent_sessions,
    get_processing_session,
)
from database.repository import dashboard_metrics
from database.db import SessionLocal
from database.models import User, ProcessingSession, Document


BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

pages_router = APIRouter(tags=["pages"])
LOGGER = logging.getLogger(__name__)


@pages_router.get("/dashboard")
def dashboard_page(request: Request):
    session_id_param = request.query_params.get("session_id")
    active_session_id = int(session_id_param) if session_id_param and session_id_param.isdigit() else None
    
    with SessionLocal() as session:
        recent_sessions = list_recent_sessions(session)
        user = _resolve_user(request, session)
        
        active_session = None
        documents = []
        if active_session_id:
            active_session = get_processing_session(session, active_session_id)
            if active_session:
                documents = active_session.documents
                # Pre-parse canonical fields and validation metrics
                for doc in documents:
                    try:
                        ext = json.loads(doc.extracted_json or "{}")
                    except Exception:
                        ext = {}
                    from services.export_service import map_to_canonical
                    doc.canonical = map_to_canonical(ext)
                    
                    try:
                        val = json.loads(doc.validation_result or "{}")
                    except Exception:
                        val = {}
                    doc.field_confidences = val.get("field_confidences", {})
                    doc.field_states = val.get("field_states", {})
                
                # Compute excel_filename for templates (avoids Jinja basename filter)
                if active_session.excel_file_path:
                    active_session.excel_filename = Path(active_session.excel_file_path).name
                else:
                    active_session.excel_filename = ""
            else:
                return RedirectResponse(url="/dashboard", status_code=303)
                
        excel_url = None
        if active_session and active_session.excel_file_path:
            excel_path = Path(active_session.excel_file_path)
            if excel_path.exists() and excel_path.is_file():
                excel_url = f"/api/download-temp?file={excel_path.name}"
                
        print("[TRACE 6] Value passed to template context (Dashboard). request.session['picture']:", request.session.get("picture"))
        LOGGER.info(f"[TRACE 6] Value passed to template context (Dashboard). request.session['picture']: {request.session.get('picture')}")
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "page_title": active_session.name if active_session else "IDP Platform",
                "user": user,
                "user_name": user.full_name if user else "User",
                "recent_sessions": recent_sessions,
                "active_session": active_session,
                "documents": documents,
                "excel_url": excel_url,
                "active_page": "dashboard",
                "metrics": dashboard_metrics(session),
            },
        )


@pages_router.get("/upload")
def upload_page(request: Request):
    with SessionLocal() as session:
        recent_sessions = list_recent_sessions(session)
        user = _resolve_user(request, session)
        print("[TRACE 6] Value passed to template context (Upload). request.session['picture']:", request.session.get("picture"))
        LOGGER.info(f"[TRACE 6] Value passed to template context (Upload). request.session['picture']: {request.session.get('picture')}")
        return templates.TemplateResponse(
            request,
            "upload.html",
            {
                "page_title": "Upload Documents",
                "user": user,
                "user_name": user.full_name if user else "User",
                "recent_sessions": recent_sessions,
                "active_session": None,
                "active_page": "upload",
            },
        )


def _resolve_user(request: Request, session) -> User | None:
    user_id = request.session.get("user_id")
    if user_id:
        return session.get(User, user_id)
    return None


def _resolve_user_name(request: Request, session) -> str:
    user = _resolve_user(request, session)
    if user:
        return user.full_name
    return "User"


@pages_router.get("/settings")
def settings_page(request: Request):
    with SessionLocal() as session:
        recent_sessions = list_recent_sessions(session)
        user = _resolve_user(request, session)
                
        return templates.TemplateResponse(
            request,
            "settings.html",
            {
                "page_title": "Settings",
                "user": user,
                "user_name": user.full_name if user else "User",
                "recent_sessions": recent_sessions,
                "active_session": None,
                "active_page": "settings",
            },
        )

