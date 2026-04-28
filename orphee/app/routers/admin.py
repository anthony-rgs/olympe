import os
import shutil

import psutil
import psycopg
from fastapi import APIRouter, Depends, HTTPException
from psycopg.errors import UniqueViolation
from pydantic import BaseModel

from ..auth import hash_password, require_auth
from ..config import COOKIES_DIR, STORAGE_ROOT
from ..db import get_db

router = APIRouter()


# ── Dépendance admin ──────────────────────────────────────────────────────────

async def require_admin(user: dict = Depends(require_auth)) -> dict:
  if not user["is_admin"]:
    raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs.")
  return user


# ── Schémas ───────────────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
  username: str
  password: str
  is_admin: bool = False
  features: list[str] = []
  max_jobs: int = 1


class UpdateUserRequest(BaseModel):
  username:  str | None = None
  password:  str | None = None
  is_admin:  bool | None = None
  features:  list[str] | None = None
  max_jobs:  int | None = None


class UpdateMetricsRequest(BaseModel):
  money_earned: float


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
  _: dict = Depends(require_admin),
  conn: psycopg.AsyncConnection = Depends(get_db),
):
  """Retourne tous les users avec leur dernier job."""
  async with conn.cursor() as cur:
    await cur.execute("""
      SELECT
        u.id, u.username, u.is_admin, u.features, u.max_jobs,
        u.total_videos_created, u.total_duration_seconds, u.total_clips_used,
        u.created_at,
        COALESCE(
          json_agg(
            json_build_object(
              'id',               j.id,
              'title',            j.title,
              'status',           j.status,
              'file_size_bytes',  j.file_size_bytes,
              'duration_seconds', j.duration_seconds,
              'created_at',       j.created_at
            ) ORDER BY j.created_at DESC
          ) FILTER (WHERE j.id IS NOT NULL),
          '[]'::json
        ) AS jobs
      FROM orphee_users u
      LEFT JOIN orphee_jobs j ON j.user_id = u.id AND j.status = 'done'
      GROUP BY u.id
      ORDER BY u.created_at
    """)
    rows = await cur.fetchall()

  return [_format_user_row(r) for r in rows]


@router.post("/users", status_code=201)
async def create_user(
  body: CreateUserRequest,
  _: dict = Depends(require_admin),
  conn: psycopg.AsyncConnection = Depends(get_db),
):
  try:
    async with conn.cursor() as cur:
      await cur.execute(
        """
        INSERT INTO orphee_users (username, password_hash, is_admin, features, max_jobs)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, username, is_admin, features, max_jobs, created_at
        """,
        (body.username, hash_password(body.password), body.is_admin, body.features, body.max_jobs),
      )
      row = await cur.fetchone()
    await conn.commit()
  except UniqueViolation:
    raise HTTPException(status_code=409, detail=f"Le nom d'utilisateur '{body.username}' est déjà pris.")
  return {"id": str(row["id"]), "username": row["username"], "is_admin": row["is_admin"],
          "features": row["features"], "max_jobs": row["max_jobs"], "created_at": row["created_at"]}


@router.patch("/users/{user_id}")
async def update_user(
  user_id: str,
  body: UpdateUserRequest,
  _: dict = Depends(require_admin),
  conn: psycopg.AsyncConnection = Depends(get_db),
):
  fields, values = [], []

  if body.username  is not None: fields.append("username = %s");      values.append(body.username)
  if body.password  is not None: fields.append("password_hash = %s"); values.append(hash_password(body.password))
  if body.is_admin  is not None: fields.append("is_admin = %s");      values.append(body.is_admin)
  if body.features  is not None: fields.append("features = %s");      values.append(body.features)
  if body.max_jobs  is not None: fields.append("max_jobs = %s");      values.append(body.max_jobs)

  if not fields:
    raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour.")

  values.append(user_id)
  async with conn.cursor() as cur:
    await cur.execute(
      f"UPDATE orphee_users SET {', '.join(fields)} WHERE id = %s RETURNING id",
      values,
    )
    if not await cur.fetchone():
      raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
  await conn.commit()

  # Cleanup si max_jobs a diminué
  if body.max_jobs is not None:
    async with conn.cursor() as cur:
      await cur.execute(
        "SELECT id FROM orphee_jobs WHERE user_id = %s AND status = 'done' ORDER BY created_at ASC",
        (user_id,),
      )
      done_jobs = await cur.fetchall()

    excess = len(done_jobs) - body.max_jobs
    if excess > 0:
      to_delete = done_jobs[:excess]
      for job in to_delete:
        job_id = str(job["id"])
        job_dir = os.path.join(STORAGE_ROOT, user_id, job_id)
        if os.path.isdir(job_dir):
          shutil.rmtree(job_dir, ignore_errors=True)
      ids_to_delete = [str(j["id"]) for j in to_delete]
      async with conn.cursor() as cur:
        await cur.execute(
          "DELETE FROM orphee_jobs WHERE id = ANY(%s)",
          (ids_to_delete,),
        )
      await conn.commit()

  return {"detail": "Utilisateur mis à jour."}


