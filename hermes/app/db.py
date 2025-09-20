import os
from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row

# Read from env and fail fast if missing
_db_url = os.getenv("DATABASE_URL")
if not _db_url:
    raise RuntimeError("DATABASE_URL is not set. Provide it via docker-compose/.env")

# Normalize scheme (some tools set postgres://; psycopg expects postgresql://)
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

@contextmanager
def get_conn():
  """Yield a psycopg connection with dict rows (JSON-friendly)."""
  with psycopg.connect(_db_url, row_factory=dict_row) as conn:
    yield conn