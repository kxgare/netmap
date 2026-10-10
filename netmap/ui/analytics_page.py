import html
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QScrollArea, QSpinBox, QTextBrowser, QVBoxLayout, QWidget
from netmap.ui.common import card, label, metric, page_header
from netmap.widgets.charts import Bars, Timeline
from netmap.ui.table import display_time


class AnalyticsPage(QWidget):
    probe_requested = Signal(str,int)
    cancel_requested = Signal()
    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0,0,0,0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28,24,28,24)
        page_header(layout,"Аналитика","Статистика наблюдаемых сокетов · число соединений не является объёмом трафика")
        row = QHBoxLayout()
        self.metrics = {}
        for key,title in [("total","Сокетов сейчас"),("new","Новых за опрос"),("unique_ips","Уникальных IP сейчас")]:
            frame,value = metric(title)
            self.metrics[key]=value
            row.addWidget(frame)
        layout.addLayout(row)
        self.timeline = Timeline()
        layout.addWidget(card("Соединения во времени · голубой: всего / фиолетовый: новых · последние 180 опросов",self.timeline))
        row = QHBoxLayout()
        self.apps,self.protocols,self.countries = Bars(),Bars(),Bars()
        row.addWidget(card("Топ приложений · сокеты",self.apps))
        row.addWidget(card("Протоколы · сокеты",self.protocols))
        layout.addLayout(row)
        layout.addWidget(card("Страны · уникальные публичные IP текущего опроса",self.countries))
        diag = QWidget()
        d = QVBoxLayout(diag)
        d.setContentsMargins(0,0,0,0)
        d.addWidget(label("Ручная TCP-проверка: время установления соединения, не ICMP RTT. Доля неудач не равнозначна потерям пакетов. Запросы выполняются только после нажатия кнопки; сервер увидит ваш IP.","subheading",True))
        toolbar = QHBoxLayout()
        self.host = QLineEdit()
        self.host.setPlaceholderText("IP или домен для ручной проверки")
        self.port = QSpinBox()
        self.port.setRange(1,65535)
        self.port.setValue(443)
        self.run = QPushButton("Проверить TCP")
        self.run.setObjectName("primary")
        self.cancel = QPushButton("Остановить")
        self.cancel.setEnabled(False)
        toolbar.addWidget(self.host,1)
        toolbar.addWidget(label("Порт"))
        toolbar.addWidget(self.port)
        toolbar.addWidget(self.run)
        toolbar.addWidget(self.cancel)
        d.addLayout(toolbar)
        self.progress = label("Проверки не запускаются автоматически","subheading")
        d.addWidget(self.progress)
        self.results = QTextBrowser()
        self.results.setMinimumHeight(190)
        d.addWidget(self.results)
        layout.addWidget(card("Диагностика задержек · TCP",diag))
        self.run.clicked.connect(lambda: self.probe_requested.emit(self.host.text(),self.port.value()))
        self.cancel.clicked.connect(self.cancel_requested)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def update_data(self, payload):
        for key,value in self.metrics.items():
            value.setText(str(payload['new'] if key=='new' else payload['stats'][key]))
        self.timeline.set_samples(payload['samples'])
        self.apps.set_values(payload['stats']['apps'])
        self.protocols.set_values(payload['stats']['protocols'])
        self.countries.set_values(payload['stats']['countries'])

    def show_diagnostics(self, results):
        text = ''
        for r in results:
            esc = html.escape
            text += '<h3>'+esc(r['host'])+':'+str(r['port'])+' · '+display_time(r['time'])+'</h3>'
            text += '<p>TCP · '+esc(r['address'])+' · успешных '+str(r['success'])+'/'+str(r['attempts'])
            text += ' · неудачных '+str(r['failure_percent'])+'%</p>'
            text += '<p>Минимум / среднее / максимум: '+' / '.join(str(r[k]) if r[k] is not None else '—' for k in ('min_ms','avg_ms','max_ms'))+' мс</p>'
            if r.get('cancelled'):
                text += '<p>Проверка остановлена пользователем.</p>'
            if any(r.get('errors',[])):
                text += '<p>'+esc(next(e for e in r['errors'] if e))+'</p>'
        self.results.setHtml(text or '<p>Сохранённых проверок нет.</p>')
