"""
Nero Web — szukanie i czytanie internetu przez DuckDuckGo HTML
"""

import urllib.request
import urllib.parse
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0"
}


def search(query: str, max_results: int = 3) -> list[dict]:
    """Szukaj w DuckDuckGo, zwróć listę {title, url, snippet}"""
    try:
        params = urllib.parse.urlencode({"q": query, "kl": "pl-pl"})
        req = urllib.request.Request(
            f"https://html.duckduckgo.com/html/?{params}",
            headers=HEADERS
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        results = []
        # Wyciągnij wyniki z HTML
        blocks = re.findall(
            r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>.*?<a[^>]+class="result__snippet"[^>]*>([^<]*(?:<[^>]+>[^<]*)*)</a>',
            html, re.DOTALL
        )
        for url, title, snippet in blocks[:max_results]:
            snippet_clean = re.sub(r"<[^>]+>", "", snippet).strip()
            results.append({
                "title": title.strip(),
                "url": url.strip(),
                "snippet": snippet_clean[:400]
            })

        if not results:
            # Fallback — wyciągnij cokolwiek
            titles = re.findall(r'class="result__a"[^>]*>([^<]+)<', html)
            urls = re.findall(r'result__url[^>]*>([^<]+)<', html)
            for t, u in zip(titles[:max_results], urls[:max_results]):
                results.append({"title": t.strip(), "url": u.strip(), "snippet": ""})

        return results
    except Exception as e:
        print(f"[web] Błąd wyszukiwania: {e}")
        return []


def fetch_page(url: str, max_chars: int = 2000) -> str | None:
    """Pobierz tekst ze strony"""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        # Usuń skrypty i style
        html = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", " ", html, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        print(f"[web] Błąd pobierania: {e}")
        return None


def research(query: str) -> dict:
    """Nero szuka i zbiera wiedzę na temat"""
    print(f"[web] Szukam: '{query}'")
    results = search(query, max_results=3)

    if not results:
        return {"query": query, "found": False, "content": "", "title": "", "url": ""}

    best = results[0]
    content = best["snippet"]

    if best.get("url") and len(content) < 300:
        page = fetch_page(best["url"], max_chars=1500)
        if page:
            content = page

    print(f"[web] {len(results)} wyników | {len(content)} znaków | {best['title'][:50]}")
    return {
        "query": query,
        "found": True,
        "title": best["title"],
        "url": best["url"],
        "content": content
    }


if __name__ == "__main__":
    result = research("artificial general intelligence")
    print(f"Tytuł: {result['title']}")
    print(f"Treść: {result['content'][:300]}")
