"""
Main ingestion: EVERYTHING comes from tracks.json (artists, albums, titles, links, meta)
"""

import json
from .config import TRACKS_PATH
from .db import get_conn
from .utils import resolve_latest_json, safe_int, normalize_str
from .tables.tracks_meta_table import upsert_tracks_meta
from .tables.artists_table import upsert_artist
from .tables.albums_table import upsert_album
from .tables.titles_table import upsert_title
from .tables.album_artists_table import link_album_to_artist
from .tables.title_artists_table import link_title_to_artist

# Ingest tracks JSON: upsert meta (link/cover), then for each track upsert artists, album, and title,
# link artists↔album and artists↔title; return counters of touched rows
def ingest_tracks() -> dict[str, int]:
  # Resolve and load the latest tracks JSON file
  path = resolve_latest_json(TRACKS_PATH)
  print(f"[OWL] Tracks JSON: {path}")
  with open(path, "r", encoding="utf-8") as file_handle:
    data = json.load(file_handle)

  # Extract top-level meta
  link, cover_img, cover_artist = data.get("link"), data.get("cover_img"), data.get("cover_artist")

  # Counters
  artists_touched = 0
  albums_touched = 0
  titles_touched = 0

  with get_conn() as conn:
    # Upsert meta (singleton row)
    upsert_tracks_meta(conn, link=link, cover_img=cover_img, cover_artist=cover_artist)

    # Upsert each track and its relations
    for track in data.get("tracks", []):
      # Upsert artists and collect their IDs
      artist_ids: list[int] = []
      for artist_name in (track.get("artists") or []):
        artist_id = upsert_artist(conn, artist_name=normalize_str(artist_name))
        artist_ids.append(artist_id)
        artists_touched += 1

      # Upsert album
      album_title = normalize_str(track.get("album"))
      album_id = upsert_album(
        conn,
        title=album_title,
        cover_url=track.get("track_img"),
        release_year=safe_int(track.get("track_year")),
      )
      albums_touched += 1

      # Link album ↔ artists
      for artist_id in artist_ids:
        link_album_to_artist(conn, album_id=album_id, artist_id=artist_id)

      # Upsert title (track)
      streams_raw = track.get("play_count") or track.get("track_play_count")
      title_id = upsert_title(
        conn,
        name=normalize_str(track.get("track_name")),
        album_id=album_id,
        streams_count=safe_int(streams_raw),
        track_time=track.get("track_time"),
        cover_url=track.get("track_img"),
        iframe=track.get("track_iframe") or track.get("track_embed"),
      )
      titles_touched += 1

      # Link title ↔ artists
      for artist_id in artist_ids:
        link_title_to_artist(conn, title_id=title_id, artist_id=artist_id)

  # Summary counters
  return {"artists_touched": artists_touched, "albums_touched": albums_touched, "titles_touched": titles_touched}
