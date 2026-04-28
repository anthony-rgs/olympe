import asyncio
from datetime import datetime, timedelta, timezone

import psycopg
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import JWT_EXPIRE_HOURS, JWT_SECRET
from .db import get_db

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)

_FAIL_DELAY = 3


# ── Utilisateurs ──────────────────────────────────────────────────────────────

async def get_user_by_username(conn: psycopg.AsyncConnection, username: str) -> dict | None:
  async with conn.cursor() as cur:
    await cur.execute("SELECT * FROM orphee_users WHERE username = %s", (username,))
    return await cur.fetchone()


async def get_user_by_id(conn: psycopg.AsyncConnection, user_id: str) -> dict | None:
  async with conn.cursor() as cur:
    await cur.execute("SELECT * FROM orphee_users WHERE id = %s", (user_id,))
    return await cur.fetchone()


def verify_password(plain: str, hashed: str) -> bool:
  return _pwd_context.verify(plain, hashed)

def hash_password(plain: str) -> str:
  return _pwd_context.hash(plain)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_token(user_id: str, username: str, token_version: int) -> str:
  expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
  return jwt.encode(
    {"sub": str(user_id), "username": username, "tv": token_version, "exp": expire},
    JWT_SECRET,
    algorithm="HS256",
  )


# ── Dépendance FastAPI ────────────────────────────────────────────────────────

async def require_auth(
  credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
  conn: psycopg.AsyncConnection = Depends(get_db),
) -> dict:
  if not credentials:
    await asyncio.sleep(_FAIL_DELAY)
    raise HTTPException(status_code=401, detail="Token manquant. Connecte-toi via POST /auth/login.")

  try:
    payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    user_id: str = payload.get("sub")
    token_version: int = payload.get("tv")
    if not user_id or token_version is None:
      raise JWTError()
  except JWTError:
    await asyncio.sleep(_FAIL_DELAY)
    raise HTTPException(status_code=401, detail="Token invalide ou expiré.")

  user = await get_user_by_id(conn, user_id)
  if not user:
    await asyncio.sleep(_FAIL_DELAY)
    raise HTTPException(status_code=401, detail="Utilisateur introuvable.")

  if user["token_version"] != token_version:
    await asyncio.sleep(_FAIL_DELAY)
    raise HTTPException(status_code=401, detail="Token révoqué.")

  return dict(user)
