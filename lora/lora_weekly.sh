#!/bin/bash
# lora_weekly.sh — cotygodniowy eksport datasetu i upload na Google Drive
# Cron: 0 2 * * 0 (niedziela 2:00 w nocy)

LOG="/home/tom/nero/logs/lora_export.log"
NERO_DIR="/home/tom/nero"
DATASET="$NERO_DIR/lora/dataset.jsonl"
VENV="$NERO_DIR/venv/bin/python"

echo "[$(date)] === Cotygodniowy eksport LoRA ===" >> $LOG

# 1. Eksportuj dataset z Qdrant
echo "[$(date)] Eksportuję dataset..." >> $LOG
cd $NERO_DIR && $VENV tools/export_lora_dataset.py >> $LOG 2>&1

if [ ! -f "$DATASET" ]; then
    echo "[$(date)] BŁĄD: brak dataset.jsonl" >> $LOG
    exit 1
fi

LINES=$(wc -l < "$DATASET")
echo "[$(date)] Dataset: $LINES par treningowych" >> $LOG

# 2. Wgraj na Google Drive
echo "[$(date)] Wgrywam na Google Drive..." >> $LOG
rclone copy "$DATASET" gdrive:Nero/ >> $LOG 2>&1
rclone copy "$NERO_DIR/lora/nero_lora_colab.ipynb" gdrive:Nero/ >> $LOG 2>&1

echo "[$(date)] Gotowe! Otwórz Colab: https://colab.research.google.com" >> $LOG
echo "[$(date)] Plik: gdrive:Nero/dataset.jsonl ($LINES par)" >> $LOG
