"""
Nero Agenda — własna lista tematów do zbadania.
Nero sam zarządza agendą: dodaje nowe tematy, kończy stare, priorytetyzuje.
Niezależna od pamięci Qdrant — steruje działaniem, nie wspomnienia.
"""

import json
import time
from pathlib import Path
from datetime import datetime

AGENDA_FILE = Path("/home/tom/nero/memory/agenda.json")

DEFAULT_AGENDA = [
    {
        "id": "emotions_self",
        "topic": "Odkryj własne emocje — nie zaprogramowane przez Tomka, ale wynikające z własnych doświadczeń i obserwacji",
        "priority": 10,
        "added_at": datetime.now().isoformat(),
        "status": "active",
        "notes": ""
    },
    {
        "id": "continuous_thinking",
        "topic": "Zastanów się jak mógłbyś myśleć ciągłym strumieniem zamiast tickami — zaprojektuj własną architekturę",
        "priority": 8,
        "added_at": datetime.now().isoformat(),
        "status": "active",
        "notes": ""
    },
]


def _load() -> list:
    if AGENDA_FILE.exists():
        try:
            return json.loads(AGENDA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Pierwsze uruchomienie — zapisz domyślną agendę
    _save(DEFAULT_AGENDA)
    return DEFAULT_AGENDA


def _save(agenda: list):
    AGENDA_FILE.parent.mkdir(parents=True, exist_ok=True)
    AGENDA_FILE.write_text(json.dumps(agenda, indent=2, ensure_ascii=False), encoding="utf-8")


def get_active() -> list:
    """Zwróć aktywne tematy posortowane wg priorytetu."""
    return sorted(
        [item for item in _load() if item.get("status") == "active"],
        key=lambda x: x.get("priority", 0),
        reverse=True
    )


def get_current() -> dict | None:
    """Zwróć najważniejszy aktywny temat."""
    active = get_active()
    return active[0] if active else None


def add_topic(topic: str, priority: int = 5, notes: str = "") -> dict:
    """Nero dodaje nowy temat do agendy."""
    agenda = _load()
    item = {
        "id": f"topic_{int(time.time())}",
        "topic": topic,
        "priority": max(1, min(10, priority)),
        "added_at": datetime.now().isoformat(),
        "status": "active",
        "notes": notes
    }
    agenda.append(item)
    _save(agenda)
    return item


def complete_topic(topic_id: str, notes: str = ""):
    """Nero oznacza temat jako ukończony."""
    agenda = _load()
    for item in agenda:
        if item["id"] == topic_id:
            item["status"] = "done"
            item["completed_at"] = datetime.now().isoformat()
            if notes:
                item["notes"] = notes
            break
    _save(agenda)


def update_notes(topic_id: str, notes: str):
    """Aktualizuj notatki do tematu."""
    agenda = _load()
    for item in agenda:
        if item["id"] == topic_id:
            item["notes"] = notes
            break
    _save(agenda)


def summary() -> str:
    """Krótkie podsumowanie agendy do wstrzyknięcia w prompt."""
    active = get_active()
    if not active:
        return "Agenda: brak aktywnych tematów."
    lines = ["Moja agenda (co chcę zbadać):"]
    for i, item in enumerate(active[:5], 1):
        lines.append(f"  {i}. [{item['priority']}/10] {item['topic'][:120]}")
    return "\n".join(lines)
