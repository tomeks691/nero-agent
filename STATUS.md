---
name: Nero AI — status szkieletu
description: Co zostało zbudowane i co dalej
type: project
---

## Szkielet gotowy (2026-03-17)

### Pliki na Sapphire (~/nero/)
- `nero.py` — entry point, spina wszystko
- `core/consciousness.py` — pętla życia, myślenie, decyzje
- `memory/memory.py` — RAG z Qdrant + fastembed (57MB RAM)
- `memory/drives.py` — excitement, curiosity, boredom, loneliness itd.
- `lab/experiment.py` — laboratorium (DRY_RUN=True teraz)
- `comms/discord_bot.py` — pisze na kanał #nero-agent
- `.env` — NERO_DISCORD_TOKEN + NERO_DISCORD_CHANNEL_ID=1479520661469790210

### Co działa
- Nero żyje w pętli co 30s
- Sam eksperymentuje na uczniu (dry-run)
- Pisze na Discord tylko gdy ma powód (excitement>0.7 lub loneliness>0.75)
- Pamięć rośnie z każdym tickiem
- Drives zmieniają się organicznie

### Co jeszcze nie działa
- Nero nie odpowiada na wiadomości od użytkownika (on_message jest ale respond_to_user to placeholder)
- DRY_RUN=True — uczeń nie odpala prawdziwego LLM
- Myśli Nero to szablony, nie prawdziwy LLM

### Następne kroki gdy przyjdzie 96GB RAM
1. Podmień DRY_RUN=False i STUDENT_MODEL na Phi/Mistral
2. Podłącz duży LLM jako mózg Nero (generuje myśli, hipotezy, odpowiedzi)
3. Nero zaczyna naprawdę myśleć i eksperymentować

**Why:** Szkielet gotowy przed przyjściem RAM — Nero ma "dom" gdy większy model wejdzie.
