from fastapi import APIRouter, HTTPException
from ..db import get_conn

router = APIRouter()

# Get all artists
@router.get("")
def list_artists():
  with get_conn() as connection, connection.cursor() as cursor:
    cursor.execute("""
      SELECT 
        artists.id,
        artists.artist_name,
        artists.artist_img,
        artists.monthly_listeners,
        artists.updated_at,
        COUNT(DISTINCT title_artists.title_id) AS total_tracks
      FROM artists AS artists
      LEFT JOIN title_artists AS title_artists ON title_artists.artist_id = artists.id
      GROUP BY artists.id
      ORDER BY artists.monthly_listeners DESC NULLS LAST, artists.id DESC
    """)
    return cursor.fetchall()
    

# Get all artist data from an artist id
@router.get("/{artist_id}")
def artist_all_data(artist_id: int):
  with get_conn() as connection, connection.cursor() as cursor:
    # 1) Artist (tuple)
    cursor.execute("""
      SELECT id, artist_name, artist_img, monthly_listeners, created_at, updated_at
      FROM artists
      WHERE id = %s
    """, (artist_id,))
    artist = cursor.fetchone()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    # 2) Artist’s albums + total number of titles per album
    #    -> tuple: (id, title, cover_url, release_year, updated_at, total_tracks)
    cursor.execute("""
      SELECT 
        albums.id,
        albums.title,
        albums.cover_url,
        albums.release_year,
        albums.updated_at,
        COUNT(DISTINCT album_titles.id) AS total_tracks
      FROM albums
      JOIN album_artists ON album_artists.album_id = albums.id
      LEFT JOIN titles AS album_titles ON album_titles.album_id = albums.id
      WHERE album_artists.artist_id = %s
      GROUP BY albums.id, albums.title, albums.cover_url, albums.release_year, albums.updated_at
      ORDER BY albums.release_year DESC NULLS LAST, albums.id DESC
    """, (artist_id,))
    albums = cursor.fetchall()

    # 3) Titles where the artist appears
    cursor.execute("""
      SELECT titles.id, titles.name, titles.album_id, titles.streams_count, titles.track_time, titles.cover_url, titles.iframe, titles.updated_at
      FROM titles
      JOIN title_artists ON title_artists.title_id = titles.id
      WHERE title_artists.artist_id = %s
      ORDER BY titles.streams_count DESC NULLS LAST, titles.id DESC
    """, (artist_id,))
    titles = cursor.fetchall()

    # 4) All artists for each of those titles (like /albums)
    cursor.execute("""
      SELECT title_artists.title_id, artists.id AS artist_id, artists.artist_name
      FROM title_artists
      JOIN artists ON artists.id = title_artists.artist_id
      WHERE title_artists.title_id IN (
        SELECT titles_in.id
        FROM titles AS titles_in
        JOIN title_artists AS ta2 ON ta2.title_id = titles_in.id
        WHERE ta2.artist_id = %s
      )
      ORDER BY title_artists.title_id ASC, artists.artist_name ASC
    """, (artist_id,))
    titles_artists = cursor.fetchall()

    # 5) Album-level “project artists” present on 100% of tracks for each listed album
    cursor.execute("""
      WITH albums_of AS (
        SELECT albums.id
        FROM albums
        JOIN album_artists ON album_artists.album_id = albums.id
        WHERE album_artists.artist_id = %s
      ), total_per_album AS (
        SELECT album_id, COUNT(*)::int AS total_count
        FROM titles
        WHERE album_id IN (SELECT id FROM albums_of)
        GROUP BY album_id
      )
      SELECT titles.album_id,
        artists.id   AS artist_id,
        artists.artist_name,
        artists.artist_img
      FROM title_artists
      JOIN titles  ON titles.id  = title_artists.title_id
      JOIN artists ON artists.id = title_artists.artist_id
      JOIN total_per_album ON total_per_album.album_id = titles.album_id
      WHERE titles.album_id IN (SELECT id FROM albums_of)
      GROUP BY titles.album_id, artists.id, artists.artist_name, artists.artist_img, total_per_album.total_count
      HAVING COUNT(*) = total_per_album.total_count
      ORDER BY titles.album_id ASC, artists.artist_name ASC
    """, (artist_id,))
    albums_artists = cursor.fetchall()

  return {
      "artist": artist,               
      "albums": albums,               
      "titles": titles,               
      "titles_artists": titles_artists,   
      "albums_artists": albums_artists    
  }