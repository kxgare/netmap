from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path


def data_dir() -> Path:
    root = os.environ.get("NETMAP_DATA_DIR")
    if root:
        return Path(root)
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "NetMap"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "netmap"


@dataclass
class Settings:
    theme: str = "dark"
    mode: str = "simple"
    onboarding_done: bool = False
    interval: float = 2.0
    autostart: bool = True
    animations: bool = True
    map_limit: int = 500
    geo_path: str = ""
    retention_days: int = 30
    origin_enabled: bool = False
    origin_lat: float = 0.0
    origin_lon: float = 0.0
    online_tiles: bool = False
    diagnostics_enabled: bool = True
    diagnostic_count: int = 5
    diagnostic_timeout: float = 2.0

    def validate(self):
        if self.theme not in ("dark", "light") or self.mode not in ("simple", "expert"):
            raise ValueError("Неизвестная тема или режим")
        bool_names = ("onboarding_done", "autostart", "animations", "origin_enabled", "online_tiles", "diagnostics_enabled")
        if any(type(getattr(self, n)) is not bool for n in bool_names):
            raise ValueError("Некорректное логическое значение настройки")
        if not isinstance(self.geo_path, str):
            raise ValueError("Некорректный путь к базе")
        if not 0.5 <= self.interval <= 60 or not math.isfinite(self.interval):
            raise ValueError("Интервал должен быть от 0,5 до 60 секунд")
        if self.map_limit not in (100, 500, 1000):
            raise ValueError("Недопустимый лимит карты")
        if not 1 <= self.retention_days <= 365:
            raise ValueError("Срок хранения должен быть от 1 до 365 дней")
        if not -90 <= self.origin_lat <= 90 or not -180 <= self.origin_lon <= 180:
            raise ValueError("Некорректные координаты")
        if not 1 <= self.diagnostic_count <= 20 or not 0.2 <= self.diagnostic_timeout <= 10:
            raise ValueError("Некорректные параметры диагностики")
        return self

    @classmethod
    def load(cls, path: Path | None = None):
        path = path or data_dir() / "settings.json"
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__}).validate()

    def save(self, path: Path | None = None):
        self.validate()
        path = path or data_dir() / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
