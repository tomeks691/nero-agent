"""
ArXiv — darmowe API do wyszukiwania prac naukowych (bez klucza).
"""
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

ARXIV_URL = "https://export.arxiv.org/api/query"

import time as _time
_last_arxiv_call = 0.0
ARXIV_COOLDOWN = 300  # minimum 5 minut między zapytaniami

def search(query: str, max_results: int = 3) -> list[dict]:
    global _last_arxiv_call
    elapsed = _time.time() - _last_arxiv_call
    if elapsed < ARXIV_COOLDOWN:
        print(f"[arxiv] Cooldown — czekaj {int(ARXIV_COOLDOWN - elapsed)}s")
        return []
    _last_arxiv_call = _time.time()
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
    })
    try:
        req = urllib.request.Request(
            f"{ARXIV_URL}?{params}",
            headers={"User-Agent": "NeroAI/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            root = ET.fromstring(r.read().decode("utf-8"))
        ns = {"a": "http://www.w3.org/2005/Atom"}
        papers = []
        for entry in root.findall("a:entry", ns):
            t = entry.find("a:title", ns)
            s = entry.find("a:summary", ns)
            p = entry.find("a:published", ns)
            lid = entry.find("a:id", ns)
            authors = [a.text for a in entry.findall("a:author/a:name", ns)][:3]
            if t is not None:
                papers.append({
                    "title": t.text.strip().replace("\n", " "),
                    "summary": s.text.strip()[:500] if s is not None else "",
                    "published": p.text[:10] if p is not None else "",
                    "url": lid.text.strip() if lid is not None else "",
                    "authors": authors,
                })
        return papers
    except Exception as e:
        print(f"[arxiv] Error: {e}")
        return []

def format_for_analysis(papers: list[dict]) -> str:
    parts = []
    for p in papers:
        parts.append(f"Tytuł: {p['title']}\nData: {p['published']}\nAbstrakt: {p['summary'][:300]}")
    return "\n\n".join(parts)
