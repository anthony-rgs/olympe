"""
Enrichment from artists/:
  - DOES NOT CREATE ANYTHING (no albums, no tracks)
  - Only updates artist_img + monthly_listeners for artists already present
"""

import os, glob, json
from typing import Any, Dict, List
from .config import ARTISTS_PATH
from .db import get_conn
from .tables.artists_table import update_artist_enrichment
from .utils import normalize_str

# Iterate over artist JSON payloads from ARTISTS_PATH: read either a single file or all *.json files in the folder,
# return a flat list of dicts (skip invalid entries, warn on read errors).
def _iter_artist_dicts() -> List[Dict[str, Any]]:
    # Resolve path and short-circuit if missing
    artists_path = ARTISTS_PATH
    if not os.path.exists(artists_path):
      print(f"[OWL] No artists path found: {artists_path} — skipping.")
      return []

    # Build the list of files to read (single file or all *.json in the directory)
    files_to_read = (
      [artists_path]
      if os.path.isfile(artists_path)
      else [path for path in glob.glob(os.path.join(artists_path, "*.json")) if os.path.isfile(path)]
    )

    # Accumulate normalized artist dicts
    artists: List[Dict[str, Any]] = []

    # Read each JSON file and normalize payloads to dicts
    for file_path in files_to_read:
      try:
        # Load JSON payload
        with open(file_path, "r", encoding="utf-8") as file_handle:
          payload = json.load(file_handle)

        # Normalize: allow a single dict or a list of dicts
        if isinstance(payload, dict):
          artists.append(payload)
        elif isinstance(payload, list):
          artists.extend([artist for artist in payload if isinstance(artist, dict)])

      except Exception as err:
        # Non-fatal: log and continue with the next file
        print(f"[OWL] WARN reading {file_path}: {err}")

    return artists


# Ingest artist enrichment payloads: for each artist dict, update existing DB rows (no creation);
# returns counts of updated vs skipped (not found) artists.
def ingest_artists() -> dict[str, int]:
  # Gather normalized artist dicts from ARTISTS_PATH
  artist_dicts = _iter_artist_dicts()
  print(f"[OWL] Artists enrichment — {len(artist_dicts)} objects")

  # Counters
  updated = 0
  skipped = 0

  # DB session: try to update each artist with optional fields
  with get_conn() as conn:
    for artist in artist_dicts:
      updated_flag = update_artist_enrichment(
        conn,
        artist_name=normalize_str(artist.get("artist_name")),  # sanitize/normalize artist name
        artist_img=artist.get("artist_img"),
        monthly_listeners=artist.get("track_listeners"),
      )
      if updated_flag:
        updated += 1
      else:
        skipped += 1

  return {"artists_updated": updated, "artists_skipped_not_found": skipped}