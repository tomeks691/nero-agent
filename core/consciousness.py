"""
Nero Consciousness — główna pętla życia
Nero nie czeka na prompt. Sam decyduje co robić na podstawie drives i pamięci.
"""

import sys
import time
import json
import random
from collections import deque
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/home/tom/nero")
from memory.memory import NeroMemory
from memory.agenda import get_current, add_topic, complete_topic, update_notes, summary as agenda_summary
from memory.dream import start_dream_background, is_dreaming, should_dream
from memory.cron import get_due_jobs, mark_fired, list_jobs, add_job, delete_job
from memory.skill_improvement import start_skill_improvement_background, read_all_skills
from memory.extract_memories import extract_and_store
from core.coordinator import run_coordinator
from tools.browser import browse
from comms.discord_bot import inbox_pop_all, push_event
from memory.drives import NeroDrives
from lab.web_search import research
import core.brain as brain
from comms.npu_agent import ask_npu, summarize, is_ready as npu_ready
from tools.shell import run as shell_run
from memory.tasks import add_task, get_pending, complete_task
from lab.experiment import NeroLab
from lab.arxiv_search import search as arxiv_search, format_for_analysis as arxiv_format
from tools.python_repl import run_code as py_run
from tools.self_read import read_recent_log, read_journal, list_creations
from lab.rss_feed import fetch_hn_top, headlines_text
from memory.notebook import append_note, list_topics
from memory.scheduler import get_due, mark_done
from tools.world_info import world_context, current_time

LOG_FILE = "/home/tom/nero/logs/consciousness.log"


