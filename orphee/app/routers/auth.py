import asyncio

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import _FAIL_DELAY, create_token, get_user_by_username, require_auth, verify_password
from ..db import get_db
from ..job_store import get_active_jobs_for_user

router = APIRouter()


class LoginRequest(BaseModel):
  username: str
  password: str


@router.post("/login")
async def login(body: LoginRequest, conn: psycopg.AsyncConnection = Depends(get_db)):
  user = await get_user_by_username(conn, body.username)

  if not user or not verify_password(body.password, user["password_hash"]):
    await asyncio.sleep(_FAIL_DELAY)
    raise HTTPException(status_code=401, detail="Nom d'utilisateur ou mot de passe incorrect.")

  token = create_token(str(user["id"]), user["username"], user["token_version"])
  return {
    "access_token": token,
    "token_type":   "bearer",
    "username":     user["username"],
  }


@router.get("/me")
async def me(user: dict = Depends(require_auth), conn: psycopg.AsyncConnection = Depends(get_db)):
  user_id = str(user["id"])

  async with conn.cursor() as cur:
    await cur.execute(
      "SELECT id, title, status, file_size_bytes, duration_seconds, created_at, updated_at FROM orphee_jobs WHERE user_id = %s AND status = 'done' ORDER BY created_at DESC",
      (user_id,),
    )
    done_rows = await cur.fetchall()

  active = get_active_jobs_for_user(user_id)

  return {
    "id":                     user_id,
    "username":               user["username"],
    "email":                  user.get("email"),
    "is_admin":               user["is_admin"],
    "features":               user["features"],
    "max_jobs":               user["max_jobs"],
    "total_videos_created":   user["total_videos_created"],
    "total_duration_seconds": user["total_duration_seconds"],
    "total_clips_used":       user["total_clips_used"],
    "done_jobs": [
      {"job_id": str(j["id"]), "title": j["title"], "status": j["status"],
       "file_size_bytes": j["file_size_bytes"], "duration_seconds": j["duration_seconds"],
       "created_at": j["created_at"], "updated_at": j["updated_at"]}
      for j in done_rows
    ],
    "active_jobs": [
      {"job_id": j["job_id"], "title": j["title"], "status": j["status"],
       "message": j.get("message"), "created_at": j["created_at"], "updated_at": j["updated_at"]}
      for j in active
    ],
  }
