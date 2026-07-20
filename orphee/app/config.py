import os

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
  raise RuntimeError("ANTHROPIC_API_KEY is not set. Provide it via docker-compose/.env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
  raise RuntimeError("DATABASE_URL is not set. Provide it via docker-compose/.env")

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "/storage/jobs")

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
  raise RuntimeError("JWT_SECRET is not set. Provide it via docker-compose/.env")

JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "72"))

RESEND_API_KEY        = os.getenv("RESEND_API_KEY", "")
RESEND_FROM           = os.getenv("RESEND_FROM", "notifications@vexia.studio")
RESEND_TEMPLATE_READY = os.getenv("RESEND_TEMPLATE_READY", "")
RESEND_TEMPLATE_FAILED = os.getenv("RESEND_TEMPLATE_FAILED", "")
APP_URL        = os.getenv("APP_URL", "https://vexia.studio")
API_URL        = os.getenv("API_URL", "https://orphee.olympe.center")