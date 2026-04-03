#!/bin/bash
# load_lora.sh — pobiera adapter z Google Drive i restartuje Nero z LoRA
# Użycie: ./load_lora.sh <ścieżka_do_adaptera.gguf>
# Lub automatycznie z cron: ./load_lora.sh (szuka najnowszego pliku w ~/nero/lora/)

LORA_DIR="/home/tom/nero/lora"
BRAIN_PY="/home/tom/nero/core/brain.py"

if [ -n "$1" ]; then
    ADAPTER="$1"
else
    # Znajdź najnowszy adapter
    ADAPTER=$(ls -t "$LORA_DIR"/*.gguf 2>/dev/null | head -1)
fi

if [ -z "$ADAPTER" ] || [ ! -f "$ADAPTER" ]; then
    echo "[lora] Nie znaleziono adaptera GGUF w $LORA_DIR"
    echo "[lora] Wgraj plik .gguf z Colaba i uruchom ponownie"
    exit 1
fi

echo "[lora] Używam adaptera: $ADAPTER"

# Zaktualizuj brain.py — dodaj --lora do komendy llama-server
if grep -q "\-\-lora" "$BRAIN_PY"; then
    # Podmień istniejący --lora
    sed -i "s|\"--lora\", \".*\"|\"--lora\", \"$ADAPTER\"|g" "$BRAIN_PY"
else
    # Dodaj --lora po parametrach
    sed -i "s|\"-c\", \"4096\",|\"-c\", \"4096\", \"--lora\", \"$ADAPTER\",|" "$BRAIN_PY"
fi

echo "[lora] Adapter skonfigurowany w brain.py"

# Restart Nero
sudo systemctl restart nero
echo "[lora] Nero restartuje z nową LoRA: $(basename $ADAPTER)"
echo "[lora] Sprawdź logi: tail -f /home/tom/nero/logs/nero_out.log"
