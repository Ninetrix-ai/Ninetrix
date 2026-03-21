"""Agentfile API server — serves the local web dashboard."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI


class _NoHealthFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "GET /health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_NoHealthFilter())
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from ninetrix_api import db
from ninetrix_api.auth import init_machine_secret
from ninetrix_api.routers import agents, approvals, channels, integrations, runners, threads, tokens


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await db.create_runner_events_table()
    await db.create_integration_tables()
    init_machine_secret()
    # Start channel polling (Telegram getUpdates) — no tunnel needed for local dev
    from ninetrix_channels.polling import ChannelPoller
    poller = ChannelPoller(db.pool(), channels.handle_polled_message)
    await poller.start()
    yield
    await poller.stop()
    await db.close()


app = FastAPI(
    title="Agentfile API",
    version="0.1.0",
    description="Local API server for the Agentfile web dashboard",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(threads.router, prefix="/threads", tags=["threads"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
app.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
app.include_router(tokens.router, prefix="/tokens", tags=["tokens"])
app.include_router(runners.router, prefix="/v1/runners", tags=["runners"])
app.include_router(runners.router, prefix="/internal/v1/runners", tags=["runners"])
app.include_router(channels.router, prefix="/v1/channels", tags=["channels"])
app.include_router(channels.webhook_router, prefix="/v1/channels", tags=["channels-webhook"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard/")


# Serve the pre-built Next.js dashboard (static export) at /dashboard
_dashboard_dir = Path(__file__).parent / "static" / "dashboard"
if _dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=str(_dashboard_dir), html=True), name="dashboard")
