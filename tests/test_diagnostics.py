import socket
import threading
import pytest
from netmap.diagnostics.tcp import normalize_host, probe_tcp, summarize


@pytest.mark.parametrize('host',['https://example.com','host/path','host;cmd','a b','-bad.com',''])
def test_invalid_host(host):
    with pytest.raises(ValueError): normalize_host(host)


def test_idna_and_ipv6():
    assert normalize_host('[::1]')=='::1'
    assert normalize_host('пример.рф')=='xn--e1afmkfd.xn--p1ai'


def test_summary():
    s=summarize([10,None,20])
    assert s['avg_ms']==15 and s['failure_percent']==33.3 and s['success']==2
    assert summarize([None])['min_ms'] is None


def test_tcp_local_server():
    server=socket.socket(); server.bind(('127.0.0.1',0)); server.listen(4)
    def accept():
        for _ in range(3):
            client,_=server.accept(); client.close()
    thread=threading.Thread(target=accept,daemon=True); thread.start()
    try:
        result=probe_tcp('127.0.0.1',server.getsockname()[1],count=3,timeout=.5)
        assert result['success']==3 and result['failure_percent']==0
        assert result['method']=='TCP' and result['min_ms'] is not None
        thread.join(2)
        assert not thread.is_alive()
    finally: server.close()


def test_cancel_before_attempt():
    r=probe_tcp('127.0.0.1',443,count=3,cancelled=lambda:True)
    assert r['attempts']==0 and r['cancelled']


def test_dns_wait_is_bounded(monkeypatch):
    import time
    from netmap.diagnostics.tcp import resolve_addresses
    def delayed(*args,**kwargs):
        time.sleep(.2)
        return []
    monkeypatch.setattr(socket,'getaddrinfo',delayed)
    started=time.monotonic()
    with pytest.raises(OSError,match='DNS'):
        resolve_addresses('example.com',443,.03,lambda:False)
    assert time.monotonic()-started < .15
    with pytest.raises(OSError,match='Предыдущий'):
        resolve_addresses('example.com',443,.03,lambda:False)
    time.sleep(.22)  # Allow the single daemon resolver to finish before other tests.
