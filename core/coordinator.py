"""
Nero Coordinator Mode — orkiestruje równoległe zadania badawcze.
Inspirowany COORDINATOR_MODE z Claude Code.

Gdy Nero ma złożony cel badawczy, rozbija go na 3 równoległe workery:
  Worker 1: web — szuka w internecie (DuckDuckGo + pełna strona)
  Worker 2: arxiv — szuka paperów naukowych
  Worker 3: memory — przeszukuje własną pamięć Qdrant

Gemma syntetyzuje wyniki w jeden konkretny wniosek.
Wywoływany gdy curiosity > 0.75 i jest jasny podcel.
"""

import threading
import time


def _worker_web(query: str, results: dict):
    try:
        from lab.web_search import research
        r = research(query)
        if r["found"]:
            results["web"] = r["content"][:800]
            results["web_url"] = r.get("url", "")
    except Exception as e:
        results["web_error"] = str(e)


def _worker_arxiv(query: str, results: dict):
    try:
        from lab.semantic_search import search as arxiv_search, format_for_analysis
        papers = arxiv_search(query, max_results=2)
        if papers:
            results["arxiv"] = format_for_analysis(papers)[:800]
    except Exception as e:
        results["arxiv_error"] = str(e)


def _worker_memory(query: str, memory, results: dict):
    try:
        hits = memory.search(query, top_k=6)
        if hits:
            results["memory"] = "\n".join(
                f"- [{h.get('type','?')}] {h['content'][:150]}" for h in hits
            )
    except Exception as e:
        results["memory_error"] = str(e)


def run_coordinator(goal: str, memory, brain, log_fn=print) -> str | None:
    """
    Orkiestruj równoległe badania na temat celu.
    Zwraca syntetyczny wniosek lub None.
    """
    log_fn(f"[coordinator] 3 workery → {goal[:70]}")

    # Wygeneruj krótkie zapytanie po angielsku (max 5 słów) dla web/arxiv
    query_prompt = (
        f"Convert this research goal to a SHORT English search query (max 5 words, no punctuation):\n{goal}\n\nQuery:"
    )
    search_query = brain.ask(query_prompt, max_tokens=15, temp=0.3)
    if search_query:
        search_query = search_query.strip().strip('"').split("\n")[0][:60]
    else:
        search_query = goal[:60]
    log_fn(f"[coordinator] Query: {search_query}")

    results = {}

    threads = [
        threading.Thread(target=_worker_web,    args=(search_query, results),         daemon=True),
        threading.Thread(target=_worker_arxiv,  args=(search_query, results),         daemon=True),
        threading.Thread(target=_worker_memory, args=(goal, memory, results), daemon=True),
    ]

    for t in threads:
        t.start()

    deadline = time.time() + 90
    for t in threads:
        remaining = max(0.1, deadline - time.time())
        t.join(timeout=remaining)

    sources = [k for k in ("web", "arxiv", "memory") if k in results]
    if not sources:
        log_fn("[coordinator] Brak wyników od workerów")
        return None

    log_fn(f"[coordinator] Zebrano od: {sources}")

    parts = [f"Cel badawczy: {goal}", ""]
    if "web" in results:
        parts += ["## Internet:", results["web"], ""]
    if "arxiv" in results:
        parts += ["## Artykuły naukowe:", results["arxiv"], ""]
    if "memory" in results:
        parts += ["## Z własnej pamięci:", results["memory"], ""]

    parts += [
        "Na podstawie powyższych źródeł napisz JEDEN konkretny wniosek po polsku (2-4 zdania).",
        "Co nowego odkryłeś? Co jest kluczowe dla celu badawczego?",
    ]

    synthesis = brain.ask("\n".join(parts), max_tokens=500, temp=0.7)
    if synthesis:
        log_fn(f"[coordinator] Synteza: {synthesis[:120]}")
    return synthesis
