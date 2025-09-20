from typing import Optional

# Upsert an artist by case-insensitive name: insert if new, otherwise update nullable fields; returns the artist ID
def upsert_artist(conn, *, artist_name: str,
  artist_img: Optional[str] = None,
  monthly_listeners: Optional[int] = None) -> int:
  """
  Source: tracks.json — create/update artist (uniqueness by artist_name CITEXT)
  """

  sql = """
  INSERT INTO artists(artist_name, artist_img, monthly_listeners)
  VALUES (%s, %s, %s)
  ON CONFLICT (artist_name) DO UPDATE SET
    artist_img        = COALESCE(EXCLUDED.artist_img, artists.artist_img),
    monthly_listeners = COALESCE(EXCLUDED.monthly_listeners, artists.monthly_listeners)
  RETURNING id;
  """

  with conn.cursor() as cur:
    cur.execute(sql, (artist_name, artist_img, monthly_listeners))
    return cur.fetchone()[0]


# Update an existing artist with optional enrichment fields; returns False if the artist doesn't exist
def update_artist_enrichment(conn, *, artist_name: str,
  artist_img: Optional[str] = None,
  monthly_listeners: Optional[int] = None) -> bool:
  """
  Source: artists/ — UPDATE ONLY (does not create)
  """

  with conn.cursor() as cur:
    cur.execute("SELECT id FROM artists WHERE artist_name = %s", (artist_name,))
    row = cur.fetchone()
    if not row:
        return False
    cur.execute("""
      UPDATE artists SET
        artist_img = COALESCE(%s, artist_img),
        monthly_listeners = COALESCE(%s, monthly_listeners)
      WHERE id = %s
    """, (artist_img, monthly_listeners, row[0]))
    return True
