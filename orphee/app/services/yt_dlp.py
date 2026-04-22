import asyncio
import os
import shutil
import tempfile
from typing import Optional

from ..job_store import register_process, unregister_process, update_job, DOWNLOADING

_COOKIES_FILE = os.getenv("YTDLP_COOKIES_FILE", "/storage/cookies.txt")


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
                   start_time: Optional[str] = None, duration: Optional[int] = None) -> str:
  """Télécharge une vidéo via yt-dlp (YouTube, Instagram, TikTok, Vimeo...).

  Retourne le chemin du fichier téléchargé.
  Lève une RuntimeError si le téléchargement échoue.
  """
  update_job(job_id, status=DOWNLOADING, message="Téléchargement en cours...")

  output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

  base_cmd = [
    "yt-dlp",
    "--no-playlist",
    "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
    "--merge-output-format", "mp4",
    "--remote-components", "ejs:github",
    "--output", output_template,
  ]

  sections_args = []
  if start_time is not None and duration is not None:
    start_s = _parse_seconds(start_time)
    end_s = start_s + duration + 2  # +2s de buffer pour les keyframes
    sections_args = ["--download-sections", f"*{_fmt_time(start_s)}-{_fmt_time(end_s)}"]

  def _cookies_args() -> tuple[list[str], Optional[str]]:
    if os.path.isfile(_COOKIES_FILE):
      tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
      shutil.copy2(_COOKIES_FILE, tmp.name)
      tmp.close()
      return ["--cookies", tmp.name], tmp.name
    return [], None

  cookies_args, tmp_path = _cookies_args()

  # Tente d'abord avec --download-sections, fallback sans si format indisponible
  cmd = base_cmd + sections_args + cookies_args + [url]
  returncode, stderr = await _run_ytdlp(cmd, job_id)

  if returncode != 0 and sections_args:
    error_msg = stderr.decode()
    if "requested format is not available" in error_msg or "format" in error_msg.lower():
      print(f"[yt-dlp] --download-sections incompatible, retry sans sections")
      # Vide le dossier pour éviter des fichiers partiels
      for f in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, f))
      cookies_args2, tmp_path2 = _cookies_args()
      cmd2 = base_cmd + cookies_args2 + [url]
      returncode, stderr = await _run_ytdlp(cmd2, job_id)
      if tmp_path2:
        os.unlink(tmp_path2)

  if tmp_path and os.path.exists(tmp_path):
    os.unlink(tmp_path)

  if returncode != 0:
    error = stderr.decode().strip().splitlines()[-1] if stderr else "Erreur inconnue"
    raise RuntimeError(f"yt-dlp a échoué : {error}")

  files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
  if not files:
    raise RuntimeError("yt-dlp n'a produit aucun fichier mp4.")

  return os.path.join(output_dir, files[0])
