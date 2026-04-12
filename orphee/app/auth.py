import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import JWT_EXPIRE_HOURS, JWT_SECRET, USERS_FILE

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)

# Délai anti brute-force en secondes
_FAIL_DELAY = 3


# ── Gestion des utilisateurs ──────────────────────────────────────────────────

def _load_users() -> list[dict]:
  """Charge la liste des utilisateurs depuis users.json."""
  if not os.path.exists(USERS_FILE):
    return []
  with open(USERS_FILE) as f:
    return json.load(f)


def get_user(username: str) -> dict | None:
  """Retourne un utilisateur par son username, ou None s'il n'existe pas."""
  return next((u for u in _load_users() if u["username"] == username), None)


def verify_password(plain: str, hashed: str) -> bool:
  return _pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_token(username: str) -> str:
  """Crée un JWT signé valable JWT_EXPIRE_HOURS heures."""
  expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
  return jwt.encode(
    {"sub": username, "exp": expire},
    JWT_SECRET,
    algorithm="HS256",
  )


# ── Dépendance FastAPI ────────────────────────────────────────────────────────

async def require_auth(
  credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
  """Dépendance injectée sur toutes les routes protégées.

  Vérifie le JWT dans le header Authorization: Bearer <token>.
  Retourne le dict utilisateur si valide, lève 401 sinon.
  """
  if not credentials:
    await asyncio.sleep(_FAIL_DELAY)
    raise HTTPException(status_code=401, detail="Token manquant. Connecte-toi via POST /auth/login.")

  try:
    payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    username: str = payload.get("sub")
    if not username:
      raise JWTError()
  except JWTError:
    await asyncio.sleep(_FAIL_DELAY)
    raise HTTPException(status_code=401, detail="Token invalide ou expiré.")

  user = get_user(username)
  if not user:
    await asyncio.sleep(_FAIL_DELAY)
    raise HTTPException(status_code=401, detail="Utilisateur introuvable.")

  return user
