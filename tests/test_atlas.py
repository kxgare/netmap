import csv
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
from PySide6.QtWidgets import QApplication
from netmap.core.settings import Settings
from netmap.core.grouping import group_apps
from netmap.core.export import write_csv
from netmap.database.store import HistoryStore
from netmap.ui.navigation import Navigation
from netmap.ui.connections_page import ConnectionsPage
from netmap.ui.history_page import HistoryPage
from netmap.ui.geo_validation import GeoValidation
from netmap.ui.theme import tokens,stylesheet

_app=None
def app():
    global _app
    _app=QApplication.instance() or QApplication([])
    return _app

def test_old_settings_and_theme_mode_roundtrip(tmp_path):
    p=tmp_path/'settings.json'; p.write_text('{"interval":3,"geo_path":"old.mmdb"}')
    s=Settings.load(p)
    assert s.interval==3 and s.geo_path=='old.mmdb' and s.mode=='simple'
    replace(s,mode='expert',theme='light',onboarding_done=True).save(p)
    loaded=Settings.load(p)
    assert loaded.theme=='light' and loaded.mode=='expert' and loaded.onboarding_done

def test_grouping_keeps_processes_and_local_counts(connection):
    groups=group_apps([connection,replace(connection,pid=124,local_port=51001),replace(connection,remote_ip='127.0.0.1',local_port=51002)])
    assert len(groups)==1 and groups[0]['count']==3 and groups[0]['local_count']==1
    assert groups[0]['public_ips']==['8.8.8.8'] and len(groups[0]['connections'])==3

def test_modes_keep_selected_expert_row_and_filters(connection):
    app(); page=ConnectionsPage(); page.set_mode('expert'); page.update_data([connection])
    page.search.setText('browser'); page.table.setCurrentIndex(page.proxy.index(0,0))
    key=page.selected().key
    page.set_mode('simple'); page.groups.select_app(connection.app_key)
    page.set_mode('expert'); page.update_data([replace(connection,status='CLOSE_WAIT')])
    assert page.selected().key==key and page.search.text()=='browser'
    assert page.groups.current()['key']==connection.app_key
    assert not page.panel.isHidden()
    page.panel.dismiss(); page.update_data([connection]); assert page.panel.isHidden()

def test_navigation_and_tokens():
    app(); nav=Navigation(); selected=[]; modes=[]
    nav.selected.connect(selected.append); nav.mode_changed.connect(modes.append)
    nav.buttons[3].click(); nav.modes['expert'].click(); nav.select(3); nav.set_mode('expert')
    assert selected==[3] and modes==['expert'] and nav.buttons[3].isChecked()
    assert tokens('light').bg!=tokens('dark').bg and 'sidebar' not in stylesheet()

def test_pagination_filters_sort_and_export_all(tmp_path,connection):
    store=HistoryStore(tmp_path/'history.db')
    for i in range(1100):
        c=replace(connection,local_port=10000+i,pid=i,protocol='TCP' if i%2 else 'UDP')
        store.observe([c],connection.observed)
    assert store.history_count()==1100
    a=store.history(limit=100,offset=0); b=store.history(limit=100,offset=100)
    assert len(a)==len(b)==100 and not {r['id'] for r in a}&{r['id'] for r in b}
    assert store.history_count(protocol='UDP')==550
    assert len(store.history(pid=500,ip='8.8.8.8'))==1
    sorted_rows=store.history(sort='pid',descending=False,limit=100)
    assert sorted_rows[0]['pid']==0 and sorted_rows[-1]['pid']==99
    path=tmp_path/'export.csv'; n=write_csv(path,store.export_rows(protocol='TCP'),['id','process','pid'])
    with path.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.reader(f))
    assert n==550 and len(rows)==551
    store.close()

def test_csv_formula_values_are_escaped(tmp_path):
    path=tmp_path/'test.csv';write_csv(path,[{'process':'=danger'}],['process'])
    assert "'=danger" in path.read_text(encoding='utf-8-sig')

