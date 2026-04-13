import asyncio
import os
import shutil
import tempfile

from ..job_store import register_process, unregister_process, update_job, DOWNLOADING

_COOKIES_FILE = os.getenv("YTDLP_COOKIES_FILE", "/storage/cookies.txt")


async def download(job_id: str, url: str, output_dir: str) -> str:
  """Télécharge une vidéo via yt-dlp (YouTube, Instagram, TikTok, Vimeo...).

  Retourne le chemin du fichier téléchargé.
  Lève une RuntimeError si le téléchargement échoue.
  """
  update_job(job_id, status=DOWNLOADING, message="Téléchargement en cours...")

  output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

  cmd = ["yt-dlp", "--no-playlist",
    "--remote-components", "ejs:github",
    "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
    "--merge-output-format", "mp4",
    "--output", output_template,
  ]

  if os.path.isfile(_COOKIES_FILE):
    tmp_cookies = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    shutil.copy2(_COOKIES_FILE, tmp_cookies.name)
    tmp_cookies.close()
    cmd += ["--cookies", tmp_cookies.name]
  else:
    tmp_cookies = None

  cmd.append(url)

  process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )

  register_process(job_id, process)

  stdout, stderr = await process.communicate()
  unregister_process(job_id)

  if tmp_cookies:
    os.unlink(tmp_cookies.name)

  if process.returncode != 0:
    error = stderr.decode().strip().splitlines()[-1] if stderr else "Erreur inconnue"
    raise RuntimeError(f"yt-dlp a échoué : {error}")

  # Récupère le fichier mp4 téléchargé dans output_dir
  files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
  if not files:
    raise RuntimeError("yt-dlp n'a produit aucun fichier mp4.")

  return os.path.join(output_dir, files[0])
