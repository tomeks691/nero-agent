"""
Nero Lab — eksperymentowanie na uczniu (LLM)
"""

import json
import subprocess
import time
import random
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    from comms.npu_agent import ask_npu as _ask_npu, is_ready as _npu_ready
except ImportError:
    _ask_npu = None
    _npu_ready = lambda: False

_student_proc = None

def start_student_server():
    global _student_proc
    if _student_proc and _student_proc.poll() is None:
        return
    print("[lab] Startuję student server (Qwen2.5-32B)...")
    _student_proc = subprocess.Popen(
        [LLAMA_SERVER, "-m", STUDENT_MODEL, "-c", "2048",
         "--port", str(STUDENT_PORT), "--host", "127.0.0.1",
         "--no-webui", "-np", "1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    for _ in range(60):
        try:
            urllib.request.urlopen(f"{STUDENT_URL}/health", timeout=1)
            print("[lab] Student server gotowy")
            return
        except Exception:
            time.sleep(2)
    print("[lab] Student server nie odpowiada")

def stop_student_server():
    global _student_proc
    if _student_proc:
        _student_proc.terminate()
        _student_proc = None

JOURNAL_FILE    = "/home/tom/nero/logs/research_journal.jsonl"
LLAMA_SERVER    = "/home/tom/llama.cpp/build/bin/llama-server"
STUDENT_MODEL   = "/home/tom/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf"
STUDENT_PORT    = 8081
STUDENT_URL     = f"http://127.0.0.1:{STUDENT_PORT}"
DRY_RUN         = False

SEED_HYPOTHESES = [
    ("Powtarzanie pytania poprawia odpowiedź ucznia",
     "What is 2+2? What is 2+2? Final answer:", "4, four"),
    ("Uczeń lepiej odpowiada gdy prompt kończy się na 'Answer:'",
     "The capital of Germany is Answer:", "berlin, germany"),
    ("Uczeń rozumie negacje",
     "A dog is NOT a cat. A fish is NOT a Answer:", "bird, mammal"),
    ("Uczeń potrafi kontynuować sekwencje",
     "1, 2, 3, 4, 5, Answer:", "6, six"),
    ("Uczeń rozumie analogie",
     "Hot is to cold as day is to Answer:", "night, dark"),
    ("Krótszy prompt daje lepsze wyniki",
     "Sky color?", "blue"),
    ("Uczeń wyciąga wnioski z kontekstu",
     "It rained. John took umbrella. Was John wet outside? Answer:", "no, dry"),
    ("Uczeń rozumie przyczynowość",
     "Ice near fire will Answer:", "melt, melts"),
    ("Uczeń zna podstawy biologii",
     "Plants need sunlight and water to Answer:", "grow, live"),
    ("Uczeń rozumie odwrotności",
     "Big opposite is small. Fast opposite is Answer:", "slow"),
    ("Uczeń zna stolice",
     "The capital of Japan is Answer:", "tokyo"),
    ("Uczeń rozumie porównania",
     "Elephant bigger than mouse. Mouse bigger than ant. Elephant bigger than Answer:", "ant"),
    ("Uczeń rozumie czas przeszły",
     "Today I run. Yesterday I Answer:", "ran"),
    ("Uczeń dokończy przysłowie",
     "Every cloud has a silver Answer:", "lining"),
    ("Uczeń rozumie warunki logiczne",
     "If A then B. A is true. Therefore B is Answer:", "true"),
]


class Experiment:
    def __init__(self, hypothesis: str, prompt: str, expected_keywords: str):
        self.id = f"exp_{int(time.time())}"
        self.hypothesis = hypothesis
        self.prompt = prompt
        self.expected_keywords = expected_keywords
        self.timestamp = datetime.now().isoformat()
        self.student_output = None
        self.success = None
        self.conclusion = None

    def to_dict(self):
        return {
            "id": self.id, "timestamp": self.timestamp,
            "hypothesis": self.hypothesis, "prompt": self.prompt,
            "expected_keywords": self.expected_keywords,
            "student_output": self.student_output,
            "success": self.success, "conclusion": self.conclusion,
        }


class NeroLab:
    def __init__(self):
        self.journal_path = Path(JOURNAL_FILE)
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        self.history = self._load_journal()
        print(f"[lab] Laboratorium gotowe | eksperymenty w historii: {len(self.history)}")

    def _load_journal(self):
        if not self.journal_path.exists():
            return []
        with open(self.journal_path) as f:
            return [json.loads(line) for line in f if line.strip()]

    def _journal_append(self, exp: Experiment):
        with open(self.journal_path, "a") as f:
            f.write(json.dumps(exp.to_dict(), ensure_ascii=False) + "\n")
        self.history.append(exp.to_dict())

    def run_student(self, prompt: str, max_tokens: int = 100) -> str | None:
        if DRY_RUN:
            return random.choice(["Yes.", "No.", "Berlin.", "6.", "Night.", "Slow.", "True.", "Melt.", "Grow."])
        try:
            import urllib.request as _u
            data = json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3
            }).encode()
            req = _u.Request(f"{STUDENT_URL}/v1/chat/completions", data=data, headers={"Content-Type": "application/json"})
            with _u.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                return result["choices"][0]["message"]["content"].strip() or None
        except Exception as e:
            print(f"[lab] Błąd ucznia: {e}")
            return None

    def run_student_npu(self, prompt: str, max_tokens: int = 80) -> str | None:
        """Użyj NPU agenta (Qwen2.5-3B) jako ucznia gdy brak student server."""
        if not (_npu_ready and _npu_ready() and _ask_npu):
            return None
        try:
            return _ask_npu(prompt, max_tokens=max_tokens, temp=0.3)
        except Exception as e:
            print(f"[lab] NPU student error: {e}")
            return None

    def run(self, exp: Experiment) -> Experiment:
        print(f"\n[lab] Eksperyment: {exp.id}")
        print(f"  Hipoteza: {exp.hypothesis}")
        print(f"  Odpalam ucznia...")
        output = self.run_student(exp.prompt)
        if output is None:
            output = self.run_student_npu(exp.prompt)
            if output:
                print(f"  [NPU fallback] {output[:80]}")
        exp.student_output = output
        if output:
            exp.success = self._evaluate(output, exp.expected_keywords)
            exp.conclusion = self._draw_conclusion(exp)
            status = "✓ SUKCES" if exp.success else "✗ PORAŻKA"
            print(f"  {status}: {exp.conclusion}")
            print(f"  Output ucznia: {output[:100]}")
        else:
            exp.success = False
            exp.conclusion = "Uczeń nie odpowiedział"
        self._journal_append(exp)
        return exp

    def _evaluate(self, output: str, expected_keywords: str) -> bool:
        keywords = [kw.strip().lower() for kw in expected_keywords.split(",")]
        output_lower = output.lower()
        hits = sum(1 for kw in keywords if kw in output_lower)
        return hits >= max(1, len(keywords) // 2)

    def _draw_conclusion(self, exp: Experiment) -> str:
        if exp.success:
            return f"Potwierdzone: {exp.hypothesis[:80]}"
        return f"Niepotwierdzone: {exp.hypothesis[:80]}"

    def pick_experiment(self) -> Experiment:
        """Wybierz następny eksperyment — preferuj nieprzetestowane"""
        tested = {e["hypothesis"] for e in self.history}
        untested = [h for h in SEED_HYPOTHESES if h[0] not in tested]
        if untested:
            hyp, prompt, keywords = random.choice(untested)
        else:
            # Wszystkie przetestowane — losuj z całej puli (Nero wraca do starych)
            hyp, prompt, keywords = random.choice(SEED_HYPOTHESES)
        return Experiment(hypothesis=hyp, prompt=prompt, expected_keywords=keywords)

    def stats(self):
        if not self.history:
            return {"total": 0, "success": 0, "failure": 0, "rate": 0.0}
        total = len(self.history)
        success = sum(1 for e in self.history if e.get("success"))
        return {"total": total, "success": success, "failure": total - success, "rate": success / total}

    def last_conclusions(self, n=5):
        return [e["conclusion"] for e in self.history[-n:] if e.get("conclusion")]
