import os

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
  raise RuntimeError("ANTHROPIC_API_KEY is not set. Provide it via docker-compose/.env")

# Répertoire racine où Orphée stocke les jobs
STORAGE_ROOT = os.getenv("STORAGE_ROOT", "/storage/jobs")

# Clé secrète pour signer les JWT — doit être longue et aléatoire
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
  raise RuntimeError("JWT_SECRET is not set. Provide it via docker-compose/.env")

# Durée de validité d'un token JWT (en heures)
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "72"))

# Chemin vers le fichier des utilisateurs
USERS_FILE = os.getenv("USERS_FILE", "/storage/users.json")