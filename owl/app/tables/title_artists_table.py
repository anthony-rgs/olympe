# Link a title to an artist (idempotent): insert relation if missing, ignore if it already exists
def link_title_to_artist(conn, *, title_id: int, artist_id: int) -> None:
  with conn.cursor() as cur:
    cur.execute("""
      INSERT INTO title_artists(title_id, artist_id)
      VALUES (%s, %s)
      ON CONFLICT DO NOTHING
    """, (title_id, artist_id))
