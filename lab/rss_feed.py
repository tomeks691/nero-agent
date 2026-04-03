"""
Nero RSS/HackerNews — autonomiczne odkrywanie nowych tematów.
HN API: darmowe, bez klucza.
"""
import urllib.request
import json

HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

def fetch_hn_top(n: int = 8) -> list[dict]:
    try:
        with urllib.request.urlopen(HN_TOP_URL, timeout=10) as r:
            ids = json.loads(r.read())[:n * 3]
        stories = []
        for id_ in ids:
            if len(stories) >= n:
                break
            try:
                with urllib.request.urlopen(HN_ITEM_URL.format(id_), timeout=5) as r:
                    item = json.loads(r.read())
                if item.get("type") == "story" and item.get("title"):
                    stories.append({
                        "title": item["title"],
                        "url": item.get("url", ""),
                        "score": item.get("score", 0),
                    })
            except Exception:
                continue
        return stories
    except Exception as e:
        print(f"[rss] HN error: {e}")
        return []

def headlines_text(stories: list[dict]) -> str:
    if not stories:
        return ""
    return "\n".join(f"- {s['title']} (score:{s['score']})" for s in stories)
