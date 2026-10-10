from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QSplitter, QTextBrowser, QVBoxLayout, QWidget
from netmap.core.statistics import map_points
from netmap.ui.common import connection_html, label, metric, page_header
from netmap.ui.map_view import MapView


class MapPage(QWidget):
    def __init__(self):
        super().__init__()
        self.connections = []
        self.historical = []
        self.settings = None
        self.selected_ip = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28,24,28,24)
        page_header(layout,"Карта вашей сети","Публичные IP и их приблизительная география · данные остаются на компьютере")
        row = QHBoxLayout()
        self.metrics = {}
        for key,title in [("total","Наблюдаемые сокеты"),("public_ips","Публичные IP"),("mapped","IP с координатами"),("unique_ips","Уникальные удалённые IP")]:
            frame,value = metric(title)
            self.metrics[key] = value
            row.addWidget(frame)
        layout.addLayout(row)
        toolbar = QHBoxLayout()
        self.apps = QComboBox()
        self.apps.addItem("Все приложения","")
        self.apps.setMinimumWidth(240)
        toolbar.addWidget(self.apps)
        toolbar.addStretch()
        toolbar.addWidget(label("● Наблюдается   ● История   /   Координаты приблизительные","subheading"))
        layout.addLayout(toolbar)
        split = QSplitter()
        self.map = MapView()
        self.detail = QTextBrowser()
        self.detail.setMinimumWidth(270)
        self.detail.setHtml("<h3>География подключений</h3><p>Выберите точку на карте, чтобы увидеть связанные процессы.</p><p>Геолокация IP не определяет точный адрес сервера.</p>")
        split.addWidget(self.map)
        split.addWidget(self.detail)
        split.setSizes([950,280])
        layout.addWidget(split,1)
        self.notice = label("Офлайн-карта · внешние тайлы выключены","notice",True)
        layout.addWidget(self.notice)
        self.apps.currentIndexChanged.connect(self.render)
        self.map.bridge.selected.connect(self.select_ip)
        self.map.ready.connect(self.map_ready)

    def map_ready(self, ok):
        if not ok:
            self.notice.setText("Не удалось загрузить локальную карту. Соединения доступны в таблице.")

    def render(self):
        if self.settings:
            self.map.update_data(map_points(self.connections,self.historical,self.apps.currentData() or ""),self.settings)

    def select_ip(self, ip):
        self.selected_ip = ip
        rows = [c for c in self.connections if c.remote_ip == ip and (not self.apps.currentData() or c.app_key==self.apps.currentData())]
        if rows:
            self.detail.setHtml('<hr>'.join(connection_html(c) for c in rows))
        else:
            import html
            past = [r for r in self.historical if r["remote_ip"]==ip and (not self.apps.currentData() or (r["executable"] or r["process"])==self.apps.currentData())]
            self.detail.setHtml('<h3>'+html.escape(ip)+'</h3><p>Адрес ранее наблюдался. Подробнее в разделе «История».</p>'+''.join('<p>'+html.escape(r["process"])+' · PID '+str(r["pid"] or '—')+'</p>' for r in past[:20]))

    def update_data(self, payload, settings):
        self.connections, self.historical, self.settings = payload["connections"],payload["historical"],settings
        for key,value in self.metrics.items():
            value.setText(str(payload["stats"][key]))
        known_apps = {r['executable'] or r['process']:r['process'] for r in self.historical}
        known_apps.update({c.app_key:c.process for c in self.connections})
        apps = sorted(known_apps.items(),key=lambda p:p[1].casefold())
        old = self.apps.currentData()
        desired = [("Все приложения","")]+[(name,key) for key,name in apps]
        existing = [(self.apps.itemText(i),self.apps.itemData(i)) for i in range(self.apps.count())]
        if existing != desired:
            self.apps.blockSignals(True)
            self.apps.clear()
            for name,key in desired:
                self.apps.addItem(name,key)
            self.apps.setCurrentIndex(max(0,self.apps.findData(old)))
            self.apps.blockSignals(False)
        self.notice.setText(payload["geo_message"]+" · "+("Тайлы OpenStreetMap включены: сервис видит ваш IP" if settings.online_tiles else "Офлайн-карта, без загрузки тайлов"))
        self.render()
        if self.selected_ip:
            self.select_ip(self.selected_ip)
