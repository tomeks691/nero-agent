"""
Nero — główny entry point
"""

import os, sys, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
sys.path.insert(0, "/home/tom/nero")

from core.consciousness import NeroConsciousness
from comms.discord_bot import start_bot_background, send_message_sync, push_event
from comms.npu_agent import start_npu_server, stop_npu_server
import core.brain as brain

TICK_INTERVAL = 30.0

def main():
    print("=" * 50)
    print("  NERO — starting up")
    print("=" * 50)

    print("[nero] Startuję mózg (llama-server)...")
    brain.start_server()
    start_npu_server()
    time.sleep(5)  # poczekaj aż modele się załadują

    nero = NeroConsciousness()

    token = os.environ.get("NERO_DISCORD_TOKEN", "")
    discord_ok = token and not token.startswith("tu_wklej")
    if discord_ok:
        start_bot_background()
        time.sleep(3)
    else:
        print("[nero] Discord wyłączony — brak tokena")

    print(f"[nero] Pętla życia startuje (tick co {TICK_INTERVAL}s)\n")

    while True:
        try:
            nero.step()
            for msg in nero.get_pending_messages():
                if discord_ok:
                    send_message_sync(msg)
                else:
                    print(f"[→ User] {msg}")
        except KeyboardInterrupt:
            print("\n[nero] Shutdown.")
            brain.stop_server()
            stop_npu_server()
            break
        except Exception as e:
            import traceback
            print(f"[nero] BLAD w step(): {e}")
            traceback.print_exc()
            if discord_ok:
                push_event("error", f"Błąd w step(): {str(e)[:120]}")
        time.sleep(TICK_INTERVAL)

if __name__ == "__main__":
    main()
