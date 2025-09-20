from fastapi import APIRouter, HTTPException
from ..db import get_conn

router = APIRouter()

# List all albums 
@router.get("")
def list_albums():
  with get_conn() as connection, connection.cursor() as cursor:
    cursor.execute("""
      SELECT 
        album.id,
        album.title,
        album.cover_url,
        album.release_year,
        album.updated_at,
        COUNT(DISTINCT album_titles.id) AS total_tracks,
        COALESCE((
          SELECT json_agg(
              json_build_object('artist_id', project_artists.id, 'artist_name', project_artists.artist_name)
              ORDER BY project_artists.artist_name
            )
          FROM (
            -- Artists present on EVERY track of the album
            SELECT artists.id, artists.artist_name
            FROM artists
            JOIN title_artists ON title_artists.artist_id = artists.id
            JOIN titles AS titles_in_album ON titles_in_album.id = title_artists.title_id
            WHERE titles_in_album.album_id = album.id
            GROUP BY artists.id, artists.artist_name
            HAVING COUNT(*) = (
              -- Compare with the total number of titles in this album
              SELECT COUNT(*) 
              FROM titles AS titles_of_album
              WHERE titles_of_album.album_id = album.id
            )
          ) AS project_artists
        ), '[]'::json) AS artists
      FROM albums AS album
      LEFT JOIN titles AS album_titles ON album_titles.album_id = album.id
      GROUP BY album.id
      ORDER BY album.release_year DESC NULLS LAST, album.id DESC
    """)
    return cursor.fetchall()


# Get all data from an album id
@router.get("/{album_id}")
def album_all_data(album_id: int):
  with get_conn() as connection, connection.cursor() as cursor:
    # 1) Album (tuple)
    cursor.execute("""
      SELECT id, title, cover_url, release_year, updated_at
      FROM albums
      WHERE id = %s
    """, (album_id,))
    album = cursor.fetchone()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # 2) “Primary” album artists = present on 100% of the album’s titles
    cursor.execute("""
      WITH total_titles AS (
        SELECT COUNT(*)::int AS total_count
        FROM titles
        WHERE album_id = %s
      )
      SELECT artists.id, artists.artist_name, artists.artist_img
      FROM artists
      JOIN title_artists ON title_artists.artist_id = artists.id
      JOIN titles AS titles_in_album ON titles_in_album.id = title_artists.title_id
      CROSS JOIN total_titles
      WHERE titles_in_album.album_id = %s
      GROUP BY artists.id, artists.artist_name, artists.artist_img, total_titles.total_count
      HAVING COUNT(*) = total_titles.total_count
      ORDER BY artists.artist_name ASC
    """, (album_id, album_id))
    album_artists = cursor.fetchall()

    # Fallback if no artist is present on 100% of titles → pick artists present on >= 60% of titles
    if not album_artists:
      cursor.execute("""
        WITH total_titles AS (
          SELECT COUNT(*)::int AS total_count
          FROM titles
          WHERE album_id = %s
        )
        SELECT artists.id, artists.artist_name, artists.artist_img
        FROM artists
        JOIN title_artists ON title_artists.artist_id = artists.id
        JOIN titles AS titles_in_album ON titles_in_album.id = title_artists.title_id
        CROSS JOIN total_titles
        WHERE titles_in_album.album_id = %s
        GROUP BY artists.id, artists.artist_name, artists.artist_img, total_titles.total_count
        HAVING COUNT(*)::float >= total_titles.total_count * 0.6
        ORDER BY artists.artist_name ASC
      """, (album_id, album_id))
      album_artists = cursor.fetchall()

    # 3) Album titles (tuples)
    cursor.execute("""
      SELECT id, name, album_id, streams_count, track_time, cover_url, iframe, updated_at
      FROM titles
      WHERE album_id = %s
      ORDER BY streams_count DESC NULLS LAST, id DESC
    """, (album_id,))
    titles = cursor.fetchall()

    # 4) Artists per title (tuples) → (title_id, artist_id, artist_name)
    cursor.execute("""
      SELECT title_artists.title_id, artists.id AS artist_id, artists.artist_name
      FROM title_artists
      JOIN artists ON artists.id = title_artists.artist_id
      WHERE title_artists.title_id IN (SELECT id FROM titles WHERE album_id = %s)
      ORDER BY title_artists.title_id ASC, artists.artist_name ASC
    """, (album_id,))
    titles_artists = cursor.fetchall()

  return {
      "album": album,                
      "artists": album_artists,      
      "titles": titles,              
      "titles_artists": titles_artists 
  }
