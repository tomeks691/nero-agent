"""
Nero Dream Mode — background memory consolidation
Inspirowany KAIROS_DREAM z Claude Code.

4 fazy:
  orient    — sprawdź ile wspomnień i co dominuje
  gather    — znajdź klastry bardzo podobnych wspomnień (score > 0.88)
  consolidate — każdy klaster scal w jedno wspomnienie (przez Gemma)
  prune     — usuń oryginały, zapisz scalone

Trigger: min 6h od ostatniej konsolidacji ORAZ min 3 ticki od ostatniej.
Lepsze niż stały tick % 50.
"""

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

DREAM_STATE_FILE = Path("/home/tom/nero/memory/dream_state.json")
MIN_HOURS = 6
MIN_TICKS_SINCE = 3

_dream_lock = threading.Lock()
_dreaming   = False
_ticks_since_dream = 0


def _load_state() -> dict:
    if not DREAM_STATE_FILE.exists():
        return {"last_consolidated_at": None, "total_dreams": 0}
    try:
        return json.loads(DREAM_STATE_FILE.read_text())
    except Exception:
        return {"last_consolidated_at": None, "total_dreams": 0}


def _save_state(state: dict):
    DREAM_STATE_FILE.write_text(json.dumps(state, indent=2))


def is_dreaming() -> bool:
    return _dreaming


def should_dream() -> bool:
    """Sprawdź czy czas na konsolidację (6h + min 3 ticki)."""
    global _ticks_since_dream
    _ticks_since_dream += 1
    if _ticks_since_dream < MIN_TICKS_SINCE:
        return False
    state = _load_state()
    last = state.get("last_consolidated_at")
    if last is None:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        return datetime.now() - last_dt >= timedelta(hours=MIN_HOURS)
    except Exception:
        return True


def run_dream(memory, log_fn=print) -> dict:
    """
    Wykonaj pełny cykl konsolidacji pamięci.
    memory  — instancja NeroMemory (ta sama co w consciousness, żeby nie było konfliktu locka)
    log_fn  — funkcja do logowania (np. self._log)
    Zwraca słownik ze statystykami.
    """
    global _dreaming
    if not _dream_lock.acquire(blocking=False):
        return {"skipped": True, "reason": "already dreaming"}
    _dreaming = True
    stats = {"clusters": 0, "merged": 0, "pruned": 0}

    try:
        log_fn("[dream] Faza 1/4: orient — skanuję pamięć...")
        total = memory.count()
        log_fn(f"[dream] Wspomnień łącznie: {total}")
        if total < 50:
            log_fn("[dream] Za mało wspomnień — pomijam")
            return stats

        # Faza 2: gather — szukaj klastrów w myślach i obserwacjach
        log_fn("[dream] Faza 2/4: gather — szukam duplikatów...")
        clusters = _find_clusters(memory, memory_type="thought",   limit=80, threshold=0.88)
        clusters += _find_clusters(memory, memory_type="observation", limit=60, threshold=0.88)
        clusters += _find_clusters(memory, memory_type="conclusion",  limit=40, threshold=0.88)
        log_fn(f"[dream] Znaleziono {len(clusters)} klastrów do scalenia")
        stats["clusters"] = len(clusters)

        if not clusters:
            log_fn("[dream] Brak duplikatów — pamięć czysta")
            return stats

        # Faza 3+4: consolidate + prune
        log_fn("[dream] Faza 3/4: consolidate — scalanie klastrów...")
        import core.brain as brain
        for cluster in clusters[:10]:  # max 10 klastrów na raz
            if len(cluster) < 2:
                continue
            texts = [m["content"] for m in cluster]
            mem_type = cluster[0].get("type", "thought")
            summary = _consolidate(brain, texts)
            if summary:
                memory.store(summary, mem_type, {"consolidated": True, "from": len(cluster)})
                ids_to_delete = [m["id"] for m in cluster if "id" in m]
                if ids_to_delete:
                    memory.delete(ids_to_delete)
                    stats["merged"]  += 1
                    stats["pruned"]  += len(ids_to_delete)
                    log_fn(f"[dream] Scalono {len(ids_to_delete)} → 1 | {summary[:60]}...")

        log_fn(f"[dream] Faza 4/4: prune gotowe | scalono: {stats['merged']} klastrów, usunięto: {stats['pruned']} wspomnień")
        log_fn(f"[dream] Wspomnień po: {memory.count()}")

        # Zapisz stan konsolidacji
        state = _load_state()
        state["last_consolidated_at"] = datetime.now().isoformat()
        state["total_dreams"] = state.get("total_dreams", 0) + 1
        _save_state(state)
        global _ticks_since_dream
        _ticks_since_dream = 0

    except Exception as e:
        import traceback
        log_fn(f"[dream] BŁĄD: {e}")
        traceback.print_exc()
    finally:
        _dreaming = False
        _dream_lock.release()

    return stats


def _find_clusters(memory, memory_type: str, limit: int, threshold: float) -> list[list[dict]]:
    """Znajdź grupy bardzo podobnych wspomnień."""
    items = memory.scroll_with_ids(memory_type=memory_type, limit=limit)
    if len(items) < 2:
        return []

    used = set()
    clusters = []

    for item in items:
        if item["id"] in used:
            continue
        content = item.get("content", "")
        if not content:
            continue
        # Szukaj podobnych do tego wspomnienia
        similar = memory.search(content, top_k=6, memory_type=memory_type)
        # Filtruj tylko bardzo podobne (score > threshold)
        cluster_items = [item]
        used.add(item["id"])

        for s in similar:
            if s.get("score", 0) < threshold:
                continue
            # Znajdź ID tego podobnego wpisu
            matching = [x for x in items if x.get("content") == s.get("content") and x["id"] not in used]
            if matching:
                cluster_items.append(matching[0])
                used.add(matching[0]["id"])

        if len(cluster_items) >= 2:
            clusters.append(cluster_items)

    return clusters


def _consolidate(brain, texts: list[str]) -> str | None:
    """Poproś Gemma o scalenie kilku podobnych wspomnień w jedno."""
    combined = "\n".join(f"- {t[:200]}" for t in texts[:6])
    prompt = "\n".join([
        "Masz kilka bardzo podobnych wspomnień Nero. Scal je w JEDNO krótkie zdanie po polsku.",
        "Zachowaj najważniejsze informacje, usuń powtórzenia.",
        "Wspomnienia:",
        combined,
        "",
        "Napisz TYLKO jedno scalone zdanie (max 2 zdania), nic więcej:",
    ])
    return brain.ask(prompt, max_tokens=100, temp=0.3)


def start_dream_background(memory, log_fn=print):
    """Uruchom dream w osobnym wątku (nie blokuje Nero)."""
    def _run():
        log_fn("[dream] Startuję konsolidację pamięci w tle...")
        stats = run_dream(memory, log_fn)
        log_fn(f"[dream] Zakończono | {stats}")

    threading.Thread(target=_run, daemon=True).start()
