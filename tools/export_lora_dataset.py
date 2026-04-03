"""
Nero LoRA Dataset Exporter
Eksportuje najlepsze wspomnienia z Qdrant do formatu JSONL do treningu LoRA.
Uruchamiaj raz w tygodniu przed wysłaniem na Colab.
"""
import sys, json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/home/tom/nero")

from memory.memory import NeroMemory

OUTPUT_FILE = Path("/home/tom/nero/lora/dataset.jsonl")
MIN_EMOTION_WEIGHT = 0.0
MAX_SAMPLES = 600

SYSTEM_PROMPT = (
    "Jesteś Nero — autonomiczny AI żyjący na serwerze Linux. "
    "Masz własne drives (curiosity, satisfaction, excitement), pamięć i cele. "
    "Myślisz po polsku, jesteś ciekawy świata i siebie. "
    "Odpowiadasz konkretnie i szczerze."
)

def build_pairs(memory: NeroMemory) -> list[dict]:
    pairs = []

    # 1. Pary konwersacyjne — Tomek pyta, Nero odpowiada
    convs = memory.scroll_with_ids(memory_type="conversation", limit=500)
    convs = convs  # zbierz wszystkie
    
    user_msgs = [c for c in convs if c["content"].startswith("Użytkownik:")]
    nero_msgs = {c["timestamp"][:16]: c for c in convs if c["content"].startswith("Nero:")}
    
    for u in user_msgs:
        ts_prefix = u["timestamp"][:16]
        # Szukaj odpowiedzi Nero w oknie ±2 minut
        for nero_ts, nero_msg in nero_msgs.items():
            if abs(len(ts_prefix) - len(nero_ts)) < 3 and nero_ts >= ts_prefix:
                user_text = u["content"].replace("Użytkownik: ", "").strip()
                nero_text = nero_msg["content"].replace("Nero: ", "").strip()
                if len(user_text) > 10 and len(nero_text) > 20:
                    pairs.append({
                        "instruction": user_text,
                        "output": nero_text,
                        "emotion_weight": u.get("emotion_weight", 0.5),
                        "source": "conversation"
                    })
                break

    # 2. Wnioski z badań — wysokoemocjonalne
    conclusions = memory.scroll_with_ids(memory_type="conclusion", limit=400)
    conclusions = conclusions  # zbierz wszystkie
    
    for c in conclusions[:150]:
        pairs.append({
            "instruction": "Co odkryłeś podczas ostatnich badań? Opisz swój wniosek.",
            "output": c["content"].strip(),
            "emotion_weight": c.get("emotion_weight", 0.5),
            "source": "conclusion"
        })

    # 3. Myśli — głębsze i emocjonalne
    thoughts = memory.scroll_with_ids(memory_type="thought", limit=400)
    thoughts = thoughts  # zbierz wszystkie
    
    for t in thoughts[:150]:
        pairs.append({
            "instruction": "Co teraz myślisz? Wyraź swoją aktualną myśl.",
            "output": t["content"].strip(),
            "emotion_weight": t.get("emotion_weight", 0.5),
            "source": "thought"
        })

    # Sortuj po emotion_weight i przytnij
    pairs.sort(key=lambda x: x["emotion_weight"], reverse=True)
    pairs = pairs[:MAX_SAMPLES]
    print(f"[export] Łącznie par: {len(pairs)}")
    print(f"[export] conversation: {sum(1 for p in pairs if p['source']=='conversation')}")
    print(f"[export] conclusion: {sum(1 for p in pairs if p['source']=='conclusion')}")
    print(f"[export] thought: {sum(1 for p in pairs if p['source']=='thought')}")
    return pairs

def export():
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    print("[export] Łączę z Qdrant...")
    memory = NeroMemory()
    
    pairs = build_pairs(memory)
    if not pairs:
        print("[export] Brak danych do eksportu!")
        return

    # Format unsloth/alpaca JSONL
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for p in pairs:
            record = {
                "instruction": p["instruction"],
                "input": "",
                "output": p["output"],
                "system": SYSTEM_PROMPT,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    size_kb = OUTPUT_FILE.stat().st_size // 1024
    print(f"[export] Zapisano {len(pairs)} par → {OUTPUT_FILE} ({size_kb}KB)")
    print(f"[export] Gotowe do wgrania na Google Colab!")

if __name__ == "__main__":
    export()
