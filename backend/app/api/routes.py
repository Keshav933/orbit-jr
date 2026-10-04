from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "orbit-jr-api"}

@router.get("/version")
def version() -> dict[str, str]:
    return {"project": "ORBIT-JR", "version": "0.1.0"}
