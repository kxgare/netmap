from dataclasses import replace
from datetime import datetime, timezone
from netmap.database.store import HistoryStore


def test_session_updates_disappearance_and_return(tmp_path,connection):
    store=HistoryStore(tmp_path/'history.db')
    rows,new=store.observe([connection],connection.observed)
    assert new==1 and rows[0].first_seen==connection.observed
    later='2026-10-10T10:00:02.000+00:00'
    rows,new=store.observe([replace(connection,status='CLOSE_WAIT',observed=later)],later)
    assert new==0 and rows[0].first_seen==connection.observed
    h=store.history()[0]
    assert h['last_seen']==later and h['status']=='CLOSE_WAIT' and h['active']==1
    store.observe([],'2026-10-10T10:00:04.000+00:00')
    assert store.history()[0]['active']==0
    store.observe([connection],'2026-10-10T10:00:06.000+00:00')
    assert len(store.history())==2
    store.close()
    reopened=HistoryStore(tmp_path/'history.db')
    assert len(reopened.history())==2 and all(not r['active'] for r in reopened.history())
    assert reopened.samples()[-1]['new']==1
    reopened.close()


def test_search_period_app_retention_and_clear(tmp_path,connection):
    store=HistoryStore(tmp_path/'history.db')
    store.observe([connection],connection.observed)
    assert len(store.history(search='BROWSER'))==1
    assert len(store.history(search='8.8.8.8'))==1
    assert not store.history(search="' OR 1=1 --")
    assert not store.history(search='%')
    assert not store.history(since='2026-10-11T00:00:00+00:00')
    assert len(store.history(app=connection.app_key))==1
    store.end_observation()
    store.prune(1,datetime(2026,10,12,tzinfo=timezone.utc))
    assert not store.history() and not store.samples()
    store.observe([connection],connection.observed)
    store.clear()
    assert not store.history() and not store.active
    store.close()


def test_diagnostics_persist(tmp_path):
    store=HistoryStore(tmp_path/'history.db')
    result={'time':'2026-10-10T10:00:00+00:00','host':'localhost','port':443,'success':1}
    store.add_diagnostic(result)
    assert store.diagnostic_history()==[result]
    store.close()


def test_pause_makes_new_session(connection):
    store=HistoryStore(':memory:')
    store.observe([connection],connection.observed)
    store.end_observation()
    _,new=store.observe([connection],'2026-10-10T10:00:04.000+00:00')
    assert new==1 and len(store.history())==2
    store.close()


def test_russian_casefold(connection):
    store=HistoryStore(':memory:')
    store.observe([replace(connection,process='БРАУЗЕР.exe')],connection.observed)
    assert len(store.history(search='браузер'))==1
    store.close()
