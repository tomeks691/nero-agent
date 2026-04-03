"""
Nero Cron — Nero sam sobie planuje zadania z harmonogramem.
Przechowywane w /home/tom/nero/memory/cron_jobs.json

Nero może:
  add_job(prompt, cron_expr, recurring)  — zaplanuj zadanie
  delete_job(job_id)                     — usuń zadanie
  list_jobs()                            — pokaż wszystkie
  get_due_jobs()                         — co teraz do wykonania
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from croniter import croniter

CRON_FILE = Path("/home/tom/nero/memory/cron_jobs.json")


def _load() -> list:
    if not CRON_FILE.exists():
        return []
    try:
        return json.loads(CRON_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(jobs: list):
    CRON_FILE.parent.mkdir(exist_ok=True)
    CRON_FILE.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")


def _next_run(cron_expr: str) -> str:
    return croniter(cron_expr, datetime.now()).get_next(datetime).isoformat()


def add_job(prompt: str, cron_expr: str, recurring: bool = True) -> dict:
    """Dodaj zadanie cron. Zwraca job dict."""
    if not croniter.is_valid(cron_expr):
        raise ValueError(f"Nieprawidłowe wyrażenie cron: {cron_expr}")
    jobs = _load()
    job = {
        "id": str(uuid.uuid4())[:8],
        "prompt": prompt,
        "cron_expr": cron_expr,
        "recurring": recurring,
        "next_run": _next_run(cron_expr),
        "created_at": datetime.now().isoformat(),
        "run_count": 0,
    }
    jobs.append(job)
    _save(jobs)
    return job


def delete_job(job_id: str) -> bool:
    jobs = _load()
    new_jobs = [j for j in jobs if j["id"] != job_id]
    if len(new_jobs) == len(jobs):
        return False
    _save(new_jobs)
    return True


def list_jobs() -> list[dict]:
    return _load()


def get_due_jobs() -> list[dict]:
    """Zwróć zadania które powinny teraz się wykonać."""
    now = datetime.now().isoformat()
    return [j for j in _load() if j.get("next_run", "9999") <= now]


def mark_fired(job_id: str):
    """Po wykonaniu: usuń one-shot lub zaplanuj kolejne uruchomienie."""
    jobs = _load()
    for job in jobs:
        if job["id"] != job_id:
            continue
        job["run_count"] = job.get("run_count", 0) + 1
        job["last_run"] = datetime.now().isoformat()
        if job.get("recurring", True):
            job["next_run"] = _next_run(job["cron_expr"])
        else:
            jobs = [j for j in jobs if j["id"] != job_id]
            break
    _save(jobs)


def summary() -> str:
    jobs = _load()
    if not jobs:
        return "Brak zaplanowanych zadań."
    lines = []
    for j in jobs:
        rec = "↻" if j.get("recurring") else "→"
        lines.append(f"[{j['id']}] {rec} {j['cron_expr']} | {j['prompt'][:60]} | następne: {j['next_run'][:16]}")
    return "\n".join(lines)
