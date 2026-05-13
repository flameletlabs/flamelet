"""Server-Sent Events streaming for live logs."""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
import asyncio
from core.web.db import get_run, get_run_logs_since

router = APIRouter()


@router.get("/runs/{run_id}/stream")
async def stream_logs(run_id: str):
    """Stream log lines for a run via SSE."""

    async def generator():
        last_id = 0
        poll_count = 0
        max_empty_polls = 200  # ~60 seconds of polling at 0.3s intervals

        while True:
            # Get new logs
            rows = get_run_logs_since(run_id, last_id)

            for row in rows:
                last_id = row["id"]
                yield {"data": row["line"]}
                poll_count = 0  # Reset empty poll counter when we get data

            # Check if run finished
            run = get_run(run_id)
            if run and run["status"] in ("success", "failed"):
                # Send final status line
                status_line = f"✓ Completed with status: {run['status']}"
                if run["status"] == "failed":
                    status_line = f"✗ {status_line}"
                yield {"data": status_line}
                break

            # Avoid busy-waiting
            await asyncio.sleep(0.3)
            poll_count += 1

            # Stop polling if no updates for too long
            if poll_count > max_empty_polls:
                break

    return EventSourceResponse(generator())
