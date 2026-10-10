import html
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPushButton, QScrollArea, QSpinBox, QTextBrowser, QVBoxLayout, QWidget
from netmap.ui.common import card, label, metric, page_header
from netmap.widgets.charts import Bars, Timeline
from netmap.ui.table import display_time


class AnalyticsPage(QWidget):
    period_requested = Signal(int)
    probe_requested = Signal(str,int)
    cancel_requested = Signal()
    map_requested=Signal(str)
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
        self.mode='simple'
        self.period=QComboBox()
        for text,seconds in [('Последние 15 минут',900),('Последний час',3600),('Последний день',86400),('Доступная история',0)]: self.period.addItem(text,seconds)
        self.period.currentIndexChanged.connect(lambda:self.period_requested.emit(self.period.currentData()))
        layout.addWidget(self.period)
        row = QHBoxLayout()
        self.metrics = {}
        for key,title in [("total","Сейчас подключений"),("new","Новых публичных IP за период"),("unique_ips","Удалённых IP за период")]:
            frame,value = metric(title)
            self.metrics[key]=value
            row.addWidget(frame)
        layout.addLayout(row)
        self.timeline = Timeline()
        layout.addWidget(card("Подключения во времени · основная линия: всего / янтарная: новые наблюдения · единица: сокеты",self.timeline))
        row = QHBoxLayout()
        self.apps,self.protocols,self.countries = Bars(),Bars(),Bars()
        row.addWidget(card("Программы · сеансы за период",self.apps))
        row.addWidget(card("Протоколы · сеансы за период",self.protocols))
        layout.addLayout(row)
        layout.addWidget(card("География · публичные IP за период",self.countries))
        self.new_addresses=QTextBrowser(); self.new_addresses.setMaximumHeight(220); self.new_addresses.anchorClicked.connect(lambda url:self.map_requested.emit(url.toString()[3:]))
        layout.addWidget(card('Новые публичные адреса · впервые в сохранённой истории',self.new_addresses))
        diag = QWidget()
        d = QVBoxLayout(diag)
        d.setContentsMargins(0,0,0,0)
        self.diagnostic_hint=label("Ручная TCP-проверка: время установления соединения, не ICMP RTT. Доля неудач не равнозначна потерям пакетов. Запросы выполняются только после нажатия кнопки; сервер увидит ваш IP.","subheading",True)
        d.addWidget(self.diagnostic_hint)
        toolbar = QHBoxLayout()
        self.host = QLineEdit()
        self.host.setPlaceholderText("IP или домен для ручной проверки")
        self.port = QSpinBox()
        self.port.setRange(1,65535)
        self.port.setValue(443)
        self.run = QPushButton("Проверить соединение")
        self.run.setObjectName("primary")
        self.cancel = QPushButton("Остановить")
        self.cancel.setEnabled(False)
        toolbar.addWidget(self.host,1)
        self.port_label=label("Порт")
        toolbar.addWidget(self.port_label)
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

    def update_data(self,payload):
        self.metrics['total'].setText(str(payload['stats']['total']))

    def set_mode(self,mode):
        self.mode=mode; self.port.setVisible(mode=='expert'); self.port_label.setVisible(mode=='expert')
        self.run.setText('Проверить TCP' if mode=='expert' else 'Проверить соединение')
        self.diagnostic_hint.setText('Проверка открывает соединение к выбранному адресу. Сервер видит ваш IP. Измеряется время TCP-подключения, а не ICMP-пинг.' if mode=='simple' else 'TCP: минимум, среднее, максимум времени установления соединения и доля неудачных попыток. Это не ICMP RTT и не потери пакетов.')
        if hasattr(self,'diagnostic_results'): self.show_diagnostics(self.diagnostic_results)

    def show_period(self,payload):
        if payload['seconds']!=self.period.currentData(): return
        self.metrics['new'].setText(str(payload['new_ips']) if payload['available'] else '—')
        self.metrics['unique_ips'].setText(str(payload['unique_ips']) if payload['available'] else '—')
        self.metrics['new'].setToolTip('IP впервые появился в выбранном периоде относительно сохранённой истории. Удалённая история не учитывается.')
        self.new_addresses.setHtml(''.join('<p><a href="ip:'+html.escape(row['remote_ip'],quote=True)+'">'+html.escape(row['remote_ip'])+'</a> · '+html.escape(', '.join(row['apps']))+' · '+html.escape(row['country'] or 'Страна не определена')+' · '+display_time(row['first_seen'])+'</p>' for row in payload.get('new_addresses',[])) or '<p>Новых адресов в выбранном периоде не найдено.</p>')
        self.timeline.set_samples(payload['samples'])
        self.apps.set_values(payload['apps']); self.protocols.set_values(payload['protocols']); self.countries.set_values(payload['countries'])

    def show_diagnostics(self, results):
        self.diagnostic_results=results
        text = ''
        for r in results:
            esc = html.escape
            text += '<h3>'+esc(r['host'])+':'+str(r['port'])+' · '+display_time(r['time'])+'</h3>'
            text += '<p>TCP · '+esc(r['address'])+' · успешных '+str(r['success'])+'/'+str(r['attempts'])
            text += ' · неудачных '+str(r['failure_percent'])+'%</p>'
            text += '<p>Минимум / среднее / максимум: '+' / '.join(str(r[k]) if r[k] is not None else '—' for k in ('min_ms','avg_ms','max_ms'))+' мс</p>'
            if r.get('cancelled'):
                text += '<p>Проверка остановлена пользователем.</p>'
            if self.mode=='expert' and any(r.get('errors',[])):
                text += '<p>'+esc(next(e for e in r['errors'] if e))+'</p>'
        self.results.setHtml(text or '<p>Сохранённых проверок нет.</p>')
