"""Run management endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from core.web.db import get_run, get_run_logs, get_runs
from core.web.executor import queue_run

router = APIRouter()


class RunRequest(BaseModel):
    """Request to queue a new run."""

    tenant: str
    task: str
    hosts: list[str] = None
    dry_run: bool = True
    diff: bool = False


@router.post("/runs")
async def create_run(req: RunRequest):
    """Queue a new deployment run."""
    run_id = queue_run(
        req.tenant, req.task, target_hosts=req.hosts, dry_run=req.dry_run, diff=req.diff
    )
    return {"run_id": run_id}


@router.get("/runs")
async def list_runs(limit: int = 50):
    """List recent runs."""
    runs = get_runs(limit=limit)
    return runs


@router.get("/runs/{run_id}")
async def get_run_detail(run_id: str):
    """Get run details with logs."""
    run = get_run(run_id)
    if not run:
        return {"error": f"Run '{run_id}' not found"}

    logs = get_run_logs(run_id)
    return {**dict(run), "logs": logs}
