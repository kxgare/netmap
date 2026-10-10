import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
from PySide6.QtCore import QPersistentModelIndex, Qt
from PySide6.QtWidgets import QApplication
from netmap.ui.connections_page import ConnectionsPage
from netmap.ui.table import ConnectionModel, ConnectionFilter

_app = None

def app():
    global _app
    _app = QApplication.instance() or QApplication([])
    return _app


def test_persistent_selection_and_numeric_sort(connection):
    app()
    model=ConnectionModel()
    second=replace(connection,pid=9,local_port=52000,remote_port=80)
    model.update([connection,second])
    index=QPersistentModelIndex(model.index(0,0))
    model.update([replace(connection,status='CLOSE_WAIT'),second])
    assert index.isValid() and index.data()==connection.process
    proxy=ConnectionFilter(); proxy.setSourceModel(model)
    proxy.sort(1,Qt.SortOrder.AscendingOrder)
    assert proxy.index(0,1).data()==9
    model.update([connection])
    assert index.isValid() and model.rowCount()==1


def test_page_keeps_row_and_filter(connection):
    app()
    page=ConnectionsPage()
    other=replace(connection,pid=5,local_port=51001,process='other.exe',executable='/other.exe')
    page.update_data([connection,other])
    page.search.setText('browser')
    page.table.setCurrentIndex(page.proxy.index(0,0))
    key=page.selected().key
    page.update_data([replace(connection,status='CLOSE_WAIT'),other])
    assert page.selected().key==key and page.search.text()=='browser'
    assert page.proxy.rowCount()==1
    page.deleteLater()
