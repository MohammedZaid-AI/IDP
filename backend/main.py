from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from database.db import init_db
from database.repository import seed_demo_data
from routers.api import api_router
from routers.pages import pages_router
from routers.auth import auth_router

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        protected_prefixes = ("/dashboard", "/settings", "/upload", "/history", "/api/upload", "/sessions")
        path = request.url.path

        is_protected = path.startswith(protected_prefixes)
        
        # Access session directly from ASGI scope populated by SessionMiddleware
        session = scope.get("session", {})
        user_id = session.get("user_id")
        user_name = session.get("name")

        if is_protected and not user_id:
            if path.startswith("/api/"):
                response = JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized. Please log in."}
                )
            else:
                response = RedirectResponse(url="/", status_code=303)
            await response(scope, receive, send)
            return

        # Pass user info to request state
        if user_id:
            scope["state"] = scope.get("state", {})
            scope["state"]["user"] = {"name": user_name}
        else:
            if "state" in scope and "user" in scope["state"]:
                scope["state"]["user"] = None

        await self.app(scope, receive, send)


def create_app() -> FastAPI:
    app = FastAPI(title="IDP Intelligence Platform")
    
    # Register custom AuthMiddleware first (so it runs after SessionMiddleware in ASGI execution)
    app.add_middleware(AuthMiddleware)
    
    # Configure session middleware second (added last, so it runs first and populates the session)
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise ValueError("SECRET_KEY must be defined in the .env file.")

    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        session_cookie="idp_session",
        max_age=14 * 24 * 3600,  # 14 days
        same_site="lax",
        https_only=False,
    )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.state.templates = templates
    
    init_db()
    session = seed_demo_data()
    session.commit()
    session.close()

    # Register routers
    app.include_router(auth_router)
    app.include_router(pages_router)
    app.include_router(api_router)

    # Startup verification
    from services.qwen_local import QwenLocalExtractor
    extractor = QwenLocalExtractor()
    extractor.verify_model()
    
    return app


app = create_app()

