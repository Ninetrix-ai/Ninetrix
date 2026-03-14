from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from mcp_gateway.core.registry import registry

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "connected_workers": len(registry._workers)}


@router.get("/admin/workers")
async def list_workers(workspace_id: Optional[str] = Query(None)):
    workers = registry.list_workers(workspace_id)
    return {"workers": [w.model_dump() for w in workers], "count": len(workers)}


@router.get("/admin/tools")
async def list_tools(workspace_id: str = Query("default")):
    tools = registry.get_tools(workspace_id)
    return {"tools": [t.model_dump() for t in tools], "count": len(tools)}
