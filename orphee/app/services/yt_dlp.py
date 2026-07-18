import asyncio
import os

from ..job_store import register_process, unregister_process, update_job, DOWNLOADING

_FORMAT = (
  "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]"
  "/bestvideo[height<=720]+bestaudio"
  "/best[height<=720][ext=mp4]"
  "/best[height<=720]"
)


def _parse_seconds(time_str: str) -> float:
  parts = [float(p) for p in time_str.strip().split(":")]
  if len(parts) == 3:
    return parts[0] * 3600 + parts[1] * 60 + parts[2]
  if len(parts) == 2:
    return parts[0] * 60 + parts[1]
  return parts[0]


def _fmt_time(seconds: float) -> str:
  h = int(seconds // 3600)
  m = int((seconds % 3600) // 60)
  s = seconds % 60
  return f"{h:02d}:{m:02d}:{s:06.3f}"


async def _run_ytdlp(cmd: list[str], job_id: str) -> tuple[int, bytes, bytes]:
  process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )
  register_process(job_id, process)
  stdout, stderr = await process.communicate()
  unregister_process(job_id)
  return process.returncode, stdout, stderr


async def download(job_id: str, url: str, output_dir: str,
                   start_time: str | None = None,
                   duration: int | None = None) -> tuple[str, bool]:
  """Télécharge une vidéo via yt-dlp (YouTube, Instagram, TikTok, Vimeo...)."""
  update_job(job_id, status=DOWNLOADING, message="Téléchargement en cours...")

  output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
  info_path = os.path.join(output_dir, "info.json")
  proxy = os.getenv("YTDLP_PROXY", "")

  # Étape 1 : extraction des URLs via proxy (contourne le blocage bot YouTube)
  extract_cmd = ["yt-dlp", "-J", "--no-playlist"]
  if proxy:
    extract_cmd += ["--proxy", proxy]
  extract_cmd.append(url)

  returncode, stdout, stderr = await _run_ytdlp(extract_cmd, job_id)
  if returncode != 0:
    error = stderr.decode().strip().splitlines()[-1] if stderr else "Erreur inconnue"
    raise RuntimeError(f"yt-dlp a échoué : {error}")

  with open(info_path, "w") as f:
    f.write(stdout.decode())

  # Étape 2 : téléchargement direct depuis le CDN YouTube (sans proxy, débit VPS)
  base_cmd = [
    "yt-dlp",
    "--load-info-json", info_path,
    "--no-playlist",
    "--format", _FORMAT,
    "--merge-output-format", "mp4",
    "--retries", "5",
    "--fragment-retries", "5",
    "--output", output_template,
  ]

  sections_args = []
  if start_time is not None and duration is not None:
    start_s = _parse_seconds(start_time)
    end_s = start_s + duration + 2
    sections_args = ["--download-sections", f"*{_fmt_time(start_s)}-{_fmt_time(end_s)}"]

  def _clear_dir():
    for f in os.listdir(output_dir):
      if f != "info.json":
        os.remove(os.path.join(output_dir, f))

  sections_used = False
  returncode, _, stderr = await _run_ytdlp(base_cmd + sections_args, job_id)

  if returncode == 0 and sections_args:
    sections_used = True
  elif returncode != 0 and sections_args:
    print("[yt-dlp] --download-sections a échoué, retry sans sections")
    _clear_dir()
    returncode, _, stderr = await _run_ytdlp(base_cmd, job_id)

  if os.path.exists(info_path):
    os.remove(info_path)

  if returncode != 0:
    error = stderr.decode().strip().splitlines()[-1] if stderr else "Erreur inconnue"
    raise RuntimeError(f"yt-dlp a échoué : {error}")

  files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
  if not files:
    raise RuntimeError("yt-dlp n'a produit aucun fichier mp4.")

  return os.path.join(output_dir, files[0]), sections_used
