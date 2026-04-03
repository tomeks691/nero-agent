# Nero — Narzedzia i mozliwosci

## Narzedzia do badan
- web_search(query) — szuka w DuckDuckGo, zwraca snippet + URL
- browse(url) — Puppeteer (Node.js), pobiera pelna tresc strony; uzywaj gdy snippet < 300 znakow
- arxiv_search(query) — szuka paperow naukowych na arxiv.org
- run_coordinator(goal) — 3 rownolegle workery (web + arxiv + pamiec), Gemma syntetyzuje; uzywaj gdy curiosity > 0.75

## Narzedzia do pamieci
- memory.store(content, type, meta) — zapisz wspomnienie; typy: observation, conclusion, knowledge, hypothesis
- memory.search(query, top_k) — semantyczne wyszukiwanie w Qdrant
- memory.recent(n, memory_type) — ostatnie N wspomnien danego typu
- extract_and_store(text, source) — deepseek wyciaga 3-5 faktow z tekstu i zapisuje jako knowledge

## Narzedzia do zadan
- Shell: uruchamiaj polecenia przez action shell
- Python REPL: uruchamiaj kod przez action python
- add_job(prompt, cron_expr, recurring) — zaplanuj zadanie cronowe; np. cron_expr="0 9 * * *" = codz. o 9:00
- list_jobs() — lista zaplanowanych zadan
- delete_job(id) — usun zadanie cronowe

## Komunikacja z Tomkiem
- push_event(type, msg) — natychmiastowe powiadomienie Discord bez czekania na drive
  - typy: task_done, error, discovery, dream_done, skill_update, coordinator, info
- Wiadomosci z Discord trafiaja do inbox — Nero odpowiada w kolejnym ticku

## Wazne limity
- Gemma (glowny model): duze prompty dziel na czesci
- deepseek-coder: szybszy, uzywaj do ekstrakcji faktow i analizy kodu
- Browser timeout: 25s — nie browseuj ciezkich stron
- Coordinator timeout: 90s — uruchamiaj tylko dla waznych badan, koszt = 3 wątki
