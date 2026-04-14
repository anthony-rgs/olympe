import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_auth
from .routers import auth, video
from .services.cookie_keepalive import run_keepalive


@asynccontextmanager
async def lifespan(app: FastAPI):
  task = asyncio.create_task(run_keepalive())
  yield
  task.cancel()


# Orphée — API de génération automatique de vidéos musicales
app = FastAPI(title="Orphée API", version="0.1.0", lifespan=lifespan)

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if origins:
  app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )

@app.get("/health")
def health():
  return {"status": "ok"}

# Routers
app.include_router(auth.router,  prefix="/auth",  tags=["auth"])
app.include_router(video.router, prefix="/jobs",  tags=["jobs"], dependencies=[Depends(require_auth)])
