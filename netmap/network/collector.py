from dataclasses import dataclass
import socket
import time
import psutil
from netmap.core.models import Connection, utc_now


@dataclass
class Snapshot:
    connections: list[Connection]
    observed: str
    warning: str = ""
    valid: bool = True


class Collector:
    def __init__(self, backend=psutil):
        self.backend = backend
        self._processes = {}

    def process_info(self, pid):
        if pid is None:
            return "Неизвестный процесс", "", None
        try:
            proc = self.backend.Process(pid)
            started = proc.create_time()
            cached = self._processes.get(pid)
            if cached and cached[2] == started:
                return cached
            with proc.oneshot():
                name = proc.name() or f"PID {pid}"
                try:
                    executable = proc.exe()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    executable = ""
            info = name, executable, started
            self._processes[pid] = info
            return info
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            return f"PID {pid} · сведения недоступны", "", None

    def collect(self) -> Snapshot:
        observed = utc_now()
        try:
            raw = self.backend.net_connections(kind="inet")
        except (psutil.AccessDenied, PermissionError):
            return Snapshot([], observed, "ОС запретила сбор соединений. Проверьте права доступа.", False)
        except (OSError, RuntimeError) as exc:
            return Snapshot([], observed, f"Сбор временно недоступен: {exc}", False)
        result = {}
        restricted = 0
        live_pids = set()
        for item in raw:
            if not item.laddr:
                continue
            if item.type not in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
                continue
            name, exe, started = self.process_info(item.pid)
            live_pids.add(item.pid)
            restricted += not exe
            is_tcp = item.type == socket.SOCK_STREAM
            remote_ip, remote_port = item.raddr if item.raddr else ("", 0)
            status = item.status if is_tcp else ("UDP · удалённый адрес известен" if remote_ip else "UDP · открытый сокет")
            conn = Connection(item.pid, name, exe, started, "TCP" if is_tcp else "UDP",
                              item.laddr[0], item.laddr[1], remote_ip, remote_port, status, observed)
            result[conn.key] = conn
        self._processes = {pid: info for pid, info in self._processes.items() if pid in live_pids}
        warning = "Часть сведений о процессах недоступна из-за прав ОС или завершения процесса." if restricted else ""
        return Snapshot(list(result.values()), observed, warning)
