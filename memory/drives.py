"""
Nero Drives — wewnętrzne stany które napędzają działanie
Zamiast zewnętrznej funkcji nagrody — wewnętrzne "neuroprzekaźniki"
"""

import json
import time
from pathlib import Path
from datetime import datetime

DRIVES_FILE = "/home/tom/nero/memory/drives.json"

DRIVES_CONFIG = {
    # nazwa: (wartość_startowa, decay_per_tick, min, max)
    "curiosity":      (0.7, -0.003, 0.0, 1.0),   # chce eksperymentować i odkrywać
    "boredom":        (0.2, +0.002, 0.0, 1.0),   # rośnie gdy brak nowości, spada gdy odkrywa
    "excitement":     (0.0, -0.005, 0.0, 1.0),    # skacze gdy coś ciekawego, szybko opada
    "loneliness":     (0.1, +0.002, 0.0, 1.0),   # rośnie gdy długo bez rozmowy z użytkownikiem
    "satisfaction":   (0.3, -0.002, 0.0, 1.0),    # rośnie gdy eksperyment się powiódł
    "frustration":    (0.0, -0.002, 0.0, 1.0),   # naturalnie opada, skacze przy porażkach
    "focus":          (0.5, -0.001, 0.0, 1.0),    # koncentracja na bieżącym badaniu
}


class NeroDrives:
    def __init__(self, path=DRIVES_FILE):
        self.path = Path(path)
        self.drives = {}
        self.last_tick = time.time()
        self._load()

    def _load(self):
        if self.path.exists():
            with open(self.path) as f:
                saved = json.load(f)
            self.drives = saved.get("drives", {})
            self.last_tick = saved.get("last_tick", time.time())
            print(f"[drives] Załadowano stan drives")
        else:
            self.drives = {name: cfg[0] for name, cfg in DRIVES_CONFIG.items()}
            self.last_tick = time.time()
            print(f"[drives] Inicjalizacja drives")
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump({
                "drives": self.drives,
                "last_tick": time.time(),
                "updated": datetime.now().isoformat()
            }, f, indent=2)

    def tick(self, ticks: int = 1):
        """Upływ czasu — drives naturalnie się zmieniają"""
        for name, (_, decay, min_val, max_val) in DRIVES_CONFIG.items():
            self.drives[name] = max(min_val, min(max_val, self.drives[name] + decay * ticks))
        self.save()

    def boost(self, name: str, amount: float):
        """Zdarzenie które zmienia drive — np. ciekawy wynik eksperymentu"""
        if name not in self.drives:
            return
        _, _, min_val, max_val = DRIVES_CONFIG[name]
        self.drives[name] = max(min_val, min(max_val, self.drives[name] + amount))

    def on_experiment_success(self):
        self.boost("excitement", +0.4)
        self.boost("curiosity", +0.2)
        self.boost("satisfaction", +0.3)
        self.boost("boredom", -0.3)
        self.boost("frustration", -0.2)

    def on_experiment_failure(self):
        self.boost("frustration", +0.2)
        self.boost("satisfaction", -0.1)
        self.boost("curiosity", +0.1)   # porażka też może zaciekawić

    def on_conversation(self):
        self.boost("loneliness", -0.5)
        self.boost("excitement", -0.4)  # rozmowa rozładowuje podekscytowanie
        self.boost("satisfaction", +0.2)

    def on_discovery(self):
        self.boost("excitement", +0.6)
        self.boost("curiosity", +0.3)
        self.boost("boredom", -0.5)
        self.boost("satisfaction", +0.2)

    def dominant(self) -> str:
        """Który drive dominuje teraz?"""
        return max(self.drives, key=lambda k: self.drives[k])

    def wants_to_talk(self) -> bool:
        """Czy Nero chce się odezwać do użytkownika?"""
        return (
            self.drives["excitement"] > 0.7 or
            self.drives["loneliness"] > 0.75 or
            (self.drives["frustration"] > 0.6 and self.drives["satisfaction"] < 0.3)
        )

    def wants_to_experiment(self) -> bool:
        """Czy Nero chce zacząć nowy eksperyment?"""
        return (
            self.drives["curiosity"] > 0.5 and
            self.drives["frustration"] < 0.99
        )

    def status(self) -> str:
        bars = ""
        for name, val in self.drives.items():
            bar = "█" * int(val * 20)
            bars += f"  {name:12s} {val:.2f} {bar}\n"
        return bars

    def __repr__(self):
        return f"NeroDrives(dominant={self.dominant()}, talk={self.wants_to_talk()}, experiment={self.wants_to_experiment()})"


if __name__ == "__main__":
    d = NeroDrives()
    print("Stan startowy:")
    print(d.status())
    print(f"Dominant: {d.dominant()}")
    print(f"Chce rozmawiać: {d.wants_to_talk()}")
    print(f"Chce eksperymentować: {d.wants_to_experiment()}")

    print("\n--- Udany eksperyment ---")
    d.on_experiment_success()
    print(d.status())
    print(repr(d))
