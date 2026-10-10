import ipaddress
import re
import queue
import threading
import socket
import time
from netmap.core.models import utc_now


def normalize_host(host: str) -> str:
    host = host.strip().strip("[]")
    if not host or len(host) > 253 or any(c.isspace() for c in host):
        raise ValueError("Введите IP или доменное имя без схемы и пути")
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        encoded = host.rstrip(".").encode("idna").decode("ascii")
        if not all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", p) for p in encoded.split(".")):
            raise ValueError("Некорректное доменное имя")
        return encoded


def summarize(durations):
    passed = [v for v in durations if v is not None]
    return {"attempts": len(durations), "success": len(passed),
            "failure_percent": round(100 * (len(durations)-len(passed))/len(durations),1) if durations else 0,
            "min_ms": round(min(passed),2) if passed else None,
            "avg_ms": round(sum(passed)/len(passed),2) if passed else None,
            "max_ms": round(max(passed),2) if passed else None}


_dns_lock = threading.Lock()
_dns_thread = None


def resolve_addresses(host, port, timeout, cancelled):
    """Bound DNS waiting without accumulating blocked resolver threads.

    OS name resolution cannot be forcibly cancelled safely. A single daemon
    resolver may finish in the background after timeout; it never touches Qt.
    """
    global _dns_thread
    result = queue.Queue(maxsize=1)
    def resolve():
        try:
            result.put((socket.getaddrinfo(host,port,type=socket.SOCK_STREAM),None))
        except OSError as exc:
            result.put((None,exc))
    with _dns_lock:
        if _dns_thread is not None and _dns_thread.is_alive():
            raise OSError("Предыдущий системный DNS-запрос ещё выполняется. Повторите позже.")
        _dns_thread = threading.Thread(target=resolve,name="NetMap-DNS",daemon=True)
        _dns_thread.start()
    deadline = time.monotonic()+timeout
    while not cancelled():
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise OSError("Истекло время ожидания DNS. Системный запрос может завершиться позже.")
        try:
            addresses,error = result.get(timeout=min(.05,remaining))
            if error:
                raise error
            return addresses
        except queue.Empty:
            pass
    return []


def probe_tcp(host, port=443, count=5, timeout=2.0, cancelled=lambda: False, progress=lambda *_: None):
    host = normalize_host(host)
    if not 1 <= port <= 65535 or not 1 <= count <= 20 or not .2 <= timeout <= 10:
        raise ValueError("Некорректные параметры проверки")
    if cancelled():
        return {"time":utc_now(),"host":host,"port":port,"address":"","method":"TCP",
                "durations":[],"errors":[],"cancelled":True,**summarize([])}
    candidates = resolve_addresses(host,port,max(2,timeout),cancelled)
    if cancelled():
        return {"time":utc_now(),"host":host,"port":port,"address":"","method":"TCP",
                "durations":[],"errors":[],"cancelled":True,**summarize([])}
    if not candidates:
        raise OSError("DNS не вернул адреса")
    family, socktype, proto, _, addr = candidates[0]
    durations, errors = [], []
    for index in range(count):
        if cancelled():
            break
        started = time.perf_counter()
        try:
            with socket.socket(family, socktype, proto) as sock:
                sock.settimeout(timeout)
                sock.connect(addr)
            elapsed = (time.perf_counter()-started)*1000
            durations.append(elapsed)
            errors.append("")
        except OSError as exc:
            durations.append(None)
            errors.append(str(exc))
        progress(index+1, durations[-1])
        # Small cancellable delay; do not stress the selected destination.
        for _ in range(5):
            if cancelled():
                break
            time.sleep(.05)
    return {"time": utc_now(), "host": host, "port": port, "address": addr[0],
            "method": "TCP", "durations": durations, "errors": errors,
            "cancelled": cancelled(), **summarize(durations)}
