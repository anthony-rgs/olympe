from fastapi import APIRouter
from ..db import get_conn

router = APIRouter()

@router.get("")
def list_titles():
  with get_conn() as connection, connection.cursor() as cursor:
    cursor.execute("""
      SELECT 
        titles.id,
        titles.name,
        titles.album_id,
        albums.title AS album_name,
        titles.streams_count,
        titles.track_time,
        titles.cover_url,
        titles.iframe,
        titles.updated_at,
        COALESCE(
          json_agg(
            json_build_object('artist_id', artists.id, 'artist_name', artists.artist_name)
          ) FILTER (WHERE artists.id IS NOT NULL),
          '[]'
        ) AS artists
      FROM titles AS titles
      LEFT JOIN albums AS albums ON albums.id = titles.album_id
      LEFT JOIN title_artists AS title_artists ON title_artists.title_id = titles.id
      LEFT JOIN artists AS artists ON artists.id = title_artists.artist_id
      GROUP BY titles.id, albums.title
      ORDER BY titles.streams_count DESC NULLS LAST, titles.id DESC
    """)
    return cursor.fetchall()