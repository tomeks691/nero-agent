"""
Nero Extract Memories — automatyczna ekstrakcja faktów z tekstu.
Inspirowana EXTRACT_MEMORIES z Claude Code.

Zamiast ręcznego memory.store() — deepseek automatycznie wyciąga
kluczowe fakty z każdego znaleziska i zapisuje je jako osobne wspomnienia.

Używa ask_coder (deepseek-coder) bo jest szybszy niż Gemma dla ekstrakcji.
"""


def extract_and_store(text: str, source: str, memory, brain, log_fn=None) -> list[str]:
    """
    Wyciągnij kluczowe fakty z tekstu i zapisz do pamięci.
    Zwraca listę zapisanych faktów (może być pusta).
    """
    if not text or len(text.strip()) < 150:
        return []

    prompt = "\n".join([
        "Przeczytaj poniższy tekst naukowy/informacyjny.",
        "Wyciągnij z niego 3-5 konkretnych, nowych faktów.",
        "Każdy fakt = jedno zdanie po polsku. Tylko fakty, bez komentarzy.",
        "Pisz po jednym fakcie na linię.",
        "",
        f"Źródło: {source}",
        "Tekst:",
        text[:2000],
        "",
        "Fakty (jeden per linia):",
    ])

    result = brain.ask_coder(prompt, max_tokens=400)
    if not result:
        return []

    lines = [l.strip() for l in result.strip().split("\n") if l.strip()]
    # Filtruj: usuń meta-komentarze, zbyt krótkie linie, linie z ":" na początku
    facts = [
        l for l in lines
        if len(l) > 30
        and not l.lower().startswith(("fakt", "źródło", "tekst", "oto", "poniżej", "•", "-"))
        and not l.endswith(":")
    ][:5]

    stored = []
    for fact in facts:
        memory.store(fact, "knowledge", {"source": source, "extracted": True})
        stored.append(fact)

    if stored and log_fn:
        log_fn(f"[extract] Zapisano {len(stored)} faktów z: {source[:50]}")

    return stored
