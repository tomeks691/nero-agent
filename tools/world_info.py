"""
World Info — czas, data, pogoda via wttr.in (darmowe, bez klucza).
"""
import urllib.request
import urllib.parse
import json
from datetime import datetime

DAYS_PL = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]

def current_time() -> str:
    now = datetime.now()
    return f"{DAYS_PL[now.weekday()]}, {now.strftime('%d.%m.%Y %H:%M')}"

def get_weather(city: str = "Białystok") -> str | None:
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        c = data["current_condition"][0]
        return f"{city}: {c['temp_C']}°C, {c['weatherDesc'][0]['value']}, odczuwalne {c['FeelsLikeC']}°C"
    except Exception:
        return None

def world_context(city: str = "Białystok") -> str:
    parts = [f"Teraz: {current_time()}"]
    w = get_weather(city)
    if w:
        parts.append(f"Pogoda — {w}")
    return "\n".join(parts)
