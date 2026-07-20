import asyncio
from datetime import datetime, timedelta, timezone

import psycopg
import resend
from jose import jwt
from psycopg.rows import dict_row

from ..config import API_URL, APP_URL, DATABASE_URL, JWT_SECRET, RESEND_API_KEY, RESEND_FROM

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


def _base_html(icon: str, heading: str, body_content: str, footer_note: str = "") -> str:
  return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

        <!-- Header -->
        <tr><td style="padding-bottom:32px;text-align:center;">
          <span style="font-size:13px;font-weight:700;letter-spacing:3px;color:#666;text-transform:uppercase;">Vexia Studio</span>
        </td></tr>

        <!-- Card -->
        <tr><td style="background:#141414;border-radius:16px;border:1px solid #222;overflow:hidden;">

          <!-- Icon + Heading -->
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td style="padding:40px 40px 24px;text-align:center;">
              <div style="font-size:48px;line-height:1;margin-bottom:20px;">{icon}</div>
              <h1 style="margin:0;font-size:22px;font-weight:700;color:#f0f0f0;letter-spacing:-0.3px;">{heading}</h1>
            </td></tr>
          </table>

          <!-- Body -->
          {body_content}

        </td></tr>

        <!-- Footer -->
        <tr><td style="padding-top:24px;text-align:center;">
          <p style="margin:0;font-size:12px;color:#444;">
            vexia.studio{(' &nbsp;·&nbsp; ' + footer_note) if footer_note else ''}
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _success_html(job_title: str, duration: int, download_url: str) -> str:
  duration_str = _fmt_duration(duration)
  body = f"""
    <!-- Info -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:0 40px 32px;">
        <table width="100%" cellpadding="0" cellspacing="0"
               style="background:#1a1a1a;border-radius:10px;border:1px solid #2a2a2a;">
          <tr><td style="padding:20px 24px;">
            <p style="margin:0 0 6px;font-size:11px;font-weight:600;letter-spacing:2px;color:#555;text-transform:uppercase;">Vidéo</p>
            <p style="margin:0;font-size:15px;font-weight:600;color:#e0e0e0;">{job_title}</p>
          </td></tr>
          <tr><td style="padding:0 24px 20px;">
            <p style="margin:0 0 6px;font-size:11px;font-weight:600;letter-spacing:2px;color:#555;text-transform:uppercase;">Durée</p>
            <p style="margin:0;font-size:15px;font-weight:600;color:#e0e0e0;">{duration_str}</p>
          </td></tr>
        </table>
      </td></tr>
    </table>

    <!-- Buttons -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:0 40px 40px;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="padding-right:8px;" width="50%">
              <a href="{APP_URL}/user"
                 style="display:block;text-align:center;padding:14px;border-radius:10px;
                        background:#1e1e1e;border:1px solid #333;color:#aaa;
                        font-size:13px;font-weight:600;text-decoration:none;">
                Espace client
              </a>
            </td>
            <td style="padding-left:8px;" width="50%">
              <a href="{download_url}"
                 style="display:block;text-align:center;padding:14px;border-radius:10px;
                        background:#22c55e;color:#fff;
                        font-size:13px;font-weight:700;text-decoration:none;">
                Télécharger ↓
              </a>
            </td>
          </tr>
        </table>
      </td></tr>
    </table>"""

  return _base_html("✅", "Votre vidéo est prête !", body, f"Lien de téléchargement valide {_DL_TOKEN_HOURS}h")


def _error_html(job_title: str, error: str) -> str:
  error_display = (error[:200] + "…") if len(error) > 200 else error
  body = f"""
    <!-- Info -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:0 40px 32px;">
        <table width="100%" cellpadding="0" cellspacing="0"
               style="background:#1a1a1a;border-radius:10px;border:1px solid #2a2a2a;">
          <tr><td style="padding:20px 24px;">
            <p style="margin:0 0 6px;font-size:11px;font-weight:600;letter-spacing:2px;color:#555;text-transform:uppercase;">Vidéo</p>
            <p style="margin:0;font-size:15px;font-weight:600;color:#e0e0e0;">{job_title}</p>
          </td></tr>
          <tr><td style="padding:0 24px 20px;">
            <p style="margin:0 0 6px;font-size:11px;font-weight:600;letter-spacing:2px;color:#555;text-transform:uppercase;">Erreur</p>
            <p style="margin:0;font-size:13px;color:#f87171;font-family:monospace;word-break:break-all;">{error_display}</p>
          </td></tr>
        </table>
      </td></tr>
    </table>

    <!-- Button -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:0 40px 40px;">
        <a href="{APP_URL}/user"
           style="display:block;text-align:center;padding:14px;border-radius:10px;
                  background:#1e1e1e;border:1px solid #333;color:#aaa;
                  font-size:13px;font-weight:600;text-decoration:none;">
          Voir l'espace client
        </a>
      </td></tr>
    </table>"""

  return _base_html("❌", "Une erreur est survenue", body)


async def send_video_ready(user_id: str, job_id: str, job_title: str, duration: int) -> None:
  if not RESEND_API_KEY:
    return

  email = await _get_user_email(user_id)
  if not email:
    return

  token = create_download_token(job_id)
  download_url = f"{API_URL}/jobs/{job_id}/download?token={token}"

  resend.api_key = RESEND_API_KEY
  await asyncio.to_thread(
    resend.Emails.send,
    {
      "from": RESEND_FROM,
      "to": [email],
      "subject": f"✅ Votre vidéo est prête — {job_title}",
      "html": _success_html(job_title, duration, download_url),
    },
  )


async def send_video_failed(user_id: str, job_id: str, job_title: str, error: str) -> None:
  if not RESEND_API_KEY:
    return

  email = await _get_user_email(user_id)
  if not email:
    return

  resend.api_key = RESEND_API_KEY
  await asyncio.to_thread(
    resend.Emails.send,
    {
      "from": RESEND_FROM,
      "to": [email],
      "subject": f"❌ Erreur de rendu — {job_title}",
      "html": _error_html(job_title, error),
    },
  )
