import asyncio
import json
import os
import re
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from ..job_store import (
  CANCELLED, DONE, FAILED,
  _jobs,
  cancel_job, create_job, final_path, get_active_job, get_job, purge_job, update_job,
)
from ..services import ffmpeg

router = APIRouter()


# ── Schémas ──────────────────────────────────────────────────────────────────

class TitleStyle(BaseModel):
  border: Optional[int] = None
  color: Optional[str] = None
  font: Optional[str] = None
  size: Optional[int] = None
  opacity: Optional[float] = None


class SubtitleStyle(BaseModel):
  border: Optional[int] = None
  color: Optional[str] = None
  font: Optional[str] = None
  size: Optional[int] = None
  opacity: Optional[float] = None


class ClipTitleStyle(BaseModel):
  animation: str = "fade"        # "fade" | "none" | "slide-left" | "slide-bottom" | "typewriter"
  border: Optional[int] = None
  color: Optional[str] = None
  font: Optional[str] = None
  position: str = "left"         # "left" | "center"
  size: Optional[int] = None
  opacity: Optional[float] = None


class VideoTitle(BaseModel):
  first: str
  second: Optional[str] = None
  titleStyle: Optional[TitleStyle] = None
  subtitle: Optional[str] = None
  subtitleStyle: Optional[SubtitleStyle] = None


class ClipIdStyle(BaseModel):
  border: Optional[int] = None
  color: Optional[str] = None
  font: Optional[str] = None
  size: Optional[int] = None
  opacity: Optional[float] = None


class ClipItem(BaseModel):
  id: str                        # string — chiffre, lettre, emoji...
  idStyle: Optional[ClipIdStyle] = None
  url: str
  title: str
  subtitle: Optional[str] = None
  subtitleStyle: Optional[ClipTitleStyle] = None
  duration: int
  claude: bool = False
  start_time: Optional[str] = None   # obligatoire si claude=false
  titleStyle: Optional[ClipTitleStyle] = None


class HighlightActive(BaseModel):
  active: bool = False
  inactiveColor: str = "0x888888"


class RenderRequest(BaseModel):
  title: VideoTitle
  template: str = "top"              # "top" | "classic" | "minimal" | "expanded"
  highlightActive: Optional[HighlightActive] = None
  teaserTop: bool = False
  smoothTransition: Optional[dict] = None  # {"active": bool, "duration": float}
  background: str = "video"               # "video" | "0xRRGGBB"
  watermark: Optional[dict] = None        # {"active": bool, "text": str, "color": str, "font": str, "size": int}
  spacing: Optional[int] = None           # gap (px) entre title/subtitle et la vidéo (classic/minimal/expanded)
  videoMargin: Optional[int] = None       # marge (px) à gauche et droite de la vidéo (top, classic, minimal)
  data: list[ClipItem]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/render", status_code=201)
async def create_render_job(body: RenderRequest, background_tasks: BackgroundTasks):
  """Crée un job de rendu multi-clips (pipeline 9:16)."""
  if not body.data:
    raise HTTPException(status_code=400, detail="Le tableau data est vide.")

  if body.template not in ("top", "classic", "minimal", "expanded"):
    raise HTTPException(
      status_code=400,
      detail=f"template invalide : '{body.template}'. Valeurs : top, classic, minimal, expanded.",
    )

  for item in body.data:
    has_start = bool(item.start_time and item.start_time.strip())
    if not has_start and not item.claude:
      raise HTTPException(
        status_code=400,
        detail=f"Clip id={item.id} doit avoir soit un start_time, soit claude=true.",
      )

  active = get_active_job()
  if active:
    raise HTTPException(
      status_code=409,
      detail={
        "message": "Un job est déjà en cours, impossible d'en lancer un nouveau.",
        "job_id": active["job_id"],
        "status": active["status"],
      },
    )

  def _slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    return re.sub(r"[\s]+", "-", s)

  parts = [body.title.first]
  if body.title.second:
    parts.append(body.title.second)
  slug = _slugify(" ".join(parts))

  job = create_job(title=slug)
  payload = body.model_dump()
  background_tasks.add_task(_run_render_pipeline, job["job_id"], payload)
  return {
    "job_id":     job["job_id"],
    "status":     job["status"],
    "title":      job["title"],
    "created_at": job["created_at"],
    "error":      job["error"],
  }



