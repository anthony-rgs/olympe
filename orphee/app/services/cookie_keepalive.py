import asyncio
import http.cookiejar
import os
import urllib.request


_COOKIES_FILE = os.getenv("YTDLP_COOKIES_FILE", "/storage/cookies.txt")
_INTERVAL = int(os.getenv("COOKIE_KEEPALIVE_INTERVAL", "600"))  # 10 min par défaut
_KEEPALIVE_URL = "https://www.youtube.com"


def _ping_youtube() -> bool:
  """Envoie une requête légère à YouTube avec les cookies pour garder la session active."""
  if not os.path.isfile(_COOKIES_FILE):
    print("[keepalive] Pas de fichier cookies, ping ignoré.")
    return False

  try:
    jar = http.cookiejar.MozillaCookieJar(_COOKIES_FILE)
    jar.load(ignore_discard=True, ignore_expires=True)

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [
      ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
      ("Accept-Language", "en-US,en;q=0.9"),
    ]

    req = urllib.request.Request(_KEEPALIVE_URL, method="HEAD")
    with opener.open(req, timeout=10) as resp:
      jar.save(ignore_discard=True, ignore_expires=True)
      print(f"[keepalive] YouTube ping OK (status {resp.status}), cookies sauvegardés")
      return True

  except Exception as e:
    print(f"[keepalive] YouTube ping échoué : {e}")
    return False


async def run_keepalive():
  """Boucle infinie : ping YouTube toutes les _INTERVAL secondes."""
  print(f"[keepalive] Démarrage (intervalle : {_INTERVAL}s)")
  # Ping immédiat au démarrage pour valider les cookies
  await asyncio.get_event_loop().run_in_executor(None, _ping_youtube)
  while True:
    await asyncio.sleep(_INTERVAL)
    await asyncio.get_event_loop().run_in_executor(None, _ping_youtube)
