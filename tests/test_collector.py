from collections import namedtuple
import socket
import psutil
from netmap.network.collector import Collector

Socket = namedtuple('Socket','type laddr raddr pid status')


class Process:
    def __init__(self,pid,started,name): self.pid,self.started,self._name=pid,started,name
    def create_time(self): return self.started
    def oneshot(self): return self
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def name(self): return self._name
    def exe(self): return '/apps/'+self._name


class Backend:
    started=10
    name='first.exe'
    def Process(self,pid): return Process(pid,self.started,self.name)
    def net_connections(self,kind):
        assert kind=='inet'
        return [Socket(socket.SOCK_STREAM,('127.0.0.1',5000),('8.8.8.8',443),42,'ESTABLISHED'),
                Socket(socket.SOCK_DGRAM,('0.0.0.0',5353),(),42,'NONE')]


def test_tcp_udp_and_process_identity():
    backend=Backend()
    collector=Collector(backend)
    first=collector.collect()
    assert first.valid and len(first.connections)==2
    tcp,udp=first.connections
    assert tcp.process=='first.exe' and tcp.remote_port==443
    assert udp.protocol=='UDP' and not udp.remote_ip and 'сокет' in udp.status
    assert 'ESTABLISHED' not in udp.status
    backend.started=20
    backend.name='second.exe'
    second=collector.collect()
    assert second.connections[0].process=='second.exe'
    assert second.connections[0].key!=tcp.key


def test_denied_snapshot_is_not_empty_success():
    class Denied:
        def net_connections(self,kind): raise psutil.AccessDenied()
    s=Collector(Denied()).collect()
    assert not s.valid and s.warning


def test_missing_process_does_not_drop_socket():
    class Gone(Backend):
        def Process(self,pid): raise psutil.NoSuchProcess(pid)
    s=Collector(Gone()).collect()
    assert s.valid and len(s.connections)==2
    assert s.connections[0].pid==42 and not s.connections[0].executable


def test_real_local_tcp_and_udp():
    # Exercise psutil against sockets owned by this test process, no Internet needed.
    import os
    listener=socket.socket()
    udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    client=socket.socket()
    try:
        listener.bind(('127.0.0.1',0)); listener.listen(1)
        client.connect(listener.getsockname())
        accepted,_=listener.accept()
        udp.bind(('127.0.0.1',0))
        try:
            s=Collector().collect()
            assert s.valid
            assert any(c.local_port==client.getsockname()[1] and c.remote_port==listener.getsockname()[1] and c.protocol=='TCP' for c in s.connections)
            assert any(c.local_port==udp.getsockname()[1] and c.protocol=='UDP' and not c.remote_ip for c in s.connections)
        finally: accepted.close()
    finally:
        client.close(); listener.close(); udp.close()
