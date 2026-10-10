from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QLineEdit, QMenu, QPushButton, QSplitter, QTableView, QTextBrowser, QVBoxLayout, QWidget
from netmap.ui.common import connection_html, label, page_header, setup_table
from netmap.ui.table import ConnectionFilter, ConnectionModel


class ConnectionsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28,24,28,24)
        page_header(layout,"Соединения","Реальные TCP-соединения и доступные UDP-сокеты · периодический опрос")
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по IP, приложению, PID или состоянию…")
        self.protocol = QComboBox()
        self.protocol.addItems(["Все протоколы","TCP","UDP"])
        self.apps = QComboBox()
        self.apps.addItem("Все приложения","")
        toolbar.addWidget(self.search,1)
        toolbar.addWidget(self.protocol)
        toolbar.addWidget(self.apps)
        copy = QPushButton("Копировать IP")
        copy.clicked.connect(self.copy_ip)
        toolbar.addWidget(copy)
        layout.addLayout(toolbar)
        split = QSplitter()
        self.table = QTableView()
        self.model = ConnectionModel(self)
        self.proxy = ConnectionFilter(self)
        self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy)
        setup_table(self.table)
        for col,width in enumerate([180,75,90,190,180,70,180,140,145]):
            self.table.setColumnWidth(col,width)
        self.table.sortByColumn(0,Qt.SortOrder.AscendingOrder)
        self.detail = QTextBrowser()
        self.detail.setMinimumWidth(270)
        self.detail.setHtml("<h3>Сведения о соединении</h3><p>Выберите строку в таблице.</p>")
        split.addWidget(self.table)
        split.addWidget(self.detail)
        split.setSizes([850,300])
        layout.addWidget(split,1)
        self.count = label("Ожидание первого опроса","subheading")
        layout.addWidget(self.count)
        self.search.textChanged.connect(self.filter)
        self.protocol.currentIndexChanged.connect(self.filter)
        self.apps.currentIndexChanged.connect(self.filter)
        self.table.selectionModel().selectionChanged.connect(self.show_detail)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.menu)

    def filter(self):
        self.proxy.set_filters(self.search.text(),self.protocol.currentText() if self.protocol.currentIndex() else "",self.apps.currentData() or "")
        self.count.setText(f"Показано: {self.proxy.rowCount()} из {len(self.model.rows)} наблюдаемых сокетов")

    def selected(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        source = self.proxy.mapToSource(idx)
        return self.model.rows[source.row()]

    def show_detail(self):
        c = self.selected()
        if c:
            self.detail.setHtml(connection_html(c))
        else:
            self.detail.setHtml("<p>Соединение больше не наблюдается либо скрыто фильтром.</p>")

    def copy_ip(self):
        c = self.selected()
        if c:
            QApplication.clipboard().setText(c.remote_ip or c.local_ip)

    def menu(self, pos):
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        self.table.setCurrentIndex(idx)
        menu = QMenu(self)
        menu.addAction("Копировать IP",self.copy_ip)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def update_data(self, connections):
        selected = self.selected()
        key = selected.key if selected else None
        scroll = self.table.verticalScrollBar().value()
        self.model.update(connections)
        apps = sorted({c.app_key:c.process for c in connections}.items(),key=lambda p:p[1].casefold())
        old_key = self.apps.currentData()
        if old_key and old_key not in dict(apps):
            apps.append((old_key,self.apps.currentText()))
        desired = [("Все приложения","")] + [(name,key) for key,name in apps]
        existing = [(self.apps.itemText(i),self.apps.itemData(i)) for i in range(self.apps.count())]
        if desired != existing:
            old = self.apps.currentData()
            self.apps.blockSignals(True)
            self.apps.clear()
            for name,value in desired:
                self.apps.addItem(name,value)
            self.apps.setCurrentIndex(max(0,self.apps.findData(old)))
            self.apps.blockSignals(False)
        self.filter()
        if key:
            for row,c in enumerate(self.model.rows):
                if c.key == key:
                    idx = self.proxy.mapFromSource(self.model.index(row,0))
                    if idx.isValid():
                        self.table.setCurrentIndex(idx)
                    break
        self.table.verticalScrollBar().setValue(scroll)
        self.show_detail()
