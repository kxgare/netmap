from dataclasses import replace
from PySide6.QtCore import Qt,QItemSelectionModel
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QWidget,QPushButton
from netmap.core.settings import Settings
from netmap.ui.connections_page import ConnectionsPage
from netmap.ui.apps_page import AppsPage
from netmap.ui.search_overlay import SearchOverlay
from netmap.ui.window_controls import WindowControls
from netmap.ui.theme import stylesheet
from netmap.ui.ip_details import ip_html
from netmap.ui.typography import apply_typography
from netmap.ui.interaction import apply_interactions
from netmap.database.store import HistoryStore

_app=None
def app():
    global _app
    _app=QApplication.instance() or QApplication([])
    return _app

def test_server_tree_separates_apps_and_udp(connection):
    app(); p=ConnectionsPage()
    other=replace(connection,remote_ip='1.1.1.1',local_port=51001)
    udp=replace(connection,protocol='UDP',remote_ip='',remote_port=0,status='UDP · открытый сокет',local_port=51002)
    p.update_data([connection,other,udp])
    assert p.groups.tree.topLevelItemCount()==3
    local=[p.groups.tree.topLevelItem(i) for i in range(3) if 'без удалённого' in p.groups.tree.topLevelItem(i).text(0)][0]
    assert 'открытый сокет' in local.child(0).text(2)
    p.groups.search.setText('8.8.8.8')
    assert sum(not p.groups.tree.topLevelItem(i).isHidden() for i in range(3))==1

def test_combined_filters_and_multiselection_survive_update(connection):
    app(); p=ConnectionsPage();p.set_mode('expert')
    a=replace(connection,local_port=51001);b=replace(connection,pid=444,local_port=51002)
    p.update_data([connection,a,b]);p.pid.setText('123');p.state.setCurrentText('ESTABLISHED');p.family.setCurrentText('IPv4');p.search.setText('8.8.8.8')
    assert p.proxy.rowCount()==2
    for row in range(2):p.table.selectionModel().select(p.proxy.index(row,0),QItemSelectionModel.SelectionFlag.Select|QItemSelectionModel.SelectionFlag.Rows)
    p.update_data([replace(a,observed='2026-10-10T10:10:00+00:00'),connection,b])
    assert len(p.table.selectionModel().selectedRows())==2
    p.family.setCurrentText('IPv6');assert p.proxy.rowCount()==0

def test_window_controls_actions_restore_icon():
    app()
    class Window(QWidget):
        def __init__(self):super().__init__();self.minimized=0;self.closed=0
        def showMinimized(self):self.minimized+=1
        def close(self):self.closed+=1;return True
    w=Window(); controls=WindowControls(w);w.show();app().processEvents()
    icon=controls.maximize.icon().cacheKey();controls.maximize.click();app().processEvents()
    assert w.isMaximized() and controls.maximize.icon().cacheKey()!=icon
    controls.maximize.click();assert not w.isMaximized()
    controls.minimize.click();controls.close_button.click();assert w.minimized==w.closed==1
    assert controls.close_button.accessibleName()=='Закрыть'
    w.hide()

def test_actual_focus_pressed_and_cursor():
    application=app()
    b=QPushButton('Действие');apply_interactions(b);b.setStyleSheet(stylesheet());b.show();b.setFocus();application.processEvents()
    assert b.hasFocus() and b.cursor().shape()==Qt.CursorShape.PointingHandCursor
    QTest.mouseMove(b);QTest.mousePress(b,Qt.MouseButton.LeftButton);assert b.isDown()
    QTest.mouseRelease(b,Qt.MouseButton.LeftButton);assert not b.isDown()
    b.setEnabled(False);QTest.mouseClick(b,Qt.MouseButton.LeftButton);assert not b.isDown()
    for state in (':hover',':focus',':pressed',':disabled',':checked'):assert state in stylesheet()
    b.close()

def test_fonts_popups_share_family():
    from PySide6.QtWidgets import QComboBox,QSpinBox,QDateEdit,QMenu
    application=app();family=apply_typography(application)
    for widget in (QComboBox(),QSpinBox(),QDateEdit(),QMenu()):assert widget.font().family()==family

def test_ip_card_real_fields_escaped_and_no_fake_location(connection):
    text=ip_html(connection.remote_ip,[replace(connection,process='<script>')])
    assert '&lt;script&gt;' in text and '37.7510' in text and '443' in text
    from netmap.core.models import Location
    missing=ip_html(connection.remote_ip,[replace(connection,location=Location())])
    assert 'Приблизительные координаты' not in missing
    assert 'connections:' in text and 'history:' in text

def test_favorites_roundtrip_and_dormant_entry(tmp_path,connection):
    app();path=tmp_path/'settings.json';replace(Settings(),favorites=[connection.app_key]).save(path)
    settings=Settings.load(path);assert settings.favorites==[connection.app_key]
    p=AppsPage();p.set_favorites(settings.favorites);p.update_data([])
    assert p.groups.model.rows[0]['count']==0
    p.groups.select_app(connection.app_key);assert 'не наблюдаются' in p.detail.toPlainText()
    p.update_data([connection]);keys=[];p.favorites_changed.connect(keys.append);p.toggle_favorite();assert keys==[[]]

def test_search_real_history_literal_and_keyboard(connection):
    app();store=HistoryStore(':memory:');store.observe([connection],connection.observed)
    assert store.search_catalog('browser')['apps'][0]['executable']==connection.executable
    assert store.search_catalog('8.8')['ips'][0]['remote_ip']==connection.remote_ip
    assert store.search_catalog('%')=={'apps':[],'ips':[]}
    overlay=SearchOverlay();overlay.connections=[connection];overlay.open_search();overlay.input.setText('8.8')
    activated=[];overlay.activated.connect(lambda *v:activated.append(v));QTest.keyClick(overlay.input,Qt.Key.Key_Return)
    assert activated==[('ip','8.8.8.8')]
    overlay.open_search();overlay.input.setText('browser');generation=overlay.generation
    overlay.history_results({'id':generation-1,'apps':[],'ips':[{'remote_ip':'unwanted'}]})
    assert all('unwanted' not in overlay.results.item(i).text() for i in range(overlay.results.count()))
    QTest.keyClick(overlay.input,Qt.Key.Key_Down);assert overlay.results.currentRow()==1
    QTest.keyClick(overlay.input,Qt.Key.Key_Escape);assert not overlay.isVisible();store.close()

def test_new_addresses_unique_not_sockets(connection):
    from datetime import datetime,timezone
    store=HistoryStore(':memory:');store.observe([connection,replace(connection,local_port=51001),replace(connection,remote_ip='127.0.0.1',local_port=51002)],connection.observed)
    rows=store.new_addresses(900,datetime(2026,10,10,10,6,tzinfo=timezone.utc))
    assert len(rows)==1 and rows[0]['remote_ip']=='8.8.8.8' and rows[0]['apps']==['browser.exe']
    store.close()
