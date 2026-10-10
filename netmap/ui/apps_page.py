from collections import defaultdict
import html
from PySide6.QtCore import QFileInfo, Qt, Signal
from PySide6.QtWidgets import QFileIconProvider, QHBoxLayout, QListWidget, QListWidgetItem, QSplitter, QTextBrowser, QVBoxLayout, QWidget
from netmap.ui.common import label, page_header
from netmap.ui.table import display_time


class AppsPage(QWidget):
    history_requested = Signal(object)
    def __init__(self):
        super().__init__()
        self.connections = []
        self.history_payload = None
        self.icons = {}
        self.provider = QFileIconProvider()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28,24,28,24)
        page_header(layout,"Приложения","Программы, чьи сетевые сокеты доступны для наблюдения")
        split = QSplitter()
        self.list = QListWidget()
        self.list.setMinimumWidth(310)
        self.detail = QTextBrowser()
        split.addWidget(self.list)
        split.addWidget(self.detail)
        split.setSizes([380,800])
        layout.addWidget(split,1)
        layout.addWidget(label("Иконки извлекаются из доступных исполняемых файлов. Недоступные процессы отображаются без вымышленных иконок.","subheading",True))
        self.list.currentItemChanged.connect(self.selection)

    def update_data(self, connections):
        self.connections = connections
        old = self.list.currentItem().data(Qt.ItemDataRole.UserRole) if self.list.currentItem() else None
        grouped = defaultdict(list)
        for c in connections:
            grouped[c.app_key].append(c)
        scroll = self.list.verticalScrollBar().value()
        self.list.blockSignals(True)
        self.list.clear()
        for key,rows in sorted(grouped.items(),key=lambda p:-len(p[1])):
            ips = {c.remote_ip for c in rows if c.remote_ip}
            item = QListWidgetItem(f"{rows[0].process}\n{len(rows)} сокетов · {len(ips)} удалённых IP")
            item.setData(Qt.ItemDataRole.UserRole,key)
            if rows[0].executable:
                if key not in self.icons:
                    if len(self.icons)>=256:
                        self.icons.clear()
                    self.icons[key] = self.provider.icon(QFileInfo(rows[0].executable))
                item.setIcon(self.icons[key])
            self.list.addItem(item)
            if old == key:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        self.list.verticalScrollBar().setValue(scroll)
        if not self.list.currentItem() and self.list.count():
            self.list.setCurrentRow(0)
        elif self.list.currentItem():
            self.render()
        else:
            self.detail.setHtml("<h3>Нет доступных приложений</h3><p>Дождитесь следующего опроса.</p>")

    def selection(self):
        self.history_payload = None
        self.render()
        self.request_history()

    def request_history(self):
        item = self.list.currentItem()
        if item:
            self.history_requested.emit({"app":item.data(Qt.ItemDataRole.UserRole),"limit":100,"_target":"app"})

    def render(self):
        item = self.list.currentItem()
        if not item:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        rows = [c for c in self.connections if c.app_key==key]
        if not rows:
            return
        esc = html.escape
        countries = sorted({c.location.country for c in rows if c.location.country})
        text = '<h2>'+esc(rows[0].process)+'</h2><p>'+esc(rows[0].executable or "Путь к исполняемому файлу недоступен")+'</p>'
        text += '<p>Последнее наблюдение: '+display_time(max(c.observed for c in rows))+'</p>'
        text += '<p>География: '+esc(', '.join(countries) or "Геолокация не определена")+'</p><h3>Связанные сокеты</h3>'
        text += ''.join('<p>PID '+str(c.pid or '—')+' · '+esc(c.protocol)+' · '+esc(c.local_address)+' → '+esc(c.remote_address)+'<br>'+esc(c.status)+'</p>' for c in rows)
        text += '<h3>Удалённые серверы</h3><p>'+esc(', '.join(sorted({c.remote_ip for c in rows if c.remote_ip})) or "Не обнаружены")+'</p>'
        self.base_html = text
        scroll = self.detail.verticalScrollBar().value()
        self.detail.setHtml(text)
        self.detail.verticalScrollBar().setValue(scroll)
        if self.history_payload:
            self.show_history(self.history_payload)

    def show_history(self, payload):
        item = self.list.currentItem()
        if not item or payload['query'].get('app') != item.data(Qt.ItemDataRole.UserRole):
            return
        self.history_payload = payload
        text = self.base_html+'<h3>Последние сеансы приложения (до 100)</h3>'
        text += ''.join('<p>'+html.escape(r['remote_ip'] or r['local_ip'])+' · '+html.escape(r['protocol'])+' · '+display_time(r['last_seen'])+'</p>' for r in payload['rows'])
        scroll = self.detail.verticalScrollBar().value()
        self.detail.setHtml(text)
        self.detail.verticalScrollBar().setValue(scroll)