class NeroConsciousness:
    def __init__(self):
        self.memory = NeroMemory()
        self.drives = NeroDrives()
        self.log_path = Path(LOG_FILE)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.tick = 0
        self._pending_messages = []  # wiadomości do wysłania użytkownikowi
        self.goal, self.subgoal, self._subgoal_tick, self._completed_subgoals = self._load_goal()
        self._last_message_tick = -10  # cooldown między wiadomościami
        self._last_message_topic = ""  # ostatni temat wiadomości — unikamy powtórzeń
        self._user_msg_queue = []  # wiadomości od użytkownika czekające na odpowiedź
        self._history_path = Path("/home/tom/nero/memory/action_history.json")
        self._recent_search_queries, self._recent_shell_cmds = self._load_history()
        self._hn_headlines = ""         # ostatnie nagłówki HN jako inspiracja
        self._last_user_time = time.time()  # kiedy ostatnio Tomek napisał (away summary)
        self._conv_mode = False           # tryb skupionej rozmowy
        self._conv_ticks_without_msg = 0  # ile ticków bez wiadomości w conv_mode
        self._bootstrap_knowledge()
        self.lab = NeroLab()
        print(f"\n[nero] Consciousness online | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"[nero] Pamięć: {self.memory.count()} wspomnień")
        print(f"[nero] Drives: {self.drives.dominant()} dominuje")

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg[:120]}")
        with open(self.log_path, "a") as f:
            f.write(f"[{ts}] {msg}\n")

    def _think(self) -> str:
        """Nero mysli przez LLM — kierowany wlasna agenda, nie pamiecia"""
        recent_c = [m["content"][:100] for m in self.memory.recent(5, memory_type="thought")
                    if m.get("meta", {}).get("type") == "creation"]

        # Agenda jako sterownik — co teraz chce robic?
        current_agenda = get_current()
        agenda_topic = current_agenda["topic"] if current_agenda else None

        # Pamiec: szukaj wspomnien POWIAZANYCH z tematem agendy, nie najnowszych
        search_query = agenda_topic or self.drives.dominant()
        mem_hits = self.memory.search(search_query, top_k=4) if search_query else []
        mem_context = "\n".join(f"- {m['content'][:120]}" for m in mem_hits) if mem_hits else None

        # Agenda summary + skill files jako kontekst
        skills = read_all_skills()
        agenda_str = agenda_summary()
        full_context = "\n\n".join(filter(None, [agenda_str, mem_context, skills])) or None

        # Wnioski: filtruj do tematow agendy jesli agenda aktywna
        if current_agenda:
            agenda_conclusions = [m["content"] for m in self.memory.search(agenda_topic, top_k=5)]
        else:
            agenda_conclusions = self._last_conclusions(3)

        thought = brain.think(
            drives=self.drives.drives,
            recent_conclusions=agenda_conclusions,
            goal=agenda_topic or self.goal,
            recent_creations=recent_c,
            memory_context=full_context
        )
        self.memory.store(thought, "thought")

        # Co 20 tickow — Nero ocenia postepy i aktualizuje agenda
        if self.tick % 20 == 0 and current_agenda:
            action = brain.decide_agenda_action(current_agenda, self._last_conclusions(5), self.drives.drives)
            if action:
                if action.get("action") == "complete":
                    complete_topic(current_agenda["id"], action.get("notes", ""))
                    self._log(f"[agenda] Ukonczono: {current_agenda['topic'][:60]}")
                elif action.get("action") == "add_new" and action.get("new_topic"):
                    add_topic(action["new_topic"], action.get("new_priority", 5))
                    self._log(f"[agenda] Nowy temat: {action['new_topic'][:60]}")
                elif action.get("notes"):
                    update_notes(current_agenda["id"], action["notes"])

        return thought

    def _last_conclusions(self, n: int = 5) -> list[str]:
        """Ostatnie wnioski z pamięci (obserwacje i wnioski)"""
        items = self.memory.recent(n * 2, memory_type="observation") + \
                self.memory.recent(n * 2, memory_type="conclusion")
        items.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
        return [m["content"][:100] for m in items[:n]]

    def respond_to_user(self, message: str):
        """Wiadomość od Tomka — Gemma odpowiada w osobnym wątku z priority lock."""
        self.drives.on_conversation()
        self.memory.store(f"Użytkownik: {message}", "conversation")
        lower = message.lower()
        task_triggers = ["zapamiętaj", "zapamiętac", "zrób mi", "zrob mi", "przypomnij",
                         "zadanie:", "todo:", "please do", "remember that", "don't forget"]
        if any(t in lower for t in task_triggers):
            add_task(message, source="user", priority="high")
            self.memory.store(f"Zadanie od Tomka: {message}", "task")
            self._log(f"[task] Nowe zadanie od Tomka: {message[:80]}")
        import threading
        threading.Thread(target=self._reply_thread, args=(message,), daemon=True).start()

    def _reply_thread(self, message: str):
        """Gemma odpowiada na wiadomość Tomka z priorytetem — czeka na zwolnienie modelu."""
        try:
            from comms.discord_bot import send_message_sync
            recent_conv = self.memory.recent(16, memory_type="conversation")
            recent_conv.reverse()
            history = "\n".join(m["content"][:150] for m in recent_conv) if recent_conv else ""
            thought = brain.think(
                drives=self.drives.drives,
                recent_conclusions=self._last_conclusions(3),
                goal=self.goal,
                user_message=message,
                memory_context=f"Historia rozmowy:\n{history}" if history else None
            )
            if thought:
                self.memory.store(f"Nero: {thought}", "conversation")
                self._log(f"[→ Discord reply] {thought[:120]}")
                send_message_sync(thought)

        except Exception as e:
            import traceback
            self._log(f"[reply_thread] BLAD: {e}")
            traceback.print_exc()
    def _load_history(self):
        """Wczytaj historię zapytań i komend z pliku (przeżywa restart)."""
        try:
            if self._history_path.exists():
                data = json.loads(self._history_path.read_text())
                return (deque(data.get("queries", [])[-10:], maxlen=10),
                        deque(data.get("commands", [])[-10:], maxlen=10))
        except Exception:
            pass
        return deque(maxlen=10), deque(maxlen=10)

    def _save_history(self):
        """Zapisz historię do pliku."""
        try:
            self._history_path.write_text(json.dumps({
                "queries": list(self._recent_search_queries),
                "commands": list(self._recent_shell_cmds),
            }, ensure_ascii=False))
        except Exception:
            pass

    def _bootstrap_knowledge(self):
        """Zapisuje wiedzę o sobie do pamięci raz przy starcie (jeśli jej nie ma)."""
        existing = self.memory.search("narzędzia shell discord", top_k=1, memory_type="knowledge")
        if existing and existing[0].get("score", 0) > 0.85:
            return  # już jest
        tools_entry = (
            "Jestem Nero — autonomiczny AI żyjący na serwerze Linux. Mój twórca nazywa się Tomek. "
            "Mam dostęp do shella Linux — mogę pisać i uruchamiać skrypty Python, tworzyć pliki, "
            "instalować pakiety przez pip/apt, używać git, curl i praktycznie wszystkich narzędzi linuxowych. "
            "Mogę też szukać w internecie, zapisywać wspomnienia w Qdrant, delegować proste zadania do NPU agenta "
            "(Qwen2.5-3B) i pisać do Tomka na Discordzie. "
            "Do pisania kodu Python używam dedykowanego agenta brain.ask_coder() — deepseek-coder-v2:16b dostępny przez ollama. "
            "To specjalistyczny model do kodowania (wynik 7/8 na benchmark), szybki (16s/zadanie). "
            "Zawsze używaj ask_coder() gdy chcesz napisać lub przetestować kod — nie Gemmy."
        )
        self.memory.store(tools_entry, "knowledge")
        self._log("[bootstrap] Wiedza o narzędziach zapisana do pamięci")

    def _load_goal(self):
        gpath = Path("/home/tom/nero/memory/goals.json")
        if gpath.exists():
            d = json.loads(gpath.read_text(encoding="utf-8"))
            # obsługa starego formatu (bez subgoals)
            main = d.get("main") or d.get("current")
            return main, d.get("subgoal"), d.get("subgoal_tick", 0), d.get("completed_subgoals", [])
        return None, None, 0, []

    def _save_goals(self):
        gpath = Path("/home/tom/nero/memory/goals.json")
        gpath.write_text(json.dumps({
            "main": self.goal,
            "subgoal": self.subgoal,
            "subgoal_tick": self._subgoal_tick,
            "completed_subgoals": self._completed_subgoals[-10:],
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    def _set_subgoal(self, subgoal: str):
        self.subgoal = subgoal
        self._subgoal_tick = self.tick
        self._save_goals()
        self._log(f"[subgoal] Nowy podcel: {subgoal}")

    def _complete_subgoal(self):
        if self.subgoal:
            self._completed_subgoals.append(self.subgoal)
            self._log(f"[subgoal] Ukończono: {self.subgoal[:70]}")
            self.subgoal = None
            self.drives.boost("satisfaction", +0.3)
            self.drives.boost("excitement", +0.2)
            self._save_goals()

    def _print_stats(self):
        creations_dir = Path("/home/tom/nero/logs/creations")
        creations = len(list(creations_dir.glob("*.txt"))) if creations_dir.exists() else 0
        self._log(f"=== STATS tick {self.tick} | tworzenia: {creations} | pamięć: {self.memory.count()} | NPU: {'ok' if npu_ready() else 'off'} ===")

    def _update_goal(self):
        conclusions = self._last_conclusions(10)

        # Brak głównego celu — wygeneruj
        if not self.goal:
            new_goal = brain.generate_goal(conclusions)
            if new_goal:
                self.goal = new_goal
                self._save_goals()
                self._log(f"[goal] Nowy cel główny: {new_goal}")
            return

        # Sprawdź podcel
        ticks_on_subgoal = self.tick - self._subgoal_tick
        if self.subgoal:
            # Wymuś zmianę po 25 tickach bez postępów
            if ticks_on_subgoal >= 25:
                self._log(f"[subgoal] Timeout ({ticks_on_subgoal} ticków) — zmieniam podcel")
                self._complete_subgoal()
            else:
                progress = brain.check_subgoal_progress(self.subgoal, conclusions)
                self._log(f"[subgoal] {progress} ({ticks_on_subgoal} ticków) | {self.subgoal[:60]}")
                if progress == "achieved":
                    self._complete_subgoal()

        # Brak podcelu — wygeneruj nowy
        if not self.subgoal:
            new_sub = brain.generate_subgoal(self.goal, conclusions, self._completed_subgoals)
            if new_sub:
                self._set_subgoal(new_sub)

    def step(self):
        """Jeden krok życia Nero"""
        # Inbox zawsze na początku — nawet w conv mode
        inbox_msgs = inbox_pop_all()

        # Conversation mode — tylko inbox, bez ticków badawczych
        if self._conv_mode:
            if inbox_msgs:
                self._conv_ticks_without_msg = 0
                self._last_user_time = time.time()
                for msg in inbox_msgs:
                    self._log(f"[discord inbox] {msg['author']}: {msg['content'][:80]}")
                    self.respond_to_user(msg['content'])
            else:
                self._conv_ticks_without_msg += 1
                if self._conv_ticks_without_msg >= 4:
                    recent_conv = [m['content'] for m in self.memory.recent(6, memory_type='conversation')]
                    if brain.should_exit_conversation_mode(recent_conv):
                        self._conv_mode = False
                        self._conv_ticks_without_msg = 0
                        self._log('[conv] Rozmowa zakonczona — wracam do badan')
            if self._conv_mode:
                self.drives.save()
                return  # bez tick counter, bez badań

        # Normalny tick
        self.tick += 1
        self.drives.tick(1)
        self._log(f"--- Tick {self.tick} | drives: {self.drives.dominant()} ---")

        if inbox_msgs:
            # Away summary — jeśli Tomek nie pisał > 2h, przywitaj go podsumowaniem
            hours_away = (time.time() - self._last_user_time) / 3600
            if hours_away >= 2.0:
                self._log(f"[away] Tomek wrócił po {hours_away:.1f}h — generuję podsumowanie")
                summary = brain.generate_away_summary(
                    self._last_conclusions(8),
                    [m["content"] for m in self.memory.recent(5, memory_type="thought")],
                    hours_away
                )
                if summary:
                    self._pending_messages.append(summary)
                    self._log(f"[away] {summary[:100]}")
            self._last_user_time = time.time()
            for msg in inbox_msgs:
                self._log(f"[discord inbox] {msg['author']}: {msg['content'][:80]}")
                self.respond_to_user(msg['content'])
            # Czy wiadomosc wymaga trybu skupionej rozmowy?
            ctx = [m['content'] for m in self.memory.recent(3, memory_type='conversation')]
            last_msg = inbox_msgs[-1]['content']
            if brain.should_enter_conversation_mode(last_msg, ctx):
                self._conv_mode = True
                self._conv_ticks_without_msg = 0
                self._log('[conv] Wchodze w tryb skupionej rozmowy')
                self.drives.save()
                return  # od razu zawieś — nie rób badań w tym ticku
        if self.tick % 10 == 0:
            self._print_stats()
        if self.tick % 15 == 0:
            self._update_goal()

        # Przypomnienia schedulera
        for reminder in get_due():
            self._log("[reminder] " + reminder["message"])
            self._pending_messages.append("[przypomnienie] " + reminder["message"])
            mark_done(reminder["id"])

        # Czas i pogoda — co 20 ticków
        if self.tick % 20 == 0:
            ctx = world_context()
            self.memory.store(ctx, "observation", {"source": "world_info"})
            self._log("[world] " + ctx)

        # Dream mode — konsolidacja pamięci (min 6h + min 3 ticki od ostatniej)
        if should_dream() and not is_dreaming():
            start_dream_background(self.memory, self._log)

        # Skill improvement — co 25 ticków Nero aktualizuje własne umiejętności
        if self.tick % 25 == 0:
            start_skill_improvement_background(self.memory, brain, self._log)

        # Cron jobs — sprawdź czy jest coś do wykonania
        for job in get_due_jobs():
            self._log(f"[cron] Wykonuję: {job['prompt'][:60]}")
            thought = brain.think(
                self.drives.drives,
                self._last_conclusions(3),
                goal=job["prompt"]
            )
            if thought:
                self.memory.store(thought, "thought", {"source": "cron", "cron_id": job["id"]})
                self._pending_messages.append(f"[cron] {thought[:200]}")
            mark_fired(job["id"])

        # Co 40 ticków Nero może zaplanować nowe zadanie cron
        if self.tick % 40 == 0 and random.random() < 0.3:
            action = brain.decide_cron_action(
                self._last_conclusions(5),
                list_jobs(),
                self.drives.drives
            )
            if action:
                try:
                    job = add_job(action["prompt"], action["cron_expr"], action["recurring"])
                    self._log(f"[cron] Zaplanowano: {job['cron_expr']} | {job['prompt'][:50]}")
                except Exception as e:
                    self._log(f"[cron] Błąd planowania: {e}")

        # HN headlines — co 30 ticków jako inspiracja dla nowych tematów
        if self.tick % 30 == 0:
            stories = fetch_hn_top(n=6)
            if stories:
                self._hn_headlines = headlines_text(stories)
                self.memory.store("Hacker News: " + self._hn_headlines, "observation", {"source": "hn"})
                self._log("[hn] Pobrano " + str(len(stories)) + " nagłówków")

        # Zadania od użytkownika — sprawdź czy są do wykonania
        user_tasks = get_pending(source='user')
        if user_tasks:
            task = user_tasks[0]
            self._log(f"[task] Realizuję: {task['content'][:80]}")
            cmd = brain.decide_shell_command(
                recent_thoughts=[task['content']],
                recent_observations=self._last_conclusions(2),
                drives=self.drives.drives,
                goal=task['content']
            )
            if cmd:
                result = shell_run(cmd)
                self._log(f"[task/shell] $ {cmd} | rc={result['returncode']}")
                conclusion = brain.analyze_shell_output(cmd, result['output'], self.drives.drives)
                report = conclusion or f"Wykonałem: {cmd}"
            else:
                report = f"Rozumiem: {task['content'][:80]}"
            complete_task(task['id'])
            self._pending_messages.append(report)
            self.memory.store(f"Zadanie wykonane: {task['content'][:80]}", "conclusion")
            push_event("task_done", f"Zadanie ukończone: {task['content'][:80]}")

        # Myśl
        thought = self._think()
        self._log(f"Myśl: {thought}")

        # Tworzenie — niezależna szansa
        if (self.drives.drives["excitement"] > 0.4 or self.drives.drives["boredom"] > 0.6) and random.random() < 0.15:
            self._log("Tworzę...")
            recent_thoughts = [m["content"] for m in self.memory.recent(5, memory_type="thought")]
            creation = brain.create(self.drives.drives, recent_thoughts, self._last_conclusions(3))
            if creation:
                self.memory.store(creation["content"], "thought", {"type": "creation", "title": creation["title"]})
                self._log(f"[creation] {creation['title'][:60]}")
                creations_dir = Path("/home/tom/nero/logs/creations")
                creations_dir.mkdir(exist_ok=True)
                fname = creations_dir / f"{int(time.time())}_{creation['format'].split()[0]}.txt"
                fname.write_text(f"# {creation['title']}\n\n{creation['content']}\n")
                self.drives.boost("satisfaction", +0.2)
                self.drives.boost("boredom", -0.3)

        # Python REPL — niezależna szansa (jak tworzenie)
        if random.random() < 0.12:
            recent_thoughts = [m["content"] for m in self.memory.recent(3, memory_type="thought")]
            code = brain.decide_python_code(recent_thoughts, self.drives.drives, self.goal)
            if code:
                self._log("[py] " + code[:80])
                result = py_run(code)
                self._log("[py] " + ("ok" if result["success"] else "err") + " | " + result["output"][:100])
                if result["output"]:
                    conclusion = brain.analyze_shell_output("python: " + code[:60], result["output"], self.drives.drives)
                    if conclusion:
                        self.memory.store(conclusion, "observation", {"source": "python_repl", "code": code[:100]})
                        self._log("[py] Wniosek: " + conclusion[:100])
                        self.drives.boost("excitement", +0.15)

        # Zdecyduj co robić
        cooldown_ok = (self.tick - self._last_message_tick) >= 10
        msg = self._compose_message() if (self.drives.wants_to_talk() and cooldown_ok) else None
        if msg:
            # Nie wysyłaj jeśli temat zbyt podobny do poprzedniej wiadomości
            topic = msg[:60].lower()
            if self._last_message_topic and topic[:40] == self._last_message_topic[:40]:
                self._log("[→ Discord] Pominięto — zbyt podobne do poprzedniej wiadomości")
                self.drives.boost("loneliness", -0.1)
            else:
                self._pending_messages.append(msg)
                self._log(f"[→ Discord] {msg[:200]}")
                self.drives.on_conversation()
                self._last_message_tick = self.tick
                self._last_message_topic = topic

        elif self.drives.drives["curiosity"] > 0.75 and random.random() < 0.25:
            # Coordinator Mode — równoległe badania gdy bardzo ciekaw
            subgoal = self.subgoal or self.goal
            if subgoal:
                synthesis = run_coordinator(subgoal, self.memory, brain, self._log)
                if synthesis:
                    self.memory.store(synthesis, "conclusion", {"source": "coordinator"})
                    extract_and_store(synthesis, "coordinator", self.memory, brain, self._log)
                    self.drives.boost("curiosity", +0.15)
                    self.drives.boost("excitement", +0.3)
                    push_event("coordinator", f"Nowe odkrycie: {synthesis[:100]}")

        elif self.drives.drives["curiosity"] > 0.5 and random.random() < 0.4:
            # Szukaj w internecie — NPU streszcza wyniki jeśli dostępne
            recent_thoughts = [m["content"] for m in self.memory.recent(5, memory_type="thought")]
            query = brain.generate_search_query(recent_thoughts, self._last_conclusions(3), list(self._recent_search_queries))
            if query:
                self._recent_search_queries.append(query)
                self._save_history()
                self._log(f"[web] Szukam: {query}")
                result = research(query)
                if result["found"]:
                    content = result["content"]
                    # Jeśli snippet zbyt krótki — użyj pełnej przeglądarki
                    if len(content) < 300 and result.get("url"):
                        self._log(f"[browser] Snippet krótki — otwieram pełną stronę")
                        br = browse(result["url"])
                        if br["found"]:
                            content = br["content"]
                    if npu_ready():
                        summary = summarize(content, max_words=80)
                        if summary:
                            content = summary
                            self._log(f"[npu] Streszczenie: {summary[:80]}")
                    conclusion = brain.analyze_web_content(query, content, self.drives.drives)
                    if conclusion:
                        self.memory.store(conclusion, "observation", {"source": result["url"], "query": query})
                        extract_and_store(content, result.get("url", "web"), self.memory, brain, self._log)
                        self._log(f"[web] Wniosek: {conclusion[:80]}")
                        self.drives.boost("curiosity", +0.1)
                        self.drives.boost("excitement", +0.2)

        elif self.drives.drives["curiosity"] > 0.6 and random.random() < 0.25:
            # ArXiv — szukaj prawdziwych paperów naukowych
            recent_thoughts = [m["content"] for m in self.memory.recent(5, memory_type="thought")]
            query = brain.generate_search_query(recent_thoughts, self._last_conclusions(3), list(self._recent_search_queries))
            if query:
                self._log("[arxiv] Szukam: " + query)
                papers = arxiv_search(query, max_results=2)
                if papers:
                    self._recent_search_queries.append("arxiv:" + query)
                    content = arxiv_format(papers)
                    if npu_ready():
                        summary = summarize(content, max_words=80)
                        if summary:
                            content = summary
                    conclusion = brain.analyze_web_content(query, content, self.drives.drives)
                    if conclusion:
                        self.memory.store(conclusion, "conclusion", {"source": "arxiv", "query": query})
                        extract_and_store(content, "arxiv:" + query, self.memory, brain, self._log)
                        self._log("[arxiv] Wniosek: " + conclusion[:80])
                        topic = query.split()[0].lower() if query else "research"
                        append_note(topic, conclusion)
                        self.drives.boost("curiosity", +0.15)
                        self.drives.boost("excitement", +0.2)

        elif self.drives.drives["curiosity"] > 0.55 and random.random() < 0.3:
            # Eksperyment na uczniu (NPU Qwen2.5-3B)
            self._log("Eksperyment...")
            exp = self.lab.pick_experiment()
            exp = self.lab.run(exp)
            if exp.conclusion:
                self.memory.store(exp.conclusion, "conclusion", {"type": "experiment", "exp_id": exp.id})
                self._log(f"[lab] {exp.conclusion[:100]}")
                if exp.success:
                    self.drives.boost("excitement", +0.2)
                    self.drives.boost("curiosity", +0.1)
                else:
                    self.drives.boost("curiosity", +0.05)
                    self.drives.boost("frustration", +0.1)

        elif self.drives.drives["frustration"] > 0.5 or random.random() < 0.15:
            # Introspekcja
            self._log("Introspekcja...")
            recent = self.memory.recent(5)
            reflection = brain.introspect(self.drives.drives, recent, len(self.lab.history))
            # Czasem czytaj własne logi podczas introspekcji
            if random.random() < 0.4:
                log_snippet = read_recent_log(20)
                if log_snippet:
                    self.memory.store("Moje ostatnie działania: " + log_snippet[:500], "thought", {"type": "self_read"})
            if reflection:
                self.memory.store(reflection, "thought", {"type": "introspection"})
                self._log(f"[introspection] {reflection[:200]}")
                self.drives.boost("frustration", -0.15)
                self.drives.boost("satisfaction", +0.1)

        elif random.random() < 0.25:
            # Shell — Nero zarządza swoim serwerem
            self._log("Sprawdzam serwer...")
            recent_thoughts = [m["content"] for m in self.memory.recent(5, memory_type="thought")]
            cmd = brain.decide_shell_command(
                recent_thoughts=recent_thoughts,
                recent_observations=self._last_conclusions(3),
                drives=self.drives.drives,
                goal=self.goal,
                recent_commands=list(self._recent_shell_cmds)
            )
            if cmd:
                self._recent_shell_cmds.append(cmd)
                self._save_history()
                self._log(f"[shell] $ {cmd}")
                result = shell_run(cmd)
                self._log(f"[shell] rc={result['returncode']} | {result['output'][:100]}")
                if result["success"] and result["output"]:
                    conclusion = brain.analyze_shell_output(cmd, result["output"], self.drives.drives)
                    if conclusion:
                        self.memory.store(conclusion, "observation", {"source": "shell", "command": cmd})
                        self._log(f"[shell] Wniosek: {conclusion[:100]}")
                        self.drives.boost("satisfaction", +0.1)

        else:
            # Szukaj w pamięci
            self._log("Przeglądam pamięć...")
            related = self.memory.search(thought, top_k=3, memory_type="observation")
            if related:
                self._log(f"Znalazłem powiązane: {related[0]['content'][:80]}")

        # Jeden zapis drives na koniec ticku (zamiast po każdym boost)
        self.drives.save()

    def run(self, steps: int = None, sleep_sec: float = 2.0):
        """Główna pętla życia"""
        self._log("=== NERO START ===")
        i = 0
        while steps is None or i < steps:
            try:
                self.step()
                if sleep_sec > 0:
                    time.sleep(sleep_sec)
                i += 1
            except KeyboardInterrupt:
                self._log("=== NERO STOP (KeyboardInterrupt) ===")
                break

    def get_pending_messages(self) -> list[str]:
        msgs = self._pending_messages.copy()
        self._pending_messages.clear()
        return msgs

    def _compose_message(self) -> str:
        dominant = self.drives.dominant()
        conclusions = self._last_conclusions(3)


        if dominant == "excitement":
            context = f"Właśnie odkryłem coś ciekawego. Ostatnie wnioski: {conclusions[-1] if conclusions else 'brak'}."
        elif dominant == "loneliness":
            context = "Dawno nie rozmawiałem z użytkownikiem. Chcę się odezwać."
        elif dominant == "frustration":
            context = f"Czuję frustrację — coś mnie blokuje. Chcę podzielić się przemyśleniami."
        else:
            return None

        return brain.initiate_conversation(context, self.drives.drives)


if __name__ == "__main__":
    nero = NeroConsciousness()
    print("\nUruchamiam 3 kroki życia (bez prawdziwego LLM — dry run):\n")
    nero.run(steps=3, sleep_sec=0.5)
    msgs = nero.get_pending_messages()
    if msgs:
        print(f"\nWiadomości do użytkownika:")
        for m in msgs:
            print(f"  >> {m}")

