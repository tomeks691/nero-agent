"""
Nero Browser Tool — pełna przeglądarka przez Puppeteer (Node.js + Chromium).
Fallback gdy web_search nie radzi sobie z dynamicznymi/JS stronami.

Różnica od web_search.py:
  web_search — DuckDuckGo snippet, bez JS, max ~400 znaków na wynik
  browser    — pełna strona z JS, scrollowanie, do 4000 znaków treści
"""

import subprocess
import os

BROWSE_SCRIPT = "/home/tom/nero/browser/browse.js"
NODE_BIN = "node"


def browse(url: str, scroll_pages: int = 3, max_chars: int = 3000) -> dict:
    """
    Otwórz URL przez Puppeteer. Działa z JS i dynamicznymi stronami.
    Zwraca: {"found": bool, "content": str, "url": str}
    """
    if not url.startswith("http"):
        url = "https://" + url

    try:
        result = subprocess.run(
            [NODE_BIN, BROWSE_SCRIPT, url, str(scroll_pages)],
            capture_output=True, text=True, timeout=25,
            env={**os.environ, "DISPLAY": ""}
        )
        content = result.stdout.strip()
        if content and not content.startswith("[browser-error]") and len(content) > 50:
            return {"found": True, "content": content[:max_chars], "url": url}
        error = result.stderr.strip() or content
        return {"found": False, "content": f"[browser] {error[:200]}", "url": url}
    except subprocess.TimeoutExpired:
        return {"found": False, "content": "[browser] timeout po 25s", "url": url}
    except Exception as e:
        return {"found": False, "content": f"[browser] {e}", "url": url}
