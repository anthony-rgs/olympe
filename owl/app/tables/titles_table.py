from typing import Optional

# Upsert a title by (name, album_id): insert if new, otherwise update nullable fields; returns the title ID
def upsert_title(conn, *, name: str, album_id: int,
  streams_count: Optional[int],
  track_time: Optional[str],
  cover_url: Optional[str],
  iframe: Optional[str]) -> int:
  """
  Source: tracks.json — uniqueness by (name, album_id)
  """
  
  sql = """
  INSERT INTO titles(name, album_id, streams_count, track_time, cover_url, iframe)
  VALUES (%s, %s, %s, %s, %s, %s)
  ON CONFLICT (name, album_id) DO UPDATE SET
    streams_count = COALESCE(EXCLUDED.streams_count, titles.streams_count),
    track_time    = COALESCE(EXCLUDED.track_time,    titles.track_time),
    cover_url     = COALESCE(EXCLUDED.cover_url,     titles.cover_url),
    iframe        = COALESCE(EXCLUDED.iframe,        titles.iframe)
  RETURNING id;
  """
  with conn.cursor() as cur:
    cur.execute(sql, (name, album_id, streams_count, track_time, cover_url, iframe))
    return cur.fetchone()[0]
