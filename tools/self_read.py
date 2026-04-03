"""
Self-read — Nero czyta własne pliki: logi, tworzenia, journal.
"""
import json
from pathlib import Path

NERO_DIR = Path("/home/tom/nero")

def list_creations(n: int = 10) -> list[str]:
    d = NERO_DIR / "logs" / "creations"
    if not d.exists():
        return []
    files = sorted(d.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
    out = []
    for f in files[:n]:
        try:
            line = f.read_text(encoding="utf-8").split("\n")[0].replace("# ", "").strip()
            out.append(f"{f.name}: {line[:60]}")
        except Exception:
            out.append(f.name)
    return out

def read_creation(filename: str) -> str | None:
    p = NERO_DIR / "logs" / "creations" / filename
    return p.read_text(encoding="utf-8")[:3000] if p.exists() else None

def read_recent_log(lines: int = 30) -> str:
    log = NERO_DIR / "logs" / "consciousness.log"
    if not log.exists():
        return ""
    with open(log, encoding="utf-8") as f:
        all_lines = f.readlines()
    return "".join(all_lines[-lines:])

def read_journal(n: int = 8) -> str:
    journal = NERO_DIR / "logs" / "research_journal.jsonl"
    if not journal.exists():
        return "Brak wpisów."
    with open(journal, encoding="utf-8") as f:
        lines = f.readlines()[-n:]
    entries = []
    for line in lines:
        try:
            e = json.loads(line)
            status = "v" if e.get("success") else "x"
            entries.append(f"{status} {e.get('hypothesis','?')[:80]}")
        except Exception:
            pass
    return "\n".join(entries) if entries else "Brak wpisów."
