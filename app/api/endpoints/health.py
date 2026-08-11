from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["health"])
def health_check():
    """
    Check if the API is up and running.
    """
    return {"status": "ok"}
