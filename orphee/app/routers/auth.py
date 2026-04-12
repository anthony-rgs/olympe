import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import _FAIL_DELAY, create_token, get_user, require_auth, verify_password

router = APIRouter()


class LoginRequest(BaseModel):
  username: str
  password: str


@router.post("/login")
async def login(body: LoginRequest):
  """Authentification — retourne un JWT si les identifiants sont valides.

  En cas d'échec, un délai de 5 secondes est appliqué (anti brute-force).
  """
  user = get_user(body.username)

  if not user or not verify_password(body.password, user["password_hash"]):
    await asyncio.sleep(_FAIL_DELAY)
    raise HTTPException(
      status_code=401,
      detail="Nom d'utilisateur ou mot de passe incorrect.",
    )

  token = create_token(body.username)
  return {
    "access_token": token,
    "token_type": "bearer",
    "username": body.username,
  }


@router.get("/me")
async def me(user: dict = Depends(require_auth)):
  """Vérifie que le token est valide et retourne l'utilisateur courant."""
  return {"username": user["username"]}