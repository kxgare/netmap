from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class Location:
    country: str = ""
    city: str = ""
    latitude: float | None = None
    longitude: float | None = None
    accuracy_km: int | None = None
    reason: str = ""

    @property
    def mapped(self) -> bool:
        return self.latitude is not None and self.longitude is not None


@dataclass(frozen=True)
class Connection:
    pid: int | None
    process: str
    executable: str
    process_started: float | None
    protocol: str
    local_ip: str
    local_port: int
    remote_ip: str
    remote_port: int
    status: str
    observed: str
    location: Location = field(default_factory=Location)
    first_seen: str = ""

    @property
    def key(self) -> str:
        # State changes belong to the same observation; PID reuse does not.
        raw = (self.pid, self.process_started, self.protocol, self.local_ip,
               self.local_port, self.remote_ip, self.remote_port)
        return hashlib.sha256(repr(raw).encode()).hexdigest()[:32]

    @property
    def app_key(self) -> str:
        return self.executable or self.process

    @property
    def local_address(self) -> str:
        return address(self.local_ip, self.local_port)

    @property
    def remote_address(self) -> str:
        return address(self.remote_ip, self.remote_port) if self.remote_ip else "—"


def address(ip: str, port: int) -> str:
    return f"[{ip}]:{port}" if ":" in ip else f"{ip}:{port}"
