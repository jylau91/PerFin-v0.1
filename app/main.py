from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.auth import (
    AuthMiddleware,
    check_passphrase,
    clear_session,
    issue_session,
    rate_limit_login,
)
from app.config import get_settings
from app.deps import render
from app.routes import ai as ai_routes
from app.routes import dashboard as dashboard_routes
from app.routes import investments as investment_routes
from app.routes import reconcile as reconcile_routes
from app.routes import statements as statement_routes
from app.routes import transactions as transaction_routes
from app.scheduler import start_scheduler, stop_scheduler

log = logging.getLogger("perfin")
STATIC_DIR = Path(__file__).parent / "web" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.engine import get_conn
    from migrations.runner import apply_all

    applied = apply_all(get_conn())
    if applied:
        log.info("Applied migrations: %s", applied)
    scheduler = start_scheduler()
    try:
        yield
    finally:
        stop_scheduler(scheduler)


def create_app() -> FastAPI:
    app = FastAPI(title="PerFin", lifespan=lifespan)
    app.add_middleware(AuthMiddleware)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(dashboard_routes.router)
    app.include_router(statement_routes.router)
    app.include_router(transaction_routes.router)
    app.include_router(investment_routes.router)
    app.include_router(reconcile_routes.router)
    app.include_router(ai_routes.router)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    @app.get("/login")
    def login_form(request: Request):
        return render(request, "login.html", error=None)

    @app.post("/login")
    def login_submit(request: Request, passphrase: str = Form(...)):
        if not rate_limit_login():
            return render(request, "login.html", error="Too many attempts. Wait a minute.")
        if not check_passphrase(passphrase):
            return render(request, "login.html", error="Wrong passphrase.")
        response = RedirectResponse(url="/", status_code=303)
        issue_session(response)
        return response

    @app.post("/logout")
    def logout():
        response = RedirectResponse(url="/login", status_code=303)
        clear_session(response)
        return response

    return app


app = create_app()


def _bind_host() -> str:
    settings = get_settings()
    if not settings.TAILSCALE_BIND:
        return "127.0.0.1"
    try:
        import subprocess

        out = subprocess.check_output(["tailscale", "ip", "-4"], text=True, timeout=2)
        return out.strip().splitlines()[0] or "127.0.0.1"
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=_bind_host(), port=settings.PERFIN_PORT, reload=False)
