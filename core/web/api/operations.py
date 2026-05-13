"""Operations catalog endpoint."""

from fastapi import APIRouter
from core.tasks import TASK_REGISTRY

router = APIRouter()


@router.get("/operations")
async def list_operations():
    """List all operations with OS family support."""
    operations = []

    for task_name in sorted(TASK_REGISTRY.keys()):
        entries = TASK_REGISTRY[task_name]
        for entry in entries:
            os_families = entry.os_families or None  # None means all OSes
            operations.append(
                {
                    "task": task_name,
                    "config_attr": entry.config_attr,
                    "op_type": entry.op_type,
                    "os_families": os_families,
                }
            )

    return operations
