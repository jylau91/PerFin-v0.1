from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.db.engine import get_conn

TEMPLATES_DIR = Path(__file__).parent / "web" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def db() -> sqlite3.Connection:
    return get_conn()


def render(request: Request, template: str, **ctx):
    return templates.TemplateResponse(request, template, ctx)
