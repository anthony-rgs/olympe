import asyncio
import os
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import _FAIL_DELAY, create_token, get_user, require_auth, verify_password

_COOKIES_FILE = os.getenv("YTDLP_COOKIES_FILE", "/storage/cookies.txt")
_COOKIE_MAX_AGE = int(os.getenv("COOKIE_MAX_AGE_SECONDS", "600"))  # 10 min

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


@router.get("/cookies/status")
async def cookies_status(_: dict = Depends(require_auth)):
  """Retourne l'âge des cookies et si un rafraîchissement est nécessaire."""
  if not os.path.isfile(_COOKIES_FILE):
    return {"exists": False, "age_seconds": None, "needs_refresh": True}

  age = int(time.time() - os.path.getmtime(_COOKIES_FILE))
  return {
    "exists": True,
    "age_seconds": age,
    "needs_refresh": age > _COOKIE_MAX_AGE,
  }


class CookiesPayload(BaseModel):
  cookies: str  # contenu brut du fichier Netscape


@router.post("/cookies", status_code=204)
async def upload_cookies(body: CookiesPayload, _: dict = Depends(require_auth)):
  """Reçoit et sauvegarde les cookies YouTube envoyés par l'extension Chrome."""
  os.makedirs(os.path.dirname(_COOKIES_FILE), exist_ok=True)
  with open(_COOKIES_FILE, "w") as f:
    f.write(body.cookies)
  print(f"[cookies] Fichier mis à jour ({len(body.cookies)} bytes)")