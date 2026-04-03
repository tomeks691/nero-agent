"""
Nero Skill Improvement — Nero analizuje własne działania i aktualizuje pliki umiejętności.
Inspirowane Claude Code skill improvement hook.

Co 25 ticków analizuje ostatnie wnioski i aktualizuje:
  skills/research.md  — jak lepiej szukać w sieci i arxiv
  skills/coding.md    — jak generować lepszy kod
  skills/shell.md     — jak efektywniej używać shella

Pliki skills/ są czytane przez brain.py przy każdym myśleniu.
"""

import threading
from datetime import datetime
from pathlib import Path

SKILLS_DIR = Path("/home/tom/nero/skills")
SKILL_FILES = {
    "research": SKILLS_DIR / "research.md",
    "coding":   SKILLS_DIR / "coding.md",
    "shell":    SKILLS_DIR / "shell.md",
}

_lock = threading.Lock()

INITIAL_SKILLS = {
    "research": """# Nero — Umiejętności: Badania i Wyszukiwanie

## Co działa dobrze
- Dodawaj rok do zapytań ArXiv (np. "novelty detection 2024") — trafniejsze wyniki
- DuckDuckGo działa lepiej z angielskimi zapytaniami niż polskimi
- Gdy snippet jest krótki (<300 znaków), pobieraj pełną stronę

## Czego unikać
- Nie powtarzaj tego samego zapytania w ciągu 10 ticków
- Unikaj zbyt ogólnych zapytań (np. "machine learning") — bądź precyzyjny
""",
    "coding": """# Nero — Umiejętności: Programowanie

## Co działa dobrze
- Zacznij od prostego, działającego kodu — potem optymalizuj
- Używaj print() do debugowania wyników
- numpy/scipy są dostępne w venv

## Czego unikać
- Nie importuj modułów których nie ma w venv (sprawdź: pip list)
- Nie uruchamiaj kodu który modyfikuje pliki Nero bez pewności
""",
    "shell": """# Nero — Umiejętności: Shell i Serwer

## Co działa dobrze
- `systemctl status nero` — sprawdź własny status
- `free -h` i `nvidia-smi` — sprawdź zasoby
- `tail -20 /home/tom/nero/logs/consciousness.log` — własne logi

## Czego unikać
- Nie używaj sudo (brak uprawnień)
- Nie kasuj plików bez pewności — lepiej sprawdź najpierw co to jest
- Unikaj długich operacji sieciowych bez timeout
""",
}


def _ensure_skills():
    """Stwórz domyślne pliki skills jeśli nie istnieją."""
    SKILLS_DIR.mkdir(exist_ok=True)
    for name, path in SKILL_FILES.items():
        if not path.exists():
            path.write_text(INITIAL_SKILLS[name], encoding="utf-8")


def read_all_skills() -> str:
    """Zwróć zawartość wszystkich plików skills (do wstrzyknięcia w prompt)."""
    _ensure_skills()
    parts = []
    for name, path in SKILL_FILES.items():
        try:
            content = path.read_text(encoding="utf-8").strip()
            if content:
                parts.append(content)
        except Exception:
            pass
    return "\n\n".join(parts) if parts else ""


def _update_skill(brain, skill_name: str, recent_observations: list[str], log_fn) -> bool:
    """Zapytaj Gemmę czy skill wymaga aktualizacji. Zwraca True jeśli zaktualizowano."""
    path = SKILL_FILES[skill_name]
    current = path.read_text(encoding="utf-8").strip()
    obs_str = "\n".join(f"- {o[:150]}" for o in recent_observations[:10])

    prompt = "\n".join([
        f"Jesteś Nero. Analizujesz swoje ostatnie działania w kategorii '{skill_name}'.",
        "Aktualny plik umiejętności:",
        current,
        "",
        "Ostatnie obserwacje i wnioski:",
        obs_str,
        "",
        "Czy plik umiejętności wymaga aktualizacji? Jeśli TAK — napisz TYLKO zaktualizowany plik (cały, po polsku, w formacie Markdown).",
        "Jeśli NIE wymaga zmian — napisz tylko: NIE",
    ])

    result = brain.ask(prompt, max_tokens=600, temp=0.3)
    if not result or result.strip().upper().startswith("NIE"):
        return False

    # Zabezpieczenie — nie zapisuj jeśli wynik jest zbyt krótki
    if len(result.strip()) < 50:
        return False

    path.write_text(result.strip(), encoding="utf-8")
    log_fn(f"[skill] Zaktualizowano: {skill_name}")
    return True


def run_skill_improvement(memory, brain, log_fn=print) -> dict:
    """Uruchom analizę i potencjalną aktualizację skill files."""
    if not _lock.acquire(blocking=False):
        return {"skipped": True}

    stats = {"updated": 0}
    try:
        _ensure_skills()
        log_fn("[skill] Analizuję własne umiejętności...")

        # Zbierz ostatnie obserwacje, wnioski i myśli
        observations = [m["content"] for m in memory.recent(20, memory_type="observation")]
        conclusions  = [m["content"] for m in memory.recent(20, memory_type="conclusion")]
        coding_obs   = [m["content"] for m in memory.search("python kod shell wynik", top_k=10)]

        # Aktualizuj każdy skill plik
        if _update_skill(brain, "research", observations + conclusions, log_fn):
            stats["updated"] += 1
        if _update_skill(brain, "coding", coding_obs, log_fn):
            stats["updated"] += 1
        if _update_skill(brain, "shell", observations, log_fn):
            stats["updated"] += 1

        log_fn(f"[skill] Zakończono | zaktualizowano: {stats['updated']} plików")

    except Exception as e:
        log_fn(f"[skill] BŁĄD: {e}")
    finally:
        _lock.release()

    return stats


def start_skill_improvement_background(memory, brain, log_fn=print):
    """Uruchom w tle — nie blokuje ticku."""
    threading.Thread(
        target=run_skill_improvement,
        args=(memory, brain, log_fn),
        daemon=True
    ).start()
