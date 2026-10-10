from PySide6.QtCore import QAbstractTableModel,QModelIndex,QSortFilterProxyModel,QFileInfo,Qt,Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLineEdit,QTableView,QFileIconProvider
from netmap.core.grouping import group_apps
from netmap.ui.common import friendly_name,setup_table
from netmap.ui.table import display_time

class GroupModel(QAbstractTableModel):
    headers=['Программа','Подключений','Удалённых IP','Последнее наблюдение']
    def __init__(self,parent=None):
        super().__init__(parent); self.rows=[]; self.icons={}; self.provider=QFileIconProvider()
    def rowCount(self,p=QModelIndex()): return 0 if p.isValid() else len(self.rows)
    def columnCount(self,p=QModelIndex()): return 0 if p.isValid() else 4
    def headerData(self,i,o,role=Qt.ItemDataRole.DisplayRole):
        if o==Qt.Orientation.Horizontal and role==Qt.ItemDataRole.DisplayRole: return self.headers[i]
    def data(self,index,role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        r=self.rows[index.row()]; col=index.column()
        values=[friendly_name(r['name']),r['count'],len(r['remote_ips']),display_time(r['last'])]
        if role==Qt.ItemDataRole.DisplayRole: return values[col]
        if role==Qt.ItemDataRole.UserRole: return r['last'] if col==3 else values[col]
        if role==Qt.ItemDataRole.ToolTipRole: return r['executable'] or r['name']
        if role==Qt.ItemDataRole.DecorationRole and col==0 and r['executable']:
            key=r['executable']
            if key not in self.icons:
                if len(self.icons)>256: self.icons.clear()
                self.icons[key]=self.provider.icon(QFileInfo(key))
            return self.icons[key]
    def update(self,connections):
        incoming={r['key']:r for r in group_apps(connections)}
        for i in range(len(self.rows)-1,-1,-1):
            if self.rows[i]['key'] not in incoming:
                self.beginRemoveRows(QModelIndex(),i,i); self.rows.pop(i); self.endRemoveRows()
        keys={r['key'] for r in self.rows}
        for i,r in enumerate(self.rows):
            if r!=incoming[r['key']]:
                self.rows[i]=incoming[r['key']]; self.dataChanged.emit(self.index(i,0),self.index(i,3))
        extra=[r for k,r in incoming.items() if k not in keys]
        if extra:
            n=len(self.rows); self.beginInsertRows(QModelIndex(),n,n+len(extra)-1); self.rows.extend(extra); self.endInsertRows()

class GroupsView(QWidget):
    selected=Signal(str)
    def __init__(self):
        super().__init__()
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0)
        self.search=QLineEdit(); self.search.setPlaceholderText('Найти программу…')
        layout.addWidget(self.search)
        self.model=GroupModel(self); self.proxy=QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model); self.proxy.setSortRole(Qt.ItemDataRole.UserRole)
        self.proxy.setFilterKeyColumn(0); self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.table=QTableView(); self.table.setModel(self.proxy); setup_table(self.table)
        for i,w in enumerate([260,140,160,200]): self.table.setColumnWidth(i,w)
        self.table.sortByColumn(1,Qt.SortOrder.DescendingOrder); layout.addWidget(self.table,1)
        self.search.textChanged.connect(self.proxy.setFilterFixedString)
        self.table.selectionModel().currentChanged.connect(self.changed)
    def changed(self,current,previous):
        row=self.current()
        if row: self.selected.emit(row['key'])
    def current(self):
        i=self.table.currentIndex()
        return self.model.rows[self.proxy.mapToSource(i).row()] if i.isValid() else None
    def update_data(self,connections):
        scroll=self.table.verticalScrollBar().value()
        self.model.update(connections); self.table.verticalScrollBar().setValue(scroll)
    def select_app(self,key):
        for i,r in enumerate(self.model.rows):
            if r['key']==key:
                idx=self.proxy.mapFromSource(self.model.index(i,0))
                if idx.isValid(): self.table.setCurrentIndex(idx)
                return