@router.get("/last")
def get_last_job():
  """Retourne le dernier job (actif ou terminé), ou 404 si aucun."""
  job = next(
    (j for j in sorted(_jobs.values(), key=lambda j: j["created_at"], reverse=True)),
    None,
  )
  if not job:
    raise HTTPException(status_code=404, detail="Aucun job trouvé.")
  return {
    "job_id":     job["job_id"],
    "title":      job["title"],
    "created_at": job["created_at"],
    "updated_at": job["updated_at"],
  }


@router.get("/{job_id}/stream")
async def stream_job(job_id: str):
  """SSE — suit l'avancement d'un job en temps réel jusqu'à sa fin."""
  job = get_job(job_id)
  if not job:
    raise HTTPException(status_code=404, detail="Job introuvable.")

  return StreamingResponse(
    _sse_generator(job_id),
    media_type="text/event-stream",
    headers={
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",  # désactive le buffering Caddy/Nginx
    },
  )


@router.get("/{job_id}/download")
def download_job(job_id: str):
  """Télécharge le final.mp4 d'un job terminé."""
  job = get_job(job_id)
  if not job:
    raise HTTPException(status_code=404, detail="Job introuvable.")
  if job["status"] != DONE:
    raise HTTPException(
      status_code=409,
      detail=f"La vidéo n'est pas encore prête (statut : {job['status']}).",
    )
  path = final_path(job_id)
  if not os.path.exists(path):
    raise HTTPException(status_code=404, detail="Fichier final.mp4 introuvable sur le disque.")

  filename = f"{job['title']}_{job_id[:8]}.mp4"
  return FileResponse(path, media_type="video/mp4", filename=filename)


@router.delete("/{job_id}")
def delete_job(job_id: str):
  """Annule un job en cours d'exécution."""
  job = get_job(job_id)
  if not job:
    raise HTTPException(status_code=404, detail="Job introuvable.")
  if job["status"] in (DONE, FAILED, CANCELLED):
    raise HTTPException(
      status_code=409,
      detail=f"Impossible d'annuler un job déjà terminé (statut : {job['status']}).",
    )
  cancel_job(job_id)
  purge_job(job_id)
  return {"detail": "Job annulé."}


# ── Pipeline ──────────────────────────────────────────────────────────────────

async def _run_render_pipeline(job_id: str, payload: dict) -> None:
  """Orchestre le pipeline multi-clips : téléchargement → découpe → concat → rendu final."""
  try:
    await ffmpeg.render_video(job_id, payload)
    update_job(job_id, status=DONE, message="Vidéo prête !")
  except asyncio.CancelledError:
    pass
  except Exception as e:
    update_job(job_id, status=FAILED, error=str(e), message=f"Erreur : {e}")


# ── Générateur SSE ────────────────────────────────────────────────────────────

async def _sse_generator(job_id: str) -> AsyncGenerator[str, None]:
  """Envoie l'état du job toutes les 500 ms jusqu'à sa fin."""
  terminal = {DONE, FAILED, CANCELLED}

  while True:
    job = get_job(job_id)
    if not job:
      yield _sse_event({"error": "Job introuvable."})
      break

    yield _sse_event(_job_view(job))

    if job["status"] in terminal:
      break

    await asyncio.sleep(0.5)


def _job_view(job: dict) -> dict:
  view = {
    "job_id":     job["job_id"],
    "status":     job["status"],
    "title":      job["title"],
    "created_at": job["created_at"],
    "updated_at": job["updated_at"],
    "error":      job["error"],
  }
  if job.get("clips") is not None:
    view["clips"] = job["clips"]
  if job.get("message") is not None:
    view["message"] = job["message"]
  return view


def _sse_event(data: dict) -> str:
  return f"data: {json.dumps(data)}\n\n"
