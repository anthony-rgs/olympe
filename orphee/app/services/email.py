import asyncio
import json
import urllib.request
from datetime import datetime, timedelta, timezone

import psycopg
from jose import jwt
from psycopg.rows import dict_row

from ..config import (
  API_URL, APP_URL, DATABASE_URL, JWT_SECRET,
  RESEND_API_KEY, RESEND_FROM,
  RESEND_TEMPLATE_FAILED, RESEND_TEMPLATE_READY,
)

_DL_TOKEN_HOURS = 48


def create_download_token(job_id: str) -> str:
  expire = datetime.now(timezone.utc) + timedelta(hours=_DL_TOKEN_HOURS)
  return jwt.encode(
    {"job_id": job_id, "exp": expire, "type": "dl"},
    JWT_SECRET,
    algorithm="HS256",
  )


def verify_download_token(token: str) -> str | None:
  try:
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    if payload.get("type") != "dl":
      return None
    return payload.get("job_id")
  except Exception:
    return None


async def _get_user_email(user_id: str) -> str | None:
  async with await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row) as conn:
    async with conn.cursor() as cur:
      await cur.execute("SELECT email FROM orphee_users WHERE id = %s", (user_id,))
      row = await cur.fetchone()
  return row["email"] if row and row.get("email") else None


def _fmt_duration(seconds: int) -> str:
  if seconds < 60:
    return f"{seconds}s"
  m, s = divmod(seconds, 60)
  return f"{m}m {s:02d}s" if s else f"{m}m"


def _send_template(to: str, subject: str, template_id: str, variables: dict) -> None:
  payload = json.dumps({
    "from": RESEND_FROM,
    "to": [to],
    "subject": subject,
    "template_id": template_id,
    "with": variables,
  }).encode()
  req = urllib.request.Request(
    "https://api.resend.com/emails",
    data=payload,
    headers={
      "Authorization": f"Bearer {RESEND_API_KEY}",
      "Content-Type": "application/json",
    },
  )
  with urllib.request.urlopen(req) as resp:
    resp.read()


async def send_video_ready(user_id: str, job_id: str, job_title: str, duration: int) -> None:
  if not RESEND_API_KEY or not RESEND_TEMPLATE_READY:
    return

  email = await _get_user_email(user_id)
  if not email:
    return

  token = create_download_token(job_id)
  download_url = f"{API_URL}/jobs/{job_id}/download?token={token}"

  await asyncio.to_thread(_send_template, email,
    f"✅ Votre vidéo est prête — {job_title}",
    RESEND_TEMPLATE_READY,
    {
      "job_title": job_title,
      "duration": _fmt_duration(duration),
      "download_url": download_url,
      "app_url": APP_URL,
    },
  )


async def send_video_failed(user_id: str, _job_id: str, job_title: str, error: str) -> None:
  if not RESEND_API_KEY or not RESEND_TEMPLATE_FAILED:
    return

  email = await _get_user_email(user_id)
  if not email:
    return

  error_display = (error[:200] + "…") if len(error) > 200 else error

  await asyncio.to_thread(_send_template, email,
    f"❌ Erreur de rendu — {job_title}",
    RESEND_TEMPLATE_FAILED,
    {
      "job_title": job_title,
      "error": error_display,
      "app_url": APP_URL,
    },
  )
