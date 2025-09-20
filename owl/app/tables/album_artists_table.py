# Link an album to an artist (idempotent): insert relation if missing, ignore if it already exists
def link_album_to_artist(conn, *, album_id: int, artist_id: int) -> None:
  with conn.cursor() as cur:
    cur.execute("""
      INSERT INTO album_artists(album_id, artist_id)
      VALUES (%s, %s)
      ON CONFLICT DO NOTHING
    """, (album_id, artist_id))
