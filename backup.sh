#!/bin/bash
# Nero backup — kod, pamięć, notatki, drives
BACKUP_DIR="/home/tom/nero_backups"
DATE=$(date +%Y-%m-%d_%H-%M)
DEST="$BACKUP_DIR/$DATE"

mkdir -p "$DEST"

# Kod (core, lab, tools, comms, memory python files)
rsync -a --include="*.py" --include="*/" --exclude="*" \
    /home/tom/nero/ "$DEST/code/" 2>/dev/null

# Stan pamięci i konfiguracja
cp -r /home/tom/nero/memory/drives.json \
      /home/tom/nero/memory/goals.json \
      /home/tom/nero/memory/action_history.json \
      /home/tom/nero/memory/tasks.json \
      "$DEST/" 2>/dev/null

# Notatnik i tworzenia
cp -r /home/tom/nero/notes/ "$DEST/notes/" 2>/dev/null
cp -r /home/tom/nero/logs/creations/ "$DEST/creations/" 2>/dev/null

# Research journal
cp /home/tom/nero/logs/research_journal.jsonl "$DEST/" 2>/dev/null

# Qdrant snapshot
curl -s -X POST "http://localhost:6333/collections/nero_memory/snapshots" \
    -o "$DEST/qdrant_snapshot_info.json" 2>/dev/null

# Usuń backupy starsze niż 7 dni (zostaw max 7)
ls -t "$BACKUP_DIR" | tail -n +8 | xargs -I{} rm -rf "$BACKUP_DIR/{}" 2>/dev/null

# Kopia na maszynę lucek (192.168.0.13)
rsync -a --delete "$BACKUP_DIR/" lucek@192.168.0.13:/home/lucek/nero_backups/ 2>/dev/null \
    && echo "[backup] Kopia na 192.168.0.13 — OK" \
    || echo "[backup] Kopia na 192.168.0.13 — BLAD"
