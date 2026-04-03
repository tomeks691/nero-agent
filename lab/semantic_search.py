"""
Semantic Search — OpenAlex API jako zamiennik arxiv.
Darmowe, bez klucza, wysoki limit zapytań.
"""
import urllib.request
import urllib.parse
import json
import time

OPENALEX_URL = "https://api.openalex.org/works"
_last_call = 0.0
COOLDOWN = 60  # 1 minuta między zapytaniami

def search(query: str, max_results: int = 3) -> list[dict]:
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < COOLDOWN:
        print(f"[semantic] Cooldown — czekaj {int(COOLDOWN - elapsed)}s")
        return []
    _last_call = time.time()

    params = urllib.parse.urlencode({
        "search": query,
        "per-page": max_results,
        "select": "title,abstract_inverted_index,publication_year,doi",
        "sort": "relevance_score:desc",
    })
    try:
        req = urllib.request.Request(
            f"{OPENALEX_URL}?{params}",
            headers={"User-Agent": "NeroAI/1.0 (mailto:nero@localhost)"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        results = []
        for work in data.get("results", []):
            title = work.get("title", "")
            year = work.get("publication_year", "")
            doi = work.get("doi", "")
            # Odtwórz abstract z inverted index
            inv = work.get("abstract_inverted_index") or {}
            if inv:
                words = {}
                for word, positions in inv.items():
                    for pos in positions:
                        words[pos] = word
                abstract = " ".join(words[i] for i in sorted(words))[:500]
            else:
                abstract = ""
            results.append({
                "title": title,
                "abstract": abstract,
                "year": str(year),
                "url": doi or "",
            })
        print(f"[semantic] {len(results)} wyników dla: {query[:50]}")
        return results
    except Exception as e:
        print(f"[semantic] Error: {e}")
        return []


def format_for_analysis(papers: list[dict]) -> str:
    parts = []
    for p in papers:
        parts.append(f"**{p['title']}** ({p['year']})")
        if p["abstract"]:
            parts.append(p["abstract"][:300])
        parts.append("")
    return "\n".join(parts)
