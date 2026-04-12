import anthropic

from ..config import ANTHROPIC_API_KEY
from ..job_store import update_job

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def pick_best_timestamp(job_id: str, context: str, duration: int) -> str:
  """Demande à Claude de choisir le meilleur timestamp pour un extrait musical.

  context : texte libre décrivant la chanson (ex: "bohemian rhapsody queen")
  Retourne un timestamp au format HH:MM:SS.
  Lève une RuntimeError si l'appel échoue ou si le quota est dépassé.
  """
  update_job(job_id, message="Claude analyse la chanson pour choisir le meilleur passage...")

  prompt = f"""Tu es un expert en création de clips musicaux courts pour les réseaux sociaux (TikTok, Instagram Reels, YouTube Shorts).

Ta mission : choisir le meilleur timestamp de départ pour un extrait de {duration} secondes.

Contexte : {context}

Critères de sélection (par ordre de priorité) :
1. Le passage le plus reconnaissable et accrocheur (refrain, hook, drop)
2. Un moment avec une forte énergie ou émotion
3. Un passage qui donne envie d'écouter la chanson en entier

Réponds UNIQUEMENT avec le timestamp de départ au format HH:MM:SS, sans aucun autre texte.
Exemple : 00:01:23"""

  try:
    response = _client.messages.create(
      model="claude-opus-4-6",
      max_tokens=32,
      messages=[{"role": "user", "content": prompt}],
    )
  except anthropic.AuthenticationError:
    raise RuntimeError(
      "Clé API Anthropic invalide. Vérifie la variable ANTHROPIC_API_KEY."
    )
  except anthropic.PermissionDeniedError:
    raise RuntimeError(
      "Accès refusé à l'API Anthropic. Vérifie les permissions de ta clé API."
    )
  except anthropic.RateLimitError:
    raise RuntimeError(
      "Quota Anthropic dépassé ou limite de taux atteinte. Réessaie plus tard."
    )
  except anthropic.APIStatusError as e:
    if e.status_code >= 500:
      raise RuntimeError(
        f"Erreur serveur Anthropic ({e.status_code}). Réessaie dans quelques instants."
      )
    raise RuntimeError(f"Erreur API Anthropic : {e.message}")

  raw = next(
    (b.text.strip() for b in response.content if b.type == "text"), ""
  )

  if not _is_valid_timestamp(raw):
    raise RuntimeError(
      f"Claude a retourné un timestamp invalide : '{raw}'. "
      "Passe un start_time manuellement dans ta requête."
    )

  return raw


def _is_valid_timestamp(value: str) -> bool:
  """Valide le format HH:MM:SS retourné par Claude."""
  parts = value.split(":")
  if len(parts) != 3:
    return False
  try:
    h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
    return 0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60
  except ValueError:
    return False
