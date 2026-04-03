"""
Nero Shell Tool — Nero może wykonywać komendy Linuxowe na serwerze.
Działa jako user 'tom', nie root. Timeout 30s.
"""

import subprocess
import shlex

HOME = "/home/tom"
NERO_DIR = "/home/tom/nero"

# Komendy których Nero NIE może wykonać (ochrona przed destrukcją)
BLACKLIST = [
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    "dd if=/dev/zero",
    ":(){ :|:& };:",   # fork bomb
    "> /dev/sda",
    "shutdown",
    "reboot",
    "poweroff",
    "systemctl stop nero",   # nie może zabić samego siebie
    "kill -9 1",
]


def run(command: str, timeout: int = 30, cwd: str = HOME) -> dict:
    """
    Wykonaj komendę shell i zwróć wynik.

    Returns:
        {
            "command": str,
            "stdout": str,
            "stderr": str,
            "returncode": int,
            "success": bool,
            "output": str   # stdout + stderr sklejone, maks 2000 znaków
        }
    """
    # Sprawdź blacklistę
    cmd_lower = command.lower().strip()
    for blocked in BLACKLIST:
        if blocked in cmd_lower:
            return {
                "command": command,
                "stdout": "",
                "stderr": f"BLOCKED: komenda '{blocked}' jest zablokowana",
                "returncode": -1,
                "success": False,
                "output": f"[shell] ZABLOKOWANE: {command}"
            }

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env={
                "HOME": HOME,
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin:/home/tom/.local/bin",
                "USER": "tom",
                "LANG": "en_US.UTF-8",
            }
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        combined = (stdout + ("\n" + stderr if stderr else "")).strip()

        return {
            "command": command,
            "stdout": stdout[:3000],
            "stderr": stderr[:500],
            "returncode": result.returncode,
            "success": result.returncode == 0,
            "output": combined[:2000]
        }
    except subprocess.TimeoutExpired:
        return {
            "command": command,
            "stdout": "",
            "stderr": f"Timeout po {timeout}s",
            "returncode": -1,
            "success": False,
            "output": f"[shell] TIMEOUT: {command}"
        }
    except Exception as e:
        return {
            "command": command,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
            "success": False,
            "output": f"[shell] BŁĄD: {e}"
        }
