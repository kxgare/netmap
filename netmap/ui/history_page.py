import html
from datetime import datetime, time, timezone
from PySide6.QtCore import QDate, QTimer, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QDateEdit, QHBoxLayout, QLineEdit, QPushButton, QSplitter, QTableView, QTextBrowser, QVBoxLayout, QWidget
from netmap.ui.common import label, page_header, setup_table
from netmap.ui.table import display_time


class HistoryPage(QWidget):
    requested = Signal(object)
    clear_requested = Signal()
    def __init__(self):
        super().__init__()
        self.rows = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28,24,28,24)
        page_header(layout,"История","Локальные сеансы наблюдения · паузы и пропущенные короткие соединения не означают отсутствие активности")
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("IP или название процесса…")
        self.since = QDateEdit(QDate.currentDate().addDays(-30))
        self.until = QDateEdit(QDate.currentDate())
        for date in (self.since,self.until):
            date.setCalendarPopup(True)
            date.setDisplayFormat("dd.MM.yyyy")
        bar.addWidget(self.search,1)
        bar.addWidget(label("С"))
        bar.addWidget(self.since)
        bar.addWidget(label("По"))
        bar.addWidget(self.until)
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.query)
        bar.addWidget(refresh)
        clear = QPushButton("Очистить…")
        clear.clicked.connect(self.clear_requested)
        bar.addWidget(clear)
        layout.addLayout(bar)
        split = QSplitter()
        self.table = QTableView()
        self.model = QStandardItemModel(self)
        self.model.setHorizontalHeaderLabels(["Приложение","PID","IP","Порт","Протокол","Наблюдение","Страна","Первое","Последнее"])
        self.model.setSortRole(Qt.ItemDataRole.UserRole)
        self.table.setModel(self.model)
        setup_table(self.table)
        self.table.setColumnWidth(0,180)
        self.table.setColumnWidth(2,180)
        self.table.setColumnWidth(5,150)
        self.detail = QTextBrowser()
        self.detail.setMinimumWidth(250)
        split.addWidget(self.table)
        split.addWidget(self.detail)
        split.setSizes([900,270])
        layout.addWidget(split,1)
        self.count = label("Поиск выполняется в фоне. Показаны до 1000 последних результатов.","subheading")
        layout.addWidget(self.count)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(350)
        self.debounce.timeout.connect(self.query)
        self.search.textChanged.connect(lambda: self.debounce.start())
        self.since.dateChanged.connect(lambda: self.debounce.start())
        self.until.dateChanged.connect(lambda: self.debounce.start())
        self.table.selectionModel().selectionChanged.connect(self.show_detail)

    def query(self):
        if self.since.date()>self.until.date():
            self.count.setText("Начало периода должно предшествовать окончанию")
            return
        start = datetime.combine(self.since.date().toPython(),time.min).astimezone(timezone.utc).isoformat(timespec="milliseconds")
        end = datetime.combine(self.until.date().toPython(),time.max).astimezone(timezone.utc).isoformat(timespec="milliseconds")
        self.last_query = {"search":self.search.text(),"since":start,"until":end,"_target":"history"}
        self.requested.emit(self.last_query)

    def show_rows(self, payload):
        if payload["query"] and payload["query"] != getattr(self,"last_query",{}):
            return
        self.rows = payload["rows"]
        self.table.setSortingEnabled(False)
        self.model.removeRows(0,self.model.rowCount())
        for r in self.rows:
            values = [r['process'],r['pid'] if r['pid'] is not None else '—',r['remote_ip'] or '—',
                      r['remote_port'] if r['remote_ip'] else '—',r['protocol'],
                      'Наблюдается' if r['active'] else 'Наблюдение завершено',r['country'] or '—',
                      display_time(r['first_seen']),display_time(r['last_seen'])]
            items = []
            for col,value in enumerate(values):
                item = QStandardItem(str(value))
                item.setData(r['id'],Qt.ItemDataRole.UserRole+1)
                item.setData(r['first_seen'] if col==7 else r['last_seen'] if col==8 else value,Qt.ItemDataRole.UserRole)
                items.append(item)
            self.model.appendRow(items)
        self.table.setSortingEnabled(True)
        self.count.setText(f"Найдено: {len(self.rows)} (не более 1000). Время отображается в часовом поясе компьютера.")

    def show_detail(self):
        index = self.table.currentIndex()
        if not index.isValid():
            return
        sid = self.model.item(index.row(),0).data(Qt.ItemDataRole.UserRole+1)
        r = next((row for row in self.rows if row['id']==sid),None)
        if r:
            titles = {'process':'Процесс','pid':'PID','executable':'Исполняемый файл','protocol':'Протокол',
                      'local_ip':'Локальный IP','local_port':'Локальный порт','remote_ip':'Удалённый IP',
                      'remote_port':'Удалённый порт','status':'Последнее состояние','first_seen':'Первое обнаружение',
                      'last_seen':'Последнее обнаружение','country':'Страна','city':'Город','accuracy_km':'Радиус геолокации, км'}
            self.detail.setHtml('<h3>Сеанс наблюдения</h3>'+''.join('<p><span style="color:#829cba">'+title+'</span><br>'+html.escape(str(r[key] if r[key] is not None else '—'))+'</p>' for key,title in titles.items())+'<p>Геолокация приблизительная. Завершение наблюдения не доказывает закрытие сокета.</p>')
