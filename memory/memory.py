"""
Nero Memory — RAG z Qdrant + fastembed (bez torch, ~50MB RAM)
"""

import uuid
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

COLLECTION  = "nero_memory"
VECTOR_SIZE = 384

MEMORY_TYPES = ["thought", "experiment", "conclusion", "conversation", "hypothesis", "observation", "introspection", "knowledge", "task"]


class NeroMemory:
    def __init__(self, path="/home/tom/nero/memory/qdrant"):
        from fastembed import TextEmbedding
        self.client  = QdrantClient(path=path)
        self.encoder = TextEmbedding("BAAI/bge-small-en-v1.5")
        self._ensure_collection()

    def _ensure_collection(self):
        existing = [c.name for c in self.client.get_collections().collections]
        if COLLECTION not in existing:
            self.client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
            )
            print(f"[memory] Kolekcja '{COLLECTION}' utworzona")
        else:
            count = self.client.count(COLLECTION).count
            print(f"[memory] Kolekcja '{COLLECTION}' załadowana ({count} wspomnień)")

    def _embed(self, text: str) -> list[float]:
        return list(self.encoder.embed([text]))[0].tolist()

    def store(self, content: str, memory_type: str = "thought", metadata: dict = None, drives: dict = None):
        assert memory_type in MEMORY_TYPES, f"Nieznany typ: {memory_type}"
        # Waga emocjonalna — silne drives = ważniejsze wspomnienie
        emotion_weight = 0.5  # default
        if drives:
            emotion_weight = min(1.0, (
                drives.get("excitement", 0) * 0.4 +
                drives.get("curiosity", 0) * 0.3 +
                drives.get("satisfaction", 0) * 0.2 +
                drives.get("frustration", 0) * 0.1
            ))
        payload = {
            "content": content,
            "type": memory_type,
            "timestamp": datetime.now().isoformat(),
            "emotion_weight": round(emotion_weight, 3),
            "access_count": 0,
            "last_accessed": datetime.now().isoformat(),
            **(metadata or {})
        }
        self.client.upsert(
            collection_name=COLLECTION,
            points=[PointStruct(id=str(uuid.uuid4()), vector=self._embed(content), payload=payload)]
        )

    def search(self, query: str, top_k: int = 5, memory_type: str = None) -> list[dict]:
        f = None
        if memory_type:
            f = Filter(must=[FieldCondition(key="type", match=MatchValue(value=memory_type))])
        results = self.client.query_points(
            collection_name=COLLECTION, query=self._embed(query), limit=top_k, query_filter=f
        ).points
        return [{"score": r.score, **r.payload} for r in results]

    def recent(self, n: int = 10, memory_type: str = None) -> list[dict]:
        f = None
        if memory_type:
            f = Filter(must=[FieldCondition(key="type", match=MatchValue(value=memory_type))])
        results, _ = self.client.scroll(collection_name=COLLECTION, scroll_filter=f, limit=n, with_payload=True)
        memories = [r.payload for r in results]
        memories.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return memories[:n]

    def emotional_search(self, query: str, top_k: int = 5, drives: dict = None) -> list[dict]:
        """Wyszukiwanie z uwzględnieniem wagi emocjonalnej — intensywne drives = priorytet emocjonalnych wspomnień."""
        results = self.search(query, top_k=top_k * 2)
        if not drives:
            return results[:top_k]
        intensity = max(drives.values()) if drives else 0.5
        # Rerank: score = semantic_score * (1 + emotion_weight * intensity)
        for r in results:
            ew = r.get("emotion_weight", 0.5)
            r["_reranked"] = r["score"] * (1 + ew * intensity)
        results.sort(key=lambda x: x["_reranked"], reverse=True)
        return results[:top_k]

    def decay_old_memories(self, days_threshold: int = 7):
        """Obniż wagę emocjonalną starych wspomnień które nie były przywoływane."""
        from datetime import timedelta
        import time as _time
        cutoff = (datetime.now() - timedelta(days=days_threshold)).isoformat()
        try:
            results, _ = self.client.scroll(
                collection_name=COLLECTION, limit=500,
                with_payload=True, with_vectors=False
            )
            to_update = []
            for r in results:
                last = r.payload.get("last_accessed", r.payload.get("timestamp", ""))
                ew = r.payload.get("emotion_weight", 0.5)
                if last < cutoff and ew > 0.1:
                    to_update.append((str(r.id), round(ew * 0.85, 3)))
            for point_id, new_weight in to_update:
                self.client.set_payload(
                    collection_name=COLLECTION,
                    payload={"emotion_weight": new_weight},
                    points=[point_id]
                )
            if to_update:
                print(f"[memory] Decay: obniżono wagę {len(to_update)} starych wspomnień")
        except Exception as e:
            print(f"[memory] Decay error: {e}")

    def count(self) -> int:
        return self.client.count(COLLECTION).count

    def scroll_with_ids(self, memory_type: str = None, limit: int = 100) -> list[dict]:
        """Zwraca wspomnienia z ID — potrzebne do dream agent (usuwanie)."""
        f = None
        if memory_type:
            f = Filter(must=[FieldCondition(key="type", match=MatchValue(value=memory_type))])
        results, _ = self.client.scroll(
            collection_name=COLLECTION, scroll_filter=f, limit=limit,
            with_payload=True, with_vectors=False
        )
        items = [{"id": str(r.id), **r.payload} for r in results]
        items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return items

    def delete(self, ids: list[str]):
        """Usuń wspomnienia po ID."""
        from qdrant_client.models import PointIdsList
        self.client.delete(collection_name=COLLECTION, points_selector=PointIdsList(points=ids))


if __name__ == "__main__":
    mem = NeroMemory()
    mem.store("Hipoteza: przykład przed pytaniem poprawia odpowiedź", "hypothesis")
    mem.store("Uczeń nie odpowiedział na proste pytanie", "experiment")
    print(f"Wspomnień: {mem.count()}")
    for m in mem.search("przykład pytanie", top_k=2):
        print(f"  [{m['score']:.2f}] {m['content'][:60]}")
