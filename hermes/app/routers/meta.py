from fastapi import APIRouter
from ..db import get_conn

router = APIRouter()

# Get global tracks meta data
@router.get("/tracks")
def tracks_meta():
  with get_conn() as conn, conn.cursor() as cur:
    cur.execute("SELECT id, link, cover_img, cover_artist, updated_at FROM tracks_meta WHERE id = 1")
    return cur.fetchone() or {}
