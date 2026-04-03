"""
Nero Tasks — lista zadań dla Nero (od użytkownika i własne).
Przechowywane w /home/tom/nero/memory/tasks.json
Nero może je czytać, dodawać i oznaczać jako wykonane.
"""

import json
from datetime import datetime
from pathlib import Path

TASKS_FILE = "/home/tom/nero/memory/tasks.json"


def _load() -> list:
    p = Path(TASKS_FILE)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(tasks: list):
    Path(TASKS_FILE).write_text(
        json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def add_task(content: str, source: str = "nero", priority: str = "normal") -> dict:
    """
    Dodaj zadanie.
    source: 'user' (od Tomka) lub 'nero' (własne)
    priority: 'high', 'normal', 'low'
    """
    tasks = _load()
    task = {
        "id": len(tasks) + 1,
        "content": content,
        "source": source,
        "priority": priority,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "done_at": None,
    }
    tasks.append(task)
    _save(tasks)
    return task


def get_pending(source: str = None) -> list:
    """Zwróć listę niewykonanych zadań. Opcjonalnie filtruj po source."""
    tasks = _load()
    result = [t for t in tasks if t.get("status") == "pending"]
    if source:
        result = [t for t in result if t.get("source") == source]
    # Sortuj: najpierw high priority, potem user > nero
    priority_order = {"high": 0, "normal": 1, "low": 2}
    source_order = {"user": 0, "nero": 1}
    result.sort(key=lambda t: (
        priority_order.get(t.get("priority", "normal"), 1),
        source_order.get(t.get("source", "nero"), 1)
    ))
    return result


def complete_task(task_id: int):
    """Oznacz zadanie jako wykonane."""
    tasks = _load()
    for t in tasks:
        if t.get("id") == task_id:
            t["status"] = "done"
            t["done_at"] = datetime.now().isoformat()
            break
    _save(tasks)


def get_all(limit: int = 20) -> list:
    """Zwróć ostatnie N zadań (wszystkie statusy)."""
    tasks = _load()
    return tasks[-limit:]


def summary() -> str:
    """Krótkie podsumowanie stanu zadań."""
    tasks = _load()
    pending = [t for t in tasks if t.get("status") == "pending"]
    user_tasks = [t for t in pending if t.get("source") == "user"]
    nero_tasks = [t for t in pending if t.get("source") == "nero"]
    if not pending:
        return "Brak oczekujących zadań."
    lines = [f"Zadania do wykonania: {len(pending)}"]
    if user_tasks:
        lines.append(f"  Od Tomka ({len(user_tasks)}):")
        for t in user_tasks[:3]:
            lines.append(f"    [{t['priority']}] {t['content'][:80]}")
    if nero_tasks:
        lines.append(f"  Własne ({len(nero_tasks)}):")
        for t in nero_tasks[:2]:
            lines.append(f"    [{t['priority']}] {t['content'][:80]}")
    return "\n".join(lines)
