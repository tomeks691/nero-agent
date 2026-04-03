"""
Nero Notebook — zorganizowane notatki per-temat w Markdown.
/home/tom/nero/notes/<topic>.md
"""
from pathlib import Path
from datetime import datetime

NOTES_DIR = Path("/home/tom/nero/notes")

def _fname(topic: str) -> Path:
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic.lower().strip())
    safe = safe.replace(" ", "_")[:40]
    return NOTES_DIR / (safe + ".md")

def append_note(topic: str, content: str, heading: str = None) -> str:
    NOTES_DIR.mkdir(exist_ok=True)
    path = _fname(topic)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    h = f"## {heading}" if heading else f"## {ts}"
    entry = f"\n{h}\n{content.strip()}\n"
    write_header = not path.exists() or path.stat().st_size == 0
    with open(path, "a", encoding="utf-8") as f:
        if write_header:
            f.write(f"# {topic}\n")
        f.write(entry)
    return str(path)

def read_note(topic: str, last_chars: int = 2000) -> str | None:
    path = _fname(topic)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    return text[-last_chars:] if len(text) > last_chars else text

def list_topics() -> list[str]:
    if not NOTES_DIR.exists():
        return []
    return [f.stem.replace("_", " ") for f in NOTES_DIR.glob("*.md")]
