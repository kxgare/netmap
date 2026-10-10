"""A server → application → socket tree, separate from the app inspector."""
from collections import defaultdict
from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLineEdit,QTreeWidget,QTreeWidgetItem,QFileIconProvider
from PySide6.QtCore import QFileInfo
from netmap.core.grouping import group_apps
from netmap.ui.common import friendly_name

def readable_state(value):
    return {'ESTABLISHED':'Подключение наблюдается','LISTEN':'Ожидает входящих соединений','SYN_SENT':'Соединение устанавливается','SYN_RECV':'Получен запрос подключения','CLOSE_WAIT':'Ожидает закрытия','TIME_WAIT':'Завершение соединения','CLOSED':'Закрыто','FIN_WAIT1':'Завершение соединения','FIN_WAIT2':'Завершение соединения'}.get(value,value)

class ConnectionExplorer(QWidget):
    selected=Signal(str)
    def __init__(self):
        super().__init__(); self.rows=[]; self.items={}; self.chosen=None; self.app_filter=''
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0)
        self.search=QLineEdit(); self.search.setPlaceholderText('Найти сервер, IP или программу…'); layout.addWidget(self.search)
        self.tree=QTreeWidget(); self.tree.setHeaderLabels(['Удалённый сервер / программа','Сокетов','Страна / состояние'])
        self.tree.setColumnWidth(0,370); layout.addWidget(self.tree,1)
        self.search.textChanged.connect(self.apply_filter); self.tree.currentItemChanged.connect(self.changed)
        self.provider=QFileIconProvider(); self.icons={}
    def update_data(self,connections):
        groups=defaultdict(list)
        for c in connections: groups[c.remote_ip or 'Локальные сокеты без удалённого адреса'].append(c)
        expanded={self.tree.topLevelItem(i).text(0) for i in range(self.tree.topLevelItemCount()) if self.tree.topLevelItem(i).isExpanded()}
        selected=self.chosen; scroll=self.tree.verticalScrollBar().value()
        self.tree.blockSignals(True); self.tree.clear(); self.items={}; self.rows=[]
        for server,members in sorted(groups.items()):
            countries=', '.join(sorted({c.location.country for c in members if c.location.country}))
            parent=QTreeWidgetItem([server,str(len(members)),countries or ('Открытые локальные сокеты' if not members[0].remote_ip else 'Страна не определена')]); self.tree.addTopLevelItem(parent)
            parent.setExpanded(server in expanded)
            for row in group_apps(members):
                self.rows.append(row); identity=(server,row['key']); self.items[identity]=row
                states=', '.join(sorted({readable_state(c.status) for c in row['connections']}))
                item=QTreeWidgetItem([friendly_name(row['name']),str(row['count']),states]); item.setData(0,Qt.ItemDataRole.UserRole,identity); parent.addChild(item)
                exe=row['executable']
                if exe:
                    if exe not in self.icons: self.icons[exe]=self.provider.icon(QFileInfo(exe))
                    item.setIcon(0,self.icons[exe])
                for c in row['connections']:
                    child=QTreeWidgetItem([f'{c.protocol} · {c.local_address} → {c.remote_address}', '1',readable_state(c.status)]); child.setData(0,Qt.ItemDataRole.UserRole,identity); item.addChild(child)
                if identity==selected: self.tree.setCurrentItem(item)
        self.chosen=selected if selected in self.items else None
        if len(self.icons)>256: self.icons.clear()
        self.tree.blockSignals(False); self.tree.verticalScrollBar().setValue(scroll); self.apply_filter()
    def current(self): return self.items.get(self.chosen)
    def changed(self,item,previous):
        if item:
            identity=item.data(0,Qt.ItemDataRole.UserRole)
            if identity in self.items: self.chosen=identity; self.selected.emit(identity[1])
    def select_app(self,key):
        for i in range(self.tree.topLevelItemCount()):
            p=self.tree.topLevelItem(i)
            for j in range(p.childCount()):
                child=p.child(j); identity=child.data(0,Qt.ItemDataRole.UserRole)
                if identity[1]==key: p.setExpanded(True); self.tree.setCurrentItem(child); return
    def set_app_filter(self,key): self.app_filter=key; self.apply_filter()
    def apply_filter(self):
        term=self.search.text().casefold()
        for i in range(self.tree.topLevelItemCount()):
            p=self.tree.topLevelItem(i); visible=False
            for j in range(p.childCount()):
                child=p.child(j); identity=child.data(0,Qt.ItemDataRole.UserRole)
                show=(not self.app_filter or identity[1]==self.app_filter) and (not term or term in (p.text(0)+' '+child.text(0)).casefold())
                child.setHidden(not show); visible|=show
            p.setHidden(not visible)
