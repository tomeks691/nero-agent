"""
Nero Scheduler — timery i przypomnienia z poczuciem czasu.
/home/tom/nero/memory/schedule.json
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

SCHEDULE_FILE = Path("/home/tom/nero/memory/schedule.json")

def _load() -> list:
    if not SCHEDULE_FILE.exists():
        return []
    try:
        return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save(items: list):
    SCHEDULE_FILE.parent.mkdir(exist_ok=True)
    SCHEDULE_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")

def add_reminder(message: str, in_seconds: int = None, at_iso: str = None) -> dict:
    items = _load()
    if in_seconds is not None:
        due = (datetime.now() + timedelta(seconds=in_seconds)).isoformat()
    elif at_iso:
        due = at_iso
    else:
        return {}
    item = {
        "id": int(datetime.now().timestamp() * 1000),
        "message": message,
        "due": due,
        "done": False,
    }
    items.append(item)
    _save(items)
    return item

def get_due() -> list[dict]:
    items = _load()
    now = datetime.now().isoformat()
    return [i for i in items if not i.get("done") and i.get("due", "9999") <= now]

def mark_done(reminder_id: int):
    items = _load()
    for i in items:
        if i.get("id") == reminder_id:
            i["done"] = True
    _save(items)

def pending_count() -> int:
    return len([i for i in _load() if not i.get("done")])
