from dataclasses import replace
from PySide6.QtCore import QCoreApplication
from netmap.core.settings import Settings
from netmap.core.worker import MonitorWorker
from netmap.database.store import HistoryStore
from netmap.geo.resolver import GeoResolver
from netmap.network.collector import Snapshot


def test_access_failure_does_not_end_observed_sessions(connection):
    app=QCoreApplication.instance() or QCoreApplication([])
    worker=MonitorWorker(Settings())
    worker.store=HistoryStore(':memory:')
    worker.geo=GeoResolver()
    worker.store.observe([connection],connection.observed)
    class Failed:
        def collect(self): return Snapshot([],connection.observed,'denied',False)
    worker.collector=Failed()
    errors=[]
    worker.error.connect(errors.append)
    worker.poll()
    assert errors==['denied']
    assert worker.store.history()[0]['active']==1
    worker.stop()


def test_suspend_gap_breaks_observation(connection,monkeypatch):
    worker=MonitorWorker(Settings())
    worker.store=HistoryStore(':memory:')
    worker.geo=GeoResolver()
    worker.store.observe([connection],connection.observed)
    worker.last_observation_clock=100
    class Good:
        def collect(self): return Snapshot([connection],connection.observed)
    worker.collector=Good()
    monkeypatch.setattr('netmap.core.worker.time.time',lambda:200)
    worker.poll()
    rows=worker.store.history()
    assert len(rows)==2 and sum(r['active'] for r in rows)==1
    worker.stop()
