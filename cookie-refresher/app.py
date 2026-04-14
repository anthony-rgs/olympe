import asyncio
import http.cookiejar
import os
from pathlib import Path

from fastapi import FastAPI

app = FastAPI()

COOKIES_FILE = os.getenv("YTDLP_COOKIES_FILE", "/storage/cookies.txt")


def _netscape_to_playwright(cookies_file: str) -> list[dict]:
  """Convertit les cookies Netscape → format Playwright."""
  jar = http.cookiejar.MozillaCookieJar(cookies_file)
  try:
    jar.load(ignore_discard=True, ignore_expires=True)
  except Exception:
    return []

  result = []
  for c in jar:
    result.append({
      "name": c.name,
      "value": c.value,
      "domain": c.domain,
      "path": c.path,
      "expires": c.expires if c.expires else -1,
      "httpOnly": bool(c.has_nonstandard_attr("HttpOnly")),
      "secure": bool(c.secure),
      "sameSite": "None",
    })
  return result


def _playwright_to_netscape(cookies: list[dict], cookies_file: str):
  """Convertit les cookies Playwright → format Netscape."""
  lines = ["# Netscape HTTP Cookie File\n"]
  for c in cookies:
    domain = c.get("domain", "")
    subdomains = "TRUE" if domain.startswith(".") else "FALSE"
    path = c.get("path", "/")
    secure = "TRUE" if c.get("secure") else "FALSE"
    expires = int(c.get("expires", 0)) if c.get("expires", -1) != -1 else 0
    lines.append(f"{domain}\t{subdomains}\t{path}\t{secure}\t{expires}\t{c['name']}\t{c['value']}\n")
  Path(cookies_file).write_text("".join(lines))


@app.post("/refresh")
async def refresh():
  from playwright.async_api import async_playwright

  async with async_playwright() as p:
    browser = await p.chromium.launch(
      headless=True,
      args=["--no-sandbox", "--disable-setuid-sandbox"],
    )
    context = await browser.new_context(
      user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    )

    if os.path.isfile(COOKIES_FILE):
      existing = _netscape_to_playwright(COOKIES_FILE)
      if existing:
        await context.add_cookies(existing)

    page = await context.new_page()
    await page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)

    cookies = await context.cookies()
    _playwright_to_netscape(cookies, COOKIES_FILE)
    await browser.close()

  print(f"[cookie-refresher] {len(cookies)} cookies sauvegardés")
  return {"status": "ok", "cookies_count": len(cookies)}


@app.get("/health")
def health():
  return {"status": "ok"}
