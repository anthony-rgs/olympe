import glob, os
from typing import Optional

# Return the latest JSON path: if given a file, return it; if a directory, pick the newest *.json by mtime; otherwise raise
def resolve_latest_json(path_or_dir: str) -> str:
  """If file → return it; if dir → pick latest *.json; else error."""
  
  if os.path.isfile(path_or_dir):
    return path_or_dir
  
  if os.path.isdir(path_or_dir):
    # Collect *.json files inside the directory
    json_files = [file_path for file_path in glob.glob(os.path.join(path_or_dir, "*.json")) if os.path.isfile(file_path)]
    
    if not json_files:
      raise FileNotFoundError(f"No .json in {path_or_dir}")
    
    # Choose the most recently modified file
    return max(json_files, key=os.path.getmtime)
  raise FileNotFoundError(path_or_dir)


# Convert a value to int safely: strip spaces/commas; return None if not a clean integer.
def safe_int(value) -> Optional[int]:
  if value is None:
    return None
  normalized = str(value).strip().replace(",", "")
  return int(normalized) if normalized.isdigit() else None


# Normalize strings: coalesce falsy to "" and trim spaces to avoid duplicates.
def normalize_str(text) -> str:
  """Trim helper (avoid space-based duplicates)."""
  return (text or "").strip()
