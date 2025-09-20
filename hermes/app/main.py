import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import artists, albums, titles, meta

app = FastAPI(title="Hermes API", version="0.1.0")

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
app.include_router(artists.router, prefix="/artists", tags=["artists"])
app.include_router(albums.router,  prefix="/albums",  tags=["albums"])
app.include_router(titles.router,  prefix="/titles",  tags=["titles"])
app.include_router(meta.router,    prefix="/meta",    tags=["meta"])
