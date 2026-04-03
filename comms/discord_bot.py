"""
Nero Discord — bot który sam pisze na kanał
Wiadomości od Tomka trafiają do Redis queue nero:inbox
"""

import asyncio
import discord
import json
import os
import threading
import time
import redis

TOKEN      = os.environ.get("NERO_DISCORD_TOKEN")
CHANNEL_ID = int(os.environ.get("NERO_DISCORD_CHANNEL_ID", "1479520661469790210"))

_bot  = None
_loop = None
_redis = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


def inbox_push(author: str, content: str):
    """Wstaw wiadomość do kolejki Redis."""
    msg = json.dumps({
        "author": author,
        "content": content,
        "ts": time.time(),
        "replied": False,
    })
    _redis.lpush("nero:inbox", msg)


def inbox_pop_all() -> list[dict]:
    """Pobierz wszystkie wiadomości z kolejki i wyczyść."""
    msgs = []
    while True:
        raw = _redis.rpop("nero:inbox")
        if raw is None:
            break
        try:
            msgs.append(json.loads(raw))
        except Exception:
            pass
    return msgs


class NeroBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self._channel = None

    async def on_ready(self):
        print(f"[discord] Nero zalogowany jako {self.user}")
        self._channel = self.get_channel(CHANNEL_ID)
        if self._channel:
            print(f"[discord] Kanał: #{self._channel.name}")
        else:
            print(f"[discord] Nie znaleziono kanału {CHANNEL_ID}")

    async def on_disconnect(self):
        print("[discord] Rozłączono — czekam na reconnect...")

    async def on_resumed(self):
        print("[discord] Reconnect OK")
        self._channel = self.get_channel(CHANNEL_ID)

    async def send(self, text: str):
        if self._channel:
            await self._channel.send(text)
            print(f"[discord] Wysłano: {text[:80]}")

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return
        if message.channel.id != CHANNEL_ID:
            return

        print(f"[discord] {message.author}: {message.content[:80]}")
        inbox_push(str(message.author), message.content)


def start_bot_background():
    global _bot, _loop

    def run():
        global _bot, _loop
        while True:
            try:
                _bot = NeroBot()
                _loop = asyncio.new_event_loop()
                asyncio.set_event_loop(_loop)
                _loop.run_until_complete(_bot.start(TOKEN))
            except Exception as e:
                print(f"[discord] Bot crashed: {e} — restart za 15s")
                try:
                    _loop.close()
                except Exception:
                    pass
                time.sleep(15)

    threading.Thread(target=run, daemon=True).start()
    print("[discord] Bot uruchomiony w tle")


def send_message_sync(text: str):
    if _bot and _loop:
        asyncio.run_coroutine_threadsafe(_bot.send(text), _loop)


# Push notification events — wysyłane natychmiast, niezależnie od drives
PUSH_ICONS = {
    "task_done":    "✅",
    "error":        "⚠️",
    "discovery":    "🔬",
    "dream_done":   "💭",
    "skill_update": "📝",
    "coordinator":  "🔀",
    "low_resources":"⚡",
    "info":         "ℹ️",
}

def push_event(event_type: str, message: str):
    """
    Wyślij natychmiastowe powiadomienie event-driven na Discord.
    event_type: task_done | error | discovery | dream_done | skill_update | coordinator | info
    """
    icon = PUSH_ICONS.get(event_type, "🔔")
    send_message_sync(f"{icon} {message}")
