from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database.db import init_db
from database.repository import seed_demo_data
from routers.api import api_router
from routers.pages import pages_router


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def create_app() -> FastAPI:
    app = FastAPI(title="IDP Intelligence Platform")
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.state.templates = templates
    init_db()
    session = seed_demo_data()
    session.commit()
    session.close()

    app.include_router(pages_router)
    app.include_router(api_router)
    return app


app = create_app()