def test_history_grouping_preserves_sessions(connection):
    app(); store=HistoryStore(':memory:')
    store.observe([connection],connection.observed); store.end_observation()
    store.observe([connection],'2026-10-10T10:00:04.000+00:00')
    page=HistoryPage(); page.show_rows({'query':{},'rows':store.history(),'total':2})
    assert page.tree.topLevelItemCount()==1 and page.tree.topLevelItem(0).childCount()==2
    child=page.tree.topLevelItem(0).child(0); page.tree.setCurrentItem(child)
    assert page.selected_row()['id']==child.data(0,256)
    page.set_mode('expert'); assert len(page.rows)==2 and page.model.rowCount()==2
    store.close()

def test_period_statistics_new_ips_not_new_sockets(connection):
    store=HistoryStore(':memory:')
    store.observe([connection],connection.observed)
    later='2026-10-10T10:05:00.000+00:00'
    store.observe([connection,replace(connection,local_port=51001),replace(connection,remote_ip='1.1.1.1',local_port=51002)],later)
    now=datetime(2026,10,10,10,6,tzinfo=timezone.utc)
    result=store.analytics(900,now)
    assert result['new_ips']==2 and result['unique_ips']==2 and result['sample_count']==2
    assert store.analytics(120,now)['new_ips']==1
    assert len(result['samples'])==2 and result['protocols']['TCP']==3
    store.close()

def test_geo_path_rejected_in_background(tmp_path):
    worker=GeoValidation(replace(Settings(),geo_path=str(tmp_path/'missing.mmdb')))
    results=[]; worker.validated.connect(lambda *args:results.append(args))
    worker.run()
    assert results and not results[0][0]
    bad=tmp_path/'bad.mmdb'; bad.write_text('bad')
    worker=GeoValidation(replace(Settings(),geo_path=str(bad))); results=[]
    worker.validated.connect(lambda *args:results.append(args)); worker.run()
    assert not results[0][0]

def test_simple_context_stays_open_and_updates(connection):
    app(); page=ConnectionsPage(); page.set_mode('simple'); page.update_data([connection]); page.groups.select_app(connection.app_key)
    assert not page.panel.isHidden()
    page.update_data([connection,replace(connection,pid=222,local_port=51010)])
    assert not page.panel.isHidden() and '2 наблюдаемых' in page.detail.toPlainText()
    page.panel.dismiss(); page.update_data([connection]); assert page.panel.isHidden()

def test_history_actions_and_mode_selection(connection):
    app(); store=HistoryStore(':memory:'); store.observe([connection],connection.observed)
    page=HistoryPage(); page.show_rows({'query':{},'rows':store.history(),'total':1})
    page.tree.setCurrentItem(page.tree.topLevelItem(0).child(0))
    sid=page.selected_row()['id']; page.set_mode('expert'); assert page.selected_row()['id']==sid
    ips=[];apps=[];page.map_requested.connect(ips.append);page.app_requested.connect(apps.append)
    page.context_action(page.map_requested);page.context_action(page.app_requested)
    assert ips==[connection.remote_ip] and apps==[connection.app_key]
    store.close()

def test_v01_database_rows_survive_v02_queries(tmp_path,connection):
    path=tmp_path/'old.db'; store=HistoryStore(path); store.observe([connection],connection.observed);store.close()
    import sqlite3
    with sqlite3.connect(path) as db:
        before=db.execute('SELECT id,first_seen,last_seen,process,remote_ip FROM sessions').fetchall()
        version=db.execute('PRAGMA user_version').fetchone()[0]
    store=HistoryStore(path);store.history(offset=0,limit=100);store.analytics(0);store.close()
    with sqlite3.connect(path) as db:
        assert before==db.execute('SELECT id,first_seen,last_seen,process,remote_ip FROM sessions').fetchall()
        assert version==db.execute('PRAGMA user_version').fetchone()[0]==1

def test_apps_expert_address_groups_and_map_action(connection):
    from netmap.ui.apps_page import AppsPage
    app(); page=AppsPage()
    page.update_data([connection,replace(connection,pid=222,local_port=51010)])
    page.groups.select_app(connection.app_key);page.set_mode('expert')
    assert 'Группы по адресам' in page.detail.toPlainText()
    assert '8.8.8.8 · 2 сокетов' in page.detail.toPlainText()
    assert page.proxy.rowCount()==2 and page.selected_key==connection.app_key
