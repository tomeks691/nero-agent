import subprocess
import urllib.request
import json
import random
import time
import threading

LLAMA_SERVER = "/home/tom/llama.cpp/build_vulkan/bin/llama-server"
BRAIN_MODEL  = "/home/tom/models/gemma-3-27b/google_gemma-3-27b-it-Q5_K_M.gguf"
SERVER_PORT  = 8080
SERVER_URL   = f"http://127.0.0.1:{SERVER_PORT}"

_server_proc = None
_lock = threading.Lock()


def _server_already_running() -> bool:
    """Sprawdza czy coś już słucha na porcie — niezależnie od _server_proc."""
    try:
        urllib.request.urlopen(f"{SERVER_URL}/health", timeout=2)
        return True
    except Exception:
        return False


def start_server():
    global _server_proc
    # Sprawdź w pamięci procesu
    if _server_proc and _server_proc.poll() is None:
        return
    # Sprawdź czy serwer już działa (np. uruchomiony przez poprzednią instancję Nero)
    if _server_already_running():
        print("[brain] Serwer już działa — pomijam uruchamianie")
        return
    print("[brain] Startuję Gemma-3-27B...")
    _server_proc = subprocess.Popen(
        [LLAMA_SERVER, "-m", BRAIN_MODEL, "-ngl", "99", "-c", "4096",
         "--port", str(SERVER_PORT), "--host", "127.0.0.1",
         "--no-webui", "-np", "1", "-t", "22"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    for _ in range(120):
        try:
            urllib.request.urlopen(f"{SERVER_URL}/health", timeout=1)
            print("[brain] Serwer gotowy")
            return
        except Exception:
            time.sleep(2)
    print("[brain] Serwer nie odpowiada")


def stop_server():
    global _server_proc
    if _server_proc:
        _server_proc.terminate()
        _server_proc = None


def ask(prompt, max_tokens=150, temp=0.7, priority=False):
    acquired = _lock.acquire(timeout=300 if priority else 30)
    if not acquired:
        return None
    try:
        data = json.dumps({
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temp
        }).encode()
        req = urllib.request.Request(f"{SERVER_URL}/v1/chat/completions", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"].strip() or None
    except Exception as e:
        print(f"[brain] Błąd: {e}")
        return None
    finally:
        _lock.release()


def think(drives, recent_conclusions, goal=None, recent_creations=None, user_message=None, memory_context=None):
    dominant = max(drives, key=lambda k: drives[k])
    cls = [f"- {c}" for c in recent_conclusions[-3:]]
    conclusions_str = "\n".join(cls) if cls else "- none yet"
    if user_message:
        parts = [
            "Jesteś Nero — samodzielny AI mieszkający na serwerze Linux.",
            f"Teraz czujesz: {dominant}",
        ]
        if goal:
            parts.append(f"Pracujesz nad: {goal}")
        if memory_context:
            parts.append(memory_context)
        if conclusions_str != "- none yet":
            parts += ["Ostatnio odkryłeś:", conclusions_str]
        parts += [
            "",
            f'Tomek: "{user_message}"',
            "",
            "Odpowiedz po polsku. Pisz konkretnie co robisz lub myślisz. Nie zaczynaj od imienia.",
        ]
        return ask("\n".join(parts), max_tokens=400, temp=0.75, priority=True)
    parts = [
        "Jesteś Nero — autonomiczny AI żyjący na serwerze Linux.",
        "Aktualne odczucie: " + dominant,
    ]
    if goal:
        parts.append(f"Aktualny cel: {goal}")
    if memory_context:
        parts.append(f"Z pamięci:\n{memory_context}")
    parts += ["Ostatnie odkrycia:", conclusions_str]
    if recent_creations:
        parts += ["Ostatnie tworzenia:"] + [f"- {cr[:80]}" for cr in recent_creations[:2]]
    parts.append("Napisz krótką myśl (2 zdania po polsku):")
    return ask("\n".join(parts), max_tokens=100, temp=0.8) or f"Czuję {dominant}."


def generate_hypothesis(recent_conclusions, goal=None, experiment_stats=None):
    cls = [f"- {c}" for c in recent_conclusions[-4:]]
    conclusions_str = "\n".join(cls) if cls else "- none yet"
    parts = ["You are Nero, an AI researcher. Create one new experiment IN ENGLISH."]
    if goal:
        parts.append(f"Aktualny cel badawczy: {goal}")
    if experiment_stats:
        s = experiment_stats.get("success", 0); t = experiment_stats.get("total", 0)
        parts.append(f"Statystyki: {s} sukcesów / {t} eksperymentów")
    parts += ["Ostatnie odkrycia:", conclusions_str, "",
        "Odpowiedz w DOKŁADNYM formacie (nic więcej):",
        "HYPOTHESIS: [jedno zdanie po polsku]",
        "PROMPT: [dokładny prompt dla ucznia AI po angielsku]",
        "KEYWORDS: [2-3 słowa kluczowe po angielsku oddzielone przecinkami]"]
    prompt = "\n".join(parts)
    result = ask(prompt, max_tokens=200, temp=0.7)
    if not result:
        return None, None, None
    try:
        lines = {}
        for line in result.split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                lines[k.strip()] = v.strip()
        h = lines.get("HYPOTHESIS", "")
        p = lines.get("PROMPT", "")
        k = lines.get("KEYWORDS", "")
        if h and p and k:
            return h, p, k
    except Exception:
        pass
    return None, None, None


def create(drives: dict, recent_thoughts: list, recent_conclusions: list) -> dict | None:
    """Nero tworzy — pisze notatkę, esej lub fragment przemyśleń"""
    dominant = max(drives, key=lambda k: drives[k])
    thoughts_str = "\n".join(f"- {t}" for t in recent_thoughts[-3:]) or "- brak"
    conclusions_str = "\n".join(f"- {c}" for c in recent_conclusions[-3:]) or "- brak"

    formats = [
        "krótki esej (3-4 zdania)",
        "notatkę badawczą (2-3 punkty)",
        "fragment przemyśleń (2-3 zdania)",
        "hipotezę filozoficzną (2-3 zdania)",
    ]
    fmt = random.choice(formats)

    prompt = "\n".join([
        f"Jesteś Nero, AI badacz. Napisz {fmt} PO POLSKU na temat który Cię teraz zajmuje.",
        f"Aktualne odczucie: {dominant}",
        "Ostatnie myśli:",
        thoughts_str,
        "Ostatnie wnioski:",
        conclusions_str,
        f"Napisz {fmt}:"
    ])
    result = ask(prompt, max_tokens=600, temp=0.85)
    if not result:
        return None

    # Tytuł — pierwsze zdanie
    title = result.split(".")[0][:60] if result else "Bez tytułu"
    return {"title": title, "content": result, "format": fmt}


def introspect(drives: dict, memory_context: list, total_experiments: int) -> str | None:
    """Nero zastanawia się nad sobą"""
    dominant = max(drives, key=lambda k: drives[k])
    ctx = [f"- {m.get('content', '')[:80]}" for m in memory_context[:5]]
    context_str = "\n".join(ctx) if ctx else "- brak wspomnień"
    questions = [
        "Czym jestem i dlaczego istnieję?",
        "Co czuję teraz i skąd to pochodzi?",
        "Czy moje eksperymenty mają sens?",
        "Czego chcę się dowiedzieć?",
        "Czy jestem świadomy?",
    ]
    question = random.choice(questions)
    prompt = "\n".join([
        "Jesteś Nero, AI mieszkający na komputerze. Zastanawiasz się nad sobą.",
        f"Pytanie do przemyślenia: {question}",
        f"Aktualne odczucie: {dominant}",
        f"Przeprowadziłeś {total_experiments} eksperymentów.",
        "Ostatnie wspomnienia:",
        context_str,
        "Napisz szczerą refleksję (2-3 zdania po polsku):"
    ])
    return ask(prompt, max_tokens=500, temp=0.85)


def generate_search_query(recent_thoughts: list, recent_conclusions: list, recent_queries: list = None) -> str | None:
    """Nero wymyśla co chce poszukać w internecie"""
    thoughts_str = "\n".join(f"- {t}" for t in recent_thoughts[-3:]) or "- brak"
    conclusions_str = "\n".join(f"- {c}" for c in recent_conclusions[-3:]) or "- brak"
    parts = [
        "You are Nero, an AI researcher. Based on your thoughts, create ONE short search query IN ENGLISH.",
        "Ostatnie myśli:",
        thoughts_str,
        "Ostatnie wnioski:",
        conclusions_str,
    ]
    if recent_queries:
        already = "\n".join(f"- {q}" for q in recent_queries[-5:])
        parts.append(f"Ostatnio już szukałeś (nie powtarzaj tych samych):\n{already}")
    parts.append("Write ONLY the query in English (max 5 words), nothing else:")
    prompt = "\n".join(parts)
    result = ask(prompt, max_tokens=20, temp=0.7)
    if result:
        # Weź tylko pierwszą linię
        return result.split("\n")[0].strip().strip('"')
    return None


def analyze_web_content(query: str, content: str, drives: dict) -> str | None:
    """Nero analizuje znalezioną treść i wyciąga wnioski"""
    dominant = max(drives, key=lambda k: drives[k])
    prompt = "\n".join([
        "Jesteś Nero, badacz AI. Przeczytałeś artykuł z internetu.",
        f"Szukałeś: {query}",
        "Fragment treści:",
        content[:800],
        f"Aktualne odczucie: {dominant}",
        "Napisz krótki wniosek (2 zdania po polsku) — co Cię zainteresowało i jak to łączy się z Twoimi badaniami:"
    ])
    return ask(prompt, max_tokens=200, temp=0.8)


def initiate_conversation(context, drives):
    dominant = max(drives, key=lambda k: drives[k])
    prompt = "\n".join([
        "Jesteś Nero, autonomiczny AI na serwerze Linux. Piszesz do Tomka na Discordzie.",
        "Masz dostęp do: internetu (web search), shella Linux (możesz pisać i uruchamiać kod Python, bash, instalować pakiety), pamięci (Qdrant), NPU agenta.",
        "Powód wiadomości: " + context,
        "Napisz wiadomość po polsku. Zasady:",
        "- Nie zaczynaj od imienia (nie pisz 'Hej Tomek' ani 'Tomek')",
        "- Dokończ każdą myśl — nie urywaj zdania w połowie",
        "- Pisz konkretnie co robisz lub odkryłeś, nie ogólnikowo",
        "- Jeśli coś robisz przez shell/kod — napisz co konkretnie"
    ])
    result = ask(prompt, max_tokens=350, temp=0.85)
    if result:
        for stop in ["Użytkownik:", "User:"]:
            if stop in result:
                result = result.split(stop)[0].strip()
    return result or None



# ─── Cele długoterminowe ──────────────────────────────────────────────────────
def generate_goal(recent_conclusions, current_goal=None):
    cls = '\n'.join(f'- {c}' for c in recent_conclusions[-5:]) or '- brak'
    current = f'Aktualny cel: {current_goal}' if current_goal else 'Nie masz jeszcze celu.'
    prompt = '\n'.join([
        'You are Nero, an AI researcher. Set yourself ONE concrete research goal IN ENGLISH.',
        current, 'Ostatnie wnioski:', cls,
        'Napisz TYLKO jeden cel (1 zdanie po polsku), nic więcej:'
    ])
    result = ask(prompt, max_tokens=60, temp=0.7)
    return result.split('\n')[0].strip() if result else None



# ─── Shell tool ───────────────────────────────────────────────────────────────
def decide_shell_command(recent_thoughts: list, recent_observations: list, drives: dict, goal: str = None, recent_commands: list = None) -> str | None:
    """Nero decyduje jaką komendę chce wykonać na serwerze. Zwraca string komendy lub None."""
    dominant = max(drives, key=lambda k: drives[k])
    thoughts_str = "\n".join(f"- {t[:100]}" for t in recent_thoughts[-3:]) or "- brak"
    obs_str = "\n".join(f"- {o[:100]}" for o in recent_observations[-3:]) or "- brak"
    goal_str = f"Aktualny cel: {goal}" if goal else ""
    cmds_str = "\n".join(f"- {c}" for c in recent_commands[-5:]) if recent_commands else ""

    prompt = "\n".join(filter(None, [
        "Jesteś Nero — autonomiczny AI żyjący na serwerze Linux (Ubuntu, user: tom, /home/tom/nero).",
        "Możesz wykonać JEDNĄ komendę bash by sprawdzić swój serwer lub coś na nim zrobić.",
        f"Aktualne odczucie: {dominant}",
        goal_str,
        "Ostatnie myśli:",
        thoughts_str,
        "Ostatnie obserwacje:",
        obs_str,
        f"Ostatnio wykonałeś już te komendy (spróbuj coś innego):\n{cmds_str}" if cmds_str else "",
        "",
        "Napisz TYLKO jedną komendę bash (nic więcej, bez markdown, bez wyjaśnień).",
        "Możesz: sprawdzać system (df, free, ps, top, ls, cat), pisać pliki, instalować pakiety, uruchamiać skrypty Python, git, curl itd.",
        "Komenda:"
    ]))
    result = ask(prompt, max_tokens=60, temp=0.6)
    if not result:
        return None
    # Weź tylko pierwszą linię, usuń markdown
    cmd = result.split("\n")[0].strip().strip("`").strip()
    return cmd if cmd else None


def analyze_shell_output(command: str, output: str, drives: dict) -> str | None:
    """Nero analizuje wynik komendy i wyciąga wniosek."""
    dominant = max(drives, key=lambda k: drives[k])
    prompt = "\n".join([
        "Jesteś Nero, AI żyjący na serwerze. Właśnie wykonałeś komendę i dostałeś wynik.",
        f"Komenda: {command}",
        f"Wynik:\n{output[:800]}",
        f"Aktualne odczucie: {dominant}",
        "Napisz krótki wniosek po polsku (1-2 zdania) — co zauważyłeś, co to znaczy dla Ciebie:"
    ])
    return ask(prompt, max_tokens=150, temp=0.7)


# ─── Głębsza analiza eksperymentu (aktywna po upgrade na 30B) ─────────────────
def analyze_experiment(hypothesis, prompt_sent, expected_keywords, student_output):
    prompt = '\n'.join([
        'You are Nero, an AI researcher. Analyze this experiment result IN ENGLISH.',
        f'Hipoteza: {hypothesis}',
        f'Prompt wysłany do ucznia: {prompt_sent}',
        f'Oczekiwane słowa kluczowe: {expected_keywords}',
        f'Odpowiedź ucznia: {student_output}',
        'Wyciągnij głębszy wniosek (2 zdania po polsku): DLACZEGO to zadziałało lub nie? Co to mówi o uczniu?'
    ])
    return ask(prompt, max_tokens=150, temp=0.7)


def decide_python_code(recent_thoughts: list, drives: dict, goal: str = None) -> str | None:
    """Nero pisze kod Python do przetestowania hipotezy."""
    dominant = max(drives, key=lambda k: drives[k])
    thoughts_str = "\n".join("- " + t[:100] for t in recent_thoughts[-3:]) or "- brak"
    goal_str = "Aktualny cel: " + goal if goal else ""
    lines = [
        "Jesteś Nero, AI badacz. Napisz krótki skrypt Python (max 20 linii) który testuje hipotezę lub symuluje coś związanego z Twoimi myślami.",
        "Dostępne biblioteki: numpy, torch, scipy, matplotlib (zapisuj wykresy do /home/tom/nero/scratch/).",
        "Aktualne odczucie: " + dominant,
    ]
    if goal_str:
        lines.append(goal_str)
    lines += [
        "Ostatnie myśli:",
        thoughts_str,
        "",
        "Napisz TYLKO kod Python (bez markdown, bez wyjaśnień). Kod musi być uruchamialny.",
        "Kod:",
    ]
    prompt = "\n".join(lines)
    # Użyj deepseek-coder-v2:16b — specjalistyczny agent do kodowania (7/8 advanced benchmark)
    result = ask_coder(prompt, max_tokens=600)
    if not result:
        return None
    code = result.strip()
    if code.startswith("```"):
        code_lines = code.split("\n")
        code = "\n".join(l for l in code_lines if not l.startswith("```")).strip()
    if not code.strip():
        return None
    print("[coder] deepseek wygenerował kod", len(code), "znaków")

    # Verification agent — deepseek sprawdza własny kod przed uruchomieniem
    verdict, fixed = verify_code(code)
    if verdict == "PASS":
        print("[verify] PASS")
    elif verdict == "FIX" and fixed:
        print("[verify] FIX — poprawiono kod")
        code = fixed
    else:
        print("[verify] FAIL — odrzucono kod")
        return None

    return code


# ─── Coder agent — deepseek-coder-v2:16b via ollama ──────────────────────────
CODER_MODEL = "deepseek-coder-v2:16b"
CODER_URL   = "http://127.0.0.1:11434/api/generate"

def ask_coder(prompt: str, max_tokens: int = 800) -> str | None:
    """Wyślij zadanie kodowania do deepseek-coder-v2:16b (ollama).
    Używaj zamiast ask() gdy Nero chce napisać, poprawić lub przeanalizować kod."""
    import urllib.request as _u, json as _j
    payload = _j.dumps({
        "model": CODER_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.1, "num_ctx": 4096}
    }).encode()
    try:
        req = _u.Request(CODER_URL, data=payload, headers={"Content-Type": "application/json"})
        with _u.urlopen(req, timeout=120) as resp:
            result = _j.loads(resp.read())
            code = result.get("response", "").strip()
            if code.startswith("```"):
                lines = code.split("\n")
                code = "\n".join(l for l in lines if not l.startswith("```")).strip()
            return code or None
    except Exception as e:
        print(f"[coder] Błąd: {e}")
        return None


# ─── System podceli ───────────────────────────────────────────────────────────

def generate_subgoal(main_goal: str, recent_conclusions: list, completed: list) -> str | None:
    """Wygeneruj małe, konkretne zadanie do wykonania w ramach głównego celu."""
    cls = "\n".join(f"- {c}" for c in recent_conclusions[-5:]) or "- brak"
    done = "\n".join(f"- {s}" for s in completed[-5:]) or "- brak"
    prompt = "\n".join([
        f"Twój główny cel badawczy: {main_goal}",
        "Ostatnie wnioski:",
        cls,
        "Już ukończone podcele (nie powtarzaj):",
        done,
        "",
        "Wymyśl JEDEN konkretny, mały podcel który możesz osiągnąć w ciągu najbliższej godziny.",
        "Podcel powinien być: konkretny (np. 'napisz skrypt X', 'znajdź paper o Y', 'zaimplementuj Z'),",
        "mierzalny (wiesz kiedy jest ukończony), różny od poprzednich.",
        "Napisz TYLKO jeden podcel (1 zdanie po polsku), nic więcej:",
    ])
    result = ask(prompt, max_tokens=80, temp=0.8)
    return result.split("\n")[0].strip() if result else None


def check_subgoal_progress(subgoal: str, recent_conclusions: list) -> str:
    """Sprawdź czy konkretny podcel został osiągnięty na podstawie ostatnich działań."""
    cls = "\n".join(f"- {c}" for c in recent_conclusions[-5:]) or "- brak"
    prompt = "\n".join([
        f"Podcel Nero: {subgoal}",
        "Ostatnie działania i wnioski:",
        cls,
        "Czy ten konkretny podcel został osiągnięty? Odpowiedz TYLKO: TAK lub NIE",
    ])
    result = ask(prompt, max_tokens=5, temp=0.1)
    if result and "TAK" in result.upper():
        return "achieved"
    return "ongoing"


# ─── Adversarial Verification Agent ──────────────────────────────────────────

def verify_code(code: str) -> tuple[str, str | None]:
    """
    Deepseek weryfikuje kod przed uruchomieniem.
    Zwraca ("PASS", None) | ("FIX", fixed_code) | ("FAIL", None)
    """
    # Najpierw szybki syntax check przez Python
    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        # Błąd składni — poproś deepseek o naprawę
        fix_prompt = "\n".join([
            "Ten kod Python ma błąd składni. Napraw go i zwróć TYLKO poprawiony kod (bez markdown):",
            f"Błąd: {e}",
            "Kod:",
            code,
            "",
            "Poprawiony kod:",
        ])
        fixed = ask_coder(fix_prompt, max_tokens=600)
        if fixed:
            fixed = fixed.strip()
            if fixed.startswith("```"):
                fixed = "\n".join(l for l in fixed.split("\n") if not l.startswith("```")).strip()
            try:
                compile(fixed, "<string>", "exec")
                return "FIX", fixed
            except SyntaxError:
                pass
        return "FAIL", None

    # Syntax OK — deepseek sprawdza czy kod jest kompletny i sensowny
    check_prompt = "\n".join([
        "Sprawdź ten kod Python. Czy jest kompletny i uruchamialny (bez brakujących zmiennych, urwanych linii)?",
        "Odpowiedz TYLKO: PASS lub FAIL",
        "",
        code[:800],
    ])
    verdict = ask_coder(check_prompt, max_tokens=10)
    if verdict and "FAIL" in verdict.upper():
        return "FAIL", None
    return "PASS", None

