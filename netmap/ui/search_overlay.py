"""Debounced local search; all database work stays in MonitorWorker."""
from PySide6.QtCore import Qt,QTimer,Signal
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLineEdit,QListWidget,QListWidgetItem

PAGES=['Карта','Соединения','Приложения','Аналитика','История','Настройки']
class SearchOverlay(QDialog):
    requested=Signal(object)
    activated=Signal(str,str)
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowFlags(Qt.WindowType.Dialog|Qt.WindowType.FramelessWindowHint); self.setObjectName('search-overlay'); self.setWindowTitle('Быстрый поиск · Ctrl+K'); self.resize(650,440)
        self.connections=[]; self.generation=0; self.saved={'apps':[],'ips':[]}
        layout=QVBoxLayout(self); self.input=QLineEdit(); self.input.setPlaceholderText('Программа, IP или раздел…')
        layout.addWidget(self.input); self.results=QListWidget(); layout.addWidget(self.results)
        self.timer=QTimer(self); self.timer.setSingleShot(True); self.timer.setInterval(180); self.timer.timeout.connect(self.query)
        self.input.textChanged.connect(self.changed); self.results.itemActivated.connect(self.choose)
        self.input.installEventFilter(self); self.results.installEventFilter(self)
    def open_search(self):
        self.input.clear(); self.saved={'apps':[],'ips':[]}; self.changed(); self.show(); self.raise_(); self.activateWindow(); self.input.setFocus()
    def changed(self):
        self.generation+=1; self.saved={'apps':[],'ips':[]}; self.render(); self.timer.start()
    def query(self): self.requested.emit({'id':self.generation,'term':self.input.text().strip()})
    def history_results(self,payload):
        if payload['id']!=self.generation: return
        self.saved=payload; self.render()
    def render(self):
        term=self.input.text().strip().casefold(); old=self.results.currentItem(); selected=old.data(Qt.ItemDataRole.UserRole) if old else None
        self.results.clear(); entries=[]
        for i,title in enumerate(PAGES):
            if not term or term in title.casefold(): entries.append((title,'page',str(i)))
        apps={c.app_key:c.process for c in self.connections if not term or term in (c.process+' '+c.executable).casefold()}
        apps.update({r['executable'] or r['process']:r['process'] for r in self.saved['apps']})
        for key,name in list(apps.items())[:20]:
            entries.extend([(name+' · приложение','app',key),(name+' · история','history',key),(name+' · карта','map',key)])
        ips={c.remote_ip for c in self.connections if c.remote_ip and (not term or term in c.remote_ip.casefold())}|{r['remote_ip'] for r in self.saved['ips']}
        for ip in sorted(ips)[:30]: entries.append((ip+' · адрес на карте','ip',ip))
        for title,action,value in entries:
            item=QListWidgetItem(title); item.setData(Qt.ItemDataRole.UserRole,(action,value)); self.results.addItem(item)
            if selected==(action,value): self.results.setCurrentItem(item)
        if self.results.currentRow()<0 and self.results.count(): self.results.setCurrentRow(0)
    def choose(self,item):
        if not item:return
        action,value=item.data(Qt.ItemDataRole.UserRole); self.accept(); self.activated.emit(action,value)
    def eventFilter(self,obj,event):
        from PySide6.QtCore import QEvent
        if event.type()==QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Down,Qt.Key.Key_Up):
                delta=1 if event.key()==Qt.Key.Key_Down else -1
                self.results.setCurrentRow(max(0,min(self.results.count()-1,self.results.currentRow()+delta))); return True
            if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter): self.choose(self.results.currentItem()); return True
            if event.key()==Qt.Key.Key_Escape: self.reject(); return True
        return super().eventFilter(obj,event)
