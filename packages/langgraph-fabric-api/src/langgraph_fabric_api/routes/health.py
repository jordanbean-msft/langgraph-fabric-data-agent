"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        A dict with status "ok".
    """
    return {"status": "ok"}
