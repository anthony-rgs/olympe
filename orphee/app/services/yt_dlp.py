import asyncio
import os

from ..job_store import register_process, unregister_process, update_job, DOWNLOADING

_BGUTIL_URL = os.getenv("BGUTIL_SERVER_URL", "http://bgutil:4416")


async def download(job_id: str, url: str, output_dir: str) -> str:
  """Télécharge une vidéo via yt-dlp (YouTube, Instagram, TikTok, Vimeo...).

  Retourne le chemin du fichier téléchargé.
  Lève une RuntimeError si le téléchargement échoue.
  """
  update_job(job_id, status=DOWNLOADING, message="Téléchargement en cours...")

  output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

  cmd = [
    "yt-dlp",
    "--no-playlist",
    "--remote-components", "ejs:github",
    "--username", "oauth2",
    "--password", "",
    "--extractor-args", f"youtubepot-bgutilhttp:base_url={_BGUTIL_URL}",
    "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
    "--merge-output-format", "mp4",
    "--output", output_template,
    url,
  ]

  process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )

  register_process(job_id, process)

  stdout, stderr = await process.communicate()
  unregister_process(job_id)

  if process.returncode != 0:
    error = stderr.decode().strip().splitlines()[-1] if stderr else "Erreur inconnue"
    raise RuntimeError(f"yt-dlp a échoué : {error}")

  files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
  if not files:
    raise RuntimeError("yt-dlp n'a produit aucun fichier mp4.")

  return os.path.join(output_dir, files[0])
