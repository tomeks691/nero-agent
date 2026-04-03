"""
Python REPL — Nero uruchamia kod Python i widzi wynik.
"""
import subprocess
import sys
import os
import tempfile
from pathlib import Path

SCRATCH_DIR = Path("/home/tom/nero/scratch")

def run_code(code: str, timeout: int = 15) -> dict:
    """Uruchom kod Python, zwróć stdout/stderr/success."""
    SCRATCH_DIR.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", dir=SCRATCH_DIR, delete=False, encoding="utf-8") as f:
        f.write(code)
        fname = f.name
    try:
        result = subprocess.run(
            [sys.executable, fname],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(SCRATCH_DIR),
            env={
                "HOME": "/home/tom",
                "PATH": "/home/tom/nero/venv/bin:/usr/local/bin:/usr/bin:/bin",
                "PYTHONPATH": "/home/tom/nero/venv/lib/python3.14/site-packages",
                "LANG": "en_US.UTF-8",
            }
        )
        output = (result.stdout + result.stderr).strip()
        return {
            "success": result.returncode == 0,
            "output": output[:2000],
            "code": code,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": f"[timeout po {timeout}s]", "code": code}
    except Exception as e:
        return {"success": False, "output": str(e), "code": code}
    finally:
        try:
            os.unlink(fname)
        except Exception:
            pass
