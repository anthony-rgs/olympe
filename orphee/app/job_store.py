import asyncio
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Optional

from .config import STORAGE_ROOT

# Statuts possibles d'un job Orphée
PENDING     = "pending"
DOWNLOADING = "downloading"
PROCESSING  = "processing"
DONE        = "done"
FAILED      = "failed"
CANCELLED   = "cancelled"

# Stockage en mémoire : job_id -> dict du job
_jobs: dict[str, dict] = {}

# Processus actifs : job_id -> asyncio.subprocess.Process
_processes: dict[str, asyncio.subprocess.Process] = {}


def _job_dir(job_id: str) -> str:
  return os.path.join(STORAGE_ROOT, job_id)

def _job_file(job_id: str) -> str:
  return os.path.join(_job_dir(job_id), "job.json")


def purge_all_jobs() -> None:
  """Vide entièrement STORAGE_ROOT (jobs uniquement) et le store en mémoire."""
  try:
    for entry in os.scandir(STORAGE_ROOT):
      if entry.is_dir():
        shutil.rmtree(entry.path, ignore_errors=True)
      else:
        os.remove(entry.path)
  except FileNotFoundError:
    pass
  _jobs.clear()


def purge_job(job_id: str) -> None:
  """Supprime le répertoire d'un job sur disque et le retire du store en mémoire."""
  try:
    shutil.rmtree(_job_dir(job_id), ignore_errors=True)
  except Exception:
    pass
  _jobs.pop(job_id, None)


def create_job(title: Optional[str]) -> dict:
  """Crée un nouveau job Orphée et initialise son répertoire sur disque."""
  purge_all_jobs()
  job_id = str(uuid.uuid4())
  job = {
    "job_id":     job_id,
    "status":     PENDING,
    "title":      title,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "error":      None,
  }

  # Création des sous-répertoires de stockage
  for sub in ("raw", "clips"):
    os.makedirs(os.path.join(_job_dir(job_id), sub), exist_ok=True)

  _jobs[job_id] = job
  _persist(job)
  return job


def get_active_job() -> Optional[dict]:
  """Retourne le job actif (pending/downloading/processing) s'il en existe un."""
  active = {PENDING, DOWNLOADING, PROCESSING}
  return next((j for j in _jobs.values() if j["status"] in active), None)


def get_job(job_id: str) -> Optional[dict]:
  return _jobs.get(job_id)


def update_job(job_id: str, **kwargs) -> Optional[dict]:
  """Met à jour les champs d'un job et persiste sur disque."""
  job = _jobs.get(job_id)
  if not job:
    return None
  kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
  job.update(kwargs)
  _persist(job)
  return job


def register_process(job_id: str, process: asyncio.subprocess.Process) -> None:
  _processes[job_id] = process

def unregister_process(job_id: str) -> None:
  _processes.pop(job_id, None)

def get_process(job_id: str) -> Optional[asyncio.subprocess.Process]:
  return _processes.get(job_id)


def cancel_job(job_id: str) -> bool:
  """Annule un job en cours : tue le process actif et met à jour le statut."""
  job = _jobs.get(job_id)
  if not job or job["status"] in (DONE, FAILED, CANCELLED):
    return False

  process = _processes.get(job_id)
  if process:
    try:
      process.terminate()
    except ProcessLookupError:
      pass
    unregister_process(job_id)

  update_job(job_id, status=CANCELLED)
  return True


def final_path(job_id: str) -> str:
  """Chemin vers le fichier final.mp4 d'un job."""
  return os.path.join(_job_dir(job_id), "final.mp4")


def _persist(job: dict) -> None:
  """Écrit l'état du job dans job.json pour survivre aux redémarrages."""
  try:
    with open(_job_file(job["job_id"]), "w") as f:
      json.dump(job, f, indent=2)
  except OSError:
    pass
