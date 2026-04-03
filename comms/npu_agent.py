"""
NPU Agent — Qwen2.5-3B na AMD XDNA 2 NPU via Lemonade Server (FastFlowLM)
Szybki agent do prostych zadań: streszczenia, klasyfikacje, parsowanie, GitHub
"""

import json
import subprocess
import time
import urllib.request
import threading

NPU_MODEL    = "qwen2.5-it:3b"
NPU_PORT     = 8082
NPU_URL      = f"http://127.0.0.1:{NPU_PORT}"

_npu_proc    = None
_npu_lock    = threading.Lock()
_npu_ready   = False


def _check_server_alive() -> bool:
    """Sprawdź czy serwer już działa"""
    try:
        urllib.request.urlopen(f"{NPU_URL}/v1/models", timeout=3)
        return True
    except Exception:
        return False


def start_npu_server():
    """Startuje flm serve qwen2.5-it:3b na porcie 8082 (jeśli nie działa już)"""
    global _npu_proc, _npu_ready
    # Jeśli serwer już działa (np. odpalony ręcznie) — tylko oznacz jako gotowy
    if _check_server_alive():
        _npu_ready = True
        print("[npu] NPU agent już działa — podłączono")
        return
    if _npu_proc and _npu_proc.poll() is None:
        return
    print(f"[npu] Startuję Qwen2.5-3B na NPU (port {NPU_PORT})...")
    _npu_proc = subprocess.Popen(
        ["flm", "serve", NPU_MODEL, "--port", str(NPU_PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    for i in range(90):
        if _check_server_alive():
            _npu_ready = True
            print("[npu] NPU agent gotowy")
            return
        if i % 10 == 0 and i > 0:
            print(f"[npu] Czekam na serwer... ({i * 2}s)")
        time.sleep(2)
    print("[npu] NPU serwer nie odpowiada — agent wyłączony")
    _npu_ready = False


def stop_npu_server():
    global _npu_proc, _npu_ready
    # Nie zabijaj jesli serwer nadal odpowiada — zostaw dla kolejnej instancji
    if _npu_proc and not _check_server_alive():
        _npu_proc.terminate()
    _npu_proc = None
    _npu_ready = False


def is_ready() -> bool:
    return _npu_ready


def ask_npu(prompt: str, max_tokens: int = 200, temp: float = 0.4) -> str | None:
    """
    Wyślij prompt do NPU agenta. Zwraca odpowiedź lub None.
    Szybki (~5-15 tok/s decode na NPU), nie blokuje głównego mózgu.
    """
    if not _npu_ready:
        return None
    acquired = _npu_lock.acquire(timeout=30)
    if not acquired:
        return None
    try:
        data = json.dumps({
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temp
        }).encode()
        req = urllib.request.Request(
            f"{NPU_URL}/v1/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"].strip() or None
    except Exception as e:
        print(f"[npu] Błąd: {e}")
        return None
    finally:
        _npu_lock.release()


# ─── Gotowe narzędzia dla Nero ─────────────────────────────────────────────────

def summarize(text: str, max_words: int = 50) -> str | None:
    """Streść tekst do max_words słów"""
    prompt = f"Summarize in max {max_words} words, in Polish:\n\n{text[:2000]}\n\nSummary:"
    return ask_npu(prompt, max_tokens=120, temp=0.3)


def classify(text: str, categories: list[str]) -> str | None:
    """Zaklasyfikuj tekst do jednej z kategorii"""
    cats = ", ".join(categories)
    prompt = f"Classify into exactly one category: {cats}\n\nText: {text[:500]}\n\nCategory (one word only):"
    return ask_npu(prompt, max_tokens=10, temp=0.1)


def extract_keywords(text: str, n: int = 5) -> list[str]:
    """Wyciągnij n słów kluczowych"""
    prompt = f"Extract {n} keywords from this text. Reply with ONLY comma-separated keywords in English:\n\n{text[:1000]}"
    result = ask_npu(prompt, max_tokens=50, temp=0.2)
    if result:
        return [k.strip() for k in result.split(",") if k.strip()][:n]
    return []


def answer_simple(question: str, context: str = "") -> str | None:
    """Odpowiedź na proste pytanie, opcjonalnie z kontekstem"""
    if context:
        prompt = f"Context: {context[:800]}\n\nQuestion: {question}\n\nShort answer:"
    else:
        prompt = f"Question: {question}\n\nShort answer:"
    return ask_npu(prompt, max_tokens=100, temp=0.3)
