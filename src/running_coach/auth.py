import httpx
from fastapi import HTTPException, Request, status

from running_coach.config import Settings


async def authenticate_athlete(request: Request) -> str:
    """Validate the caller's Supabase Auth access token and return its user id."""
    settings: Settings = request.app.state.settings
    authorization = request.headers.get("Authorization")
    if not settings.supabase_url or not settings.supabase_anon_key or not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required."
        )
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            f"{str(settings.supabase_url).rstrip('/')}/auth/v1/user",
            headers={"Authorization": authorization, "apikey": settings.supabase_anon_key},
        )
    if response.status_code != status.HTTP_200_OK or not response.json().get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required."
        )
    return str(response.json()["id"])