@router.post("/users/{user_id}/revoke")
async def revoke_user(
  user_id: str,
  _: dict = Depends(require_admin),
  conn: psycopg.AsyncConnection = Depends(get_db),
):
  """Invalide tous les tokens actifs du user en incrémentant token_version."""
  async with conn.cursor() as cur:
    await cur.execute(
      "UPDATE orphee_users SET token_version = token_version + 1 WHERE id = %s RETURNING id",
      (user_id,),
    )
    if not await cur.fetchone():
      raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
  await conn.commit()
  return {"detail": "Tokens révoqués."}


@router.delete("/users/{user_id}")
async def delete_user(
  user_id: str,
  _: dict = Depends(require_admin),
  conn: psycopg.AsyncConnection = Depends(get_db),
):
  """Supprime le user, ses jobs en DB et son dossier de stockage."""
  async with conn.cursor() as cur:
    await cur.execute(
      "DELETE FROM orphee_users WHERE id = %s RETURNING id",
      (user_id,),
    )
    if not await cur.fetchone():
      raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
  await conn.commit()

  user_dir = os.path.join(STORAGE_ROOT, user_id)
  if os.path.isdir(user_dir):
    shutil.rmtree(user_dir, ignore_errors=True)

  cookie_file = os.path.join(COOKIES_DIR, f"{user_id}.txt")
  if os.path.isfile(cookie_file):
    os.remove(cookie_file)

  return {"detail": "Utilisateur supprimé."}




# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_user_row(r: dict) -> dict:
  jobs = r.get("jobs") or []
  return {
    "id":                     str(r["id"]),
    "username":               r["username"],
    "is_admin":               r["is_admin"],
    "features":               r["features"],
    "max_jobs":               r["max_jobs"],
    "total_videos_created":   r["total_videos_created"],
    "total_duration_seconds": r["total_duration_seconds"],
    "total_clips_used":       r["total_clips_used"],
    "created_at":             r["created_at"],
    "jobs": [
      {"id": str(j["id"]), "title": j["title"], "status": j["status"],
       "file_size_bytes": j.get("file_size_bytes"), "duration_seconds": j.get("duration_seconds"),
       "created_at": j["created_at"]}
      for j in jobs
    ],
  }


@router.patch("/metrics")
async def update_metrics(
  body: UpdateMetricsRequest,
  _: dict = Depends(require_admin),
  conn: psycopg.AsyncConnection = Depends(get_db),
):
  await conn.execute("UPDATE orphee_metrics SET money_earned = %s", (body.money_earned,))
  await conn.commit()
  return {"detail": "Métriques mises à jour."}


@router.get("/metrics/system")
async def system_metrics(_: dict = Depends(require_admin)):
  cpu = psutil.cpu_percent(interval=0.5)
  mem = psutil.virtual_memory()
  disk = psutil.disk_usage("/")
  net = psutil.net_io_counters()
  return {
    "cpu_percent": cpu,
    "ram": {
      "total_gb": round(mem.total / 1_073_741_824, 2),
      "used_gb":  round(mem.used  / 1_073_741_824, 2),
      "free_gb":  round(mem.available / 1_073_741_824, 2),
      "percent":  mem.percent,
    },
    "disk": {
      "total_gb": round(disk.total / 1_073_741_824, 2),
      "used_gb":  round(disk.used  / 1_073_741_824, 2),
      "free_gb":  round(disk.free  / 1_073_741_824, 2),
      "percent":  disk.percent,
    },
    "network": {
      "bytes_sent": net.bytes_sent,
      "bytes_recv": net.bytes_recv,
    },
  }
