import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import admin, mcp, workers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Ninetrix MCP Gateway",
    version="0.1.0",
    description="Unified MCP proxy — agents call one endpoint, workers connect from anywhere.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mcp.router)
app.include_router(workers.router)
app.include_router(admin.router)

