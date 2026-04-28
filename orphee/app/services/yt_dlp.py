import asyncio
import os
from typing import Optional

from ..job_store import register_process, unregister_process, update_job, DOWNLOADING


def _parse_seconds(time_str: str) -> float:
  """Convertit HH:MM:SS ou MM:SS en secondes."""
  parts = [float(p) for p in time_str.strip().split(":")]
  if len(parts) == 3:
    return parts[0] * 3600 + parts[1] * 60 + parts[2]
  if len(parts) == 2:
    return parts[0] * 60 + parts[1]
  return parts[0]


def _fmt_time(seconds: float) -> str:
  """Convertit des secondes en HH:MM:SS.mmm."""
  h = int(seconds // 3600)
  m = int((seconds % 3600) // 60)
  s = seconds % 60
  return f"{h:02d}:{m:02d}:{s:06.3f}"


async def _run_ytdlp(cmd: list[str], job_id: str) -> tuple[int, bytes]:
  process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )
  register_process(job_id, process)
  _, stderr = await process.communicate()
  unregister_process(job_id)
  return process.returncode, stderr


async def download(job_id: str, url: str, output_dir: str,
                   cookies_file: Optional[str] = None,
                   start_time: Optional[str] = None, duration: Optional[int] = None) -> tuple[str, bool]:
  """Télécharge une vidéo via yt-dlp (YouTube, Instagram, TikTok, Vimeo...).

  Retourne le chemin du fichier téléchargé.
  Lève une RuntimeError si le téléchargement échoue.
  """
  update_job(job_id, status=DOWNLOADING, message="Téléchargement en cours...")

  output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

  base_cmd = [
    "yt-dlp",
    "--no-playlist",
    "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio/bestvideo+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
    "--merge-output-format", "mp4",
    "--output", output_template,
  ]
  if cookies_file:
    base_cmd += ["--cookies", cookies_file, "--extractor-args", "youtube:player_client=web"]
  else:
    base_cmd += ["--extractor-args", "youtube:player_client=android_vr"]

  sections_args = []
  if start_time is not None and duration is not None:
    start_s = _parse_seconds(start_time)
    end_s = start_s + duration + 2
    sections_args = ["--download-sections", f"*{_fmt_time(start_s)}-{_fmt_time(end_s)}"]

  def _clear_dir():
    for f in os.listdir(output_dir):
      os.remove(os.path.join(output_dir, f))

  sections_used = False
  returncode, stderr = await _run_ytdlp(base_cmd + sections_args + [url], job_id)

  if returncode == 0 and sections_args:
    sections_used = True
  elif returncode != 0 and sections_args:
    print(f"[yt-dlp] --download-sections a échoué, retry sans sections")
    _clear_dir()
    returncode, stderr = await _run_ytdlp(base_cmd + [url], job_id)

  if returncode != 0:
    error = stderr.decode().strip().splitlines()[-1] if stderr else "Erreur inconnue"
    raise RuntimeError(f"yt-dlp a échoué : {error}")

  files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
  if not files:
    raise RuntimeError("yt-dlp n'a produit aucun fichier mp4.")

  return os.path.join(output_dir, files[0]), sections_used
