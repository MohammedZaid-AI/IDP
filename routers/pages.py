from __future__ import annotations

from html import escape
from math import ceil
from pathlib import Path
from urllib.parse import urlencode

import json
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
from database.db import SessionLocal
from database.models import User, ProcessingSession, Document


BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

pages_router = APIRouter(tags=["pages"])


@pages_router.get("/dashboard")
def dashboard_page(request: Request):
    session_id_param = request.query_params.get("session_id")
    active_session_id = int(session_id_param) if session_id_param and session_id_param.isdigit() else None
    
    with SessionLocal() as session:
        recent_sessions = list_recent_sessions(session)
        
        active_session = None
        documents = []
        if active_session_id:
            active_session = get_processing_session(session, active_session_id)
            if active_session:
                documents = active_session.documents
            else:
                return RedirectResponse(url="/dashboard", status_code=303)
                
        excel_url = None
        if active_session and active_session.excel_file_path:
            excel_path = Path(active_session.excel_file_path)
            if excel_path.exists() and excel_path.is_file():
                excel_url = f"/api/download-temp?file={excel_path.name}"
                
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "page_title": active_session.name if active_session else "IDP Platform",
                "user_name": _resolve_user_name(request, session),
                "recent_sessions": recent_sessions,
                "active_session": active_session,
                "documents": documents,
                "excel_url": excel_url,
            },
        )


def _resolve_user_name(request: Request, session) -> str:
    current_user = getattr(request.state, "user", None)
    if isinstance(current_user, dict):
        return str(current_user.get("name") or "User")
        
    user_id = request.session.get("user_id")
    if user_id:
        user = session.get(User, user_id)
        if user:
            return user.full_name
            
    return "User"


@pages_router.get("/settings")
def settings_page(request: Request):
    with SessionLocal() as session:
        recent_sessions = list_recent_sessions(session)
                
        return templates.TemplateResponse(
            request,
            "settings.html",
            {
                "page_title": "Settings",
                "user_name": _resolve_user_name(request, session),
                "recent_sessions": recent_sessions,
                "active_session": None,
            },
        )
