from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QLineEdit, QMenu, QPushButton, QSplitter, QTableView, QTextBrowser, QVBoxLayout, QWidget, QStackedWidget, QFileDialog, QAbstractItemView
from netmap.ui.context import ContextPanel
from netmap.ui.connection_explorer import ConnectionExplorer
from netmap.core.export import write_csv
from dataclasses import asdict
from netmap.ui.common import simple_connection_html, friendly_name, connection_html, label, page_header, setup_table
from netmap.ui.table import ConnectionFilter, ConnectionModel


class ConnectionsPage(QWidget):
    history_requested=Signal(str)
    map_requested=Signal(str)
    app_requested=Signal(str)
    ip_connections_requested=Signal(str)
    export_requested=Signal(object)
    def __init__(self):
        super().__init__()
        self.mode="simple"
        self.context_dismissed=False
        self.simple_technical=False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28,24,28,24)
        page_header(layout,"Соединения","Программы и адреса, обнаруженные на вашем компьютере")
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по IP, приложению, PID или состоянию…")
        self.search.setToolTip('IP — адрес в сети. Порт — номер сетевой службы. Локальный адрес относится к этому компьютеру; удалённый — к другой стороне сокета.')
        self.protocol = QComboBox()
        self.protocol.addItems(["Все протоколы","TCP","UDP"])
        self.apps = QComboBox()
        self.apps.addItem("Все приложения","")
        self.apps.setToolTip('Программа — владелец наблюдаемого сокета. Прокси может быть посредником: адрес сокета не всегда совпадает с конечным сервером.')
        self.protocol.setToolTip('TCP и UDP — способы обмена данными. UDP без удалённого адреса — открытый сокет, а не установленное подключение.')
        toolbar.addWidget(self.search,1)
        toolbar.addWidget(self.protocol)
        toolbar.addWidget(self.apps)
        self.column_button=QPushButton("Столбцы")
        self.column_button.clicked.connect(self.columns_menu)
        toolbar.addWidget(self.column_button)
        self.export_button=QPushButton("CSV")
        self.export_button.clicked.connect(self.export_csv)
        toolbar.addWidget(self.export_button)
        copy = QPushButton("Копировать IP")
        self.copy_button=copy
        copy.clicked.connect(self.copy_ip)
        toolbar.addWidget(copy)
        layout.addLayout(toolbar)
        self.advanced=QWidget(); advanced_layout=QHBoxLayout(self.advanced); advanced_layout.setContentsMargins(0,0,0,0)
        self.pid=QLineEdit(); self.pid.setPlaceholderText('PID'); self.pid.setMaximumWidth(130)
        from PySide6.QtGui import QIntValidator
        self.pid.setValidator(QIntValidator(0,2147483647,self))
        self.state=QComboBox(); self.state.addItems(['Все состояния','ESTABLISHED','LISTEN','SYN_SENT','CLOSE_WAIT','TIME_WAIT','UDP · открытый сокет'])
        self.family=QComboBox(); self.family.addItems(['IPv4 / IPv6','IPv4','IPv6'])
        advanced_layout.addWidget(self.pid); advanced_layout.addWidget(self.state); advanced_layout.addWidget(self.family); advanced_layout.addStretch()
        for widget in (self.pid,self.state,self.family): widget.setToolTip('Фильтры применяются одновременно с поиском, протоколом и программой')
        self.pid.textChanged.connect(self.filter); self.state.currentIndexChanged.connect(self.filter); self.family.currentIndexChanged.connect(self.filter)
        layout.addWidget(self.advanced)
        split = QSplitter()
        self.table = QTableView()
        self.model = ConnectionModel(self)
        self.proxy = ConnectionFilter(self)
        self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy)
        setup_table(self.table)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for col,width in enumerate([180,75,90,190,180,70,180,140,145]):
            self.table.setColumnWidth(col,width)
        self.table.sortByColumn(0,Qt.SortOrder.AscendingOrder)
        self.groups=ConnectionExplorer()
        self.views=QStackedWidget(); self.views.addWidget(self.groups); self.views.addWidget(self.table)
        self.panel=ContextPanel('Подключение')
        self.detail=self.panel.content
        self.panel.closed.connect(lambda:setattr(self,'context_dismissed',True))
        self.detail.anchorClicked.connect(self.detail_action)
        for title,signal in [('На карте',self.map_requested),('История',self.history_requested)]:
            button=QPushButton(title); button.clicked.connect(lambda checked=False,target=signal:self.emit_ip(target)); self.panel.actions.addWidget(button)
        split.addWidget(self.views); split.addWidget(self.panel)
        self.groups.selected.connect(self.show_group)
        split.setSizes([850,300])
        layout.addWidget(split,1)
        self.count = label("Ожидание первого опроса","subheading")
        layout.addWidget(self.count)
        self.search.textChanged.connect(self.filter)
        self.protocol.currentIndexChanged.connect(self.filter)
        self.apps.currentIndexChanged.connect(self.filter)
        self.table.selectionModel().selectionChanged.connect(self.selection_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.menu)

    def filter(self):
        self.groups.set_app_filter(self.apps.currentData() or '')
        self.proxy.set_filters(self.search.text(),self.protocol.currentText() if self.protocol.currentIndex() else "",self.apps.currentData() or "",pid=int(self.pid.text()) if self.pid.text() else None,state=self.state.currentText() if self.state.currentIndex() else "",family=self.family.currentText() if self.family.currentIndex() else "")
        self.count.setText(f"Показано: {self.proxy.rowCount()} из {len(self.model.rows)} наблюдаемых сокетов")

    def selected(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        source = self.proxy.mapToSource(idx)
        return self.model.rows[source.row()]

    def show_detail(self):
        c = self.selected()
        if c and self.mode=="expert" and not self.context_dismissed:
            self.panel.show_html(connection_html(c))
        else:
            if not c: self.panel.hide()

    def copy_ip(self):
        row=self.groups.current()
        c = self.selected() if self.mode=="expert" else (next((c for c in row["connections"] if c.remote_ip),row["connections"][0]) if row else None)
        if c:
            QApplication.clipboard().setText(c.remote_ip or c.local_ip)

    def menu(self, pos):
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        self.table.setCurrentIndex(idx)
        menu = QMenu(self)
        menu.addAction("Копировать IP",self.copy_ip)
        menu.addAction('Копировать технические данные',self.copy_technical)
        menu.addAction('Экспорт выбранных строк…',lambda:self.export_csv(selected_only=True))
        menu.addAction("Показать на карте",lambda:self.emit_ip(self.map_requested))
        menu.addAction("Найти в истории",lambda:self.emit_ip(self.history_requested))
        menu.addAction("Открыть программу",lambda:self.app_requested.emit(self.selected().app_key) if self.selected() else None)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def update_data(self, connections):
        selected_keys={self.model.rows[self.proxy.mapToSource(i).row()].key for i in self.table.selectionModel().selectedRows()}
        selected = self.selected()
        key = selected.key if selected else None
        scroll = self.table.verticalScrollBar().value()
        self.model.update(connections)
        self.groups.update_data(connections)
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
                        from PySide6.QtCore import QItemSelectionModel
                        self.table.selectionModel().setCurrentIndex(idx,QItemSelectionModel.SelectionFlag.NoUpdate)
                    break
        from PySide6.QtCore import QItemSelectionModel
        for i,c in enumerate(self.model.rows):
            if c.key in selected_keys:
                idx=self.proxy.mapFromSource(self.model.index(i,0))
                if idx.isValid(): self.table.selectionModel().select(idx,QItemSelectionModel.SelectionFlag.Select|QItemSelectionModel.SelectionFlag.Rows)
        self.table.verticalScrollBar().setValue(scroll)
        if self.mode=='expert': self.show_detail()
        elif self.groups.current() and not self.context_dismissed: self.render_group()
        elif not self.groups.current(): self.panel.hide()

    def set_mode(self,mode):
        self.mode=mode; expert=mode=='expert'; self.views.setCurrentIndex(int(expert))
        for w in (self.search,self.protocol,self.column_button,self.export_button,self.copy_button): w.setVisible(expert)
        self.advanced.setVisible(expert)
        self.panel.hide()
        if expert: self.show_detail()
        elif self.groups.current(): self.show_group(self.groups.current()['key'])

    def show_group(self,key):
        self.context_dismissed=False; self.simple_technical=False
        self.render_group()

    def render_group(self):
        import html
        row=self.groups.current()
        if not row: return
        if self.simple_technical:
            self.panel.show_html("".join(connection_html(c) for c in row["connections"])); return
        ips=''.join('<p>'+html.escape(ip)+' · <a href="copy:'+ip+'">копировать</a> · <a href="map:'+ip+'">карта</a> · <a href="history:'+ip+'">история</a></p>' for ip in row['public_ips']) or 'Публичные адреса не обнаружены'
        text=f"<h2>{html.escape(friendly_name(row['name']))}</h2><p>{row['count']} наблюдаемых подключений</p><h3>Публичные адреса</h3>{ips}<p>Локальных и служебных сокетов: {row['local_count']}</p>"
        from netmap.ui.ip_details import ip_html
        remote=next((c.remote_ip for c in row['connections'] if c.remote_ip),'')
        if remote: text+=ip_html(remote,row['connections'])
        text+='<p><a href="technical">Раскрыть технические сведения</a></p>'
        self.panel.show_html(text)

    def show_technical(self):
        self.simple_technical=True
        self.render_group()

    def emit_ip(self,signal):
        c=self.selected() if self.mode=='expert' else (self.groups.current()['connections'][0] if self.groups.current() else None)
        if c: signal.emit(c.remote_ip or c.local_ip)

    def columns_menu(self):
        from netmap.ui.table import COLUMNS
        menu=QMenu(self)
        for i,title in enumerate(COLUMNS):
            action=menu.addAction(title); action.setCheckable(True); action.setChecked(not self.table.isColumnHidden(i))
            action.triggered.connect(lambda checked,col=i:self.table.setColumnHidden(col,not checked))
        menu.exec(self.column_button.mapToGlobal(self.column_button.rect().bottomLeft()))

    def copy_technical(self):
        from netmap.ui.table import values
        QApplication.clipboard().setText("\n".join("\t".join(map(str,values(self.model.rows[self.proxy.mapToSource(i).row()]))) for i in self.table.selectionModel().selectedRows()))

    def export_csv(self,checked=False,selected_only=False):
        path,_=QFileDialog.getSaveFileName(self,'Экспорт соединений','connections.csv','CSV (*.csv)')
        if not path: return
        indexes=self.table.selectionModel().selectedRows() if selected_only else [self.proxy.index(i,0) for i in range(self.proxy.rowCount())]
        rows=[asdict(self.model.rows[self.proxy.mapToSource(i).row()]) for i in indexes]
        self.export_requested.emit({'path':path,'rows':rows,'columns':['process','pid','protocol','local_ip','local_port','remote_ip','remote_port','status','first_seen','observed']})

    def selection_changed(self):
        self.context_dismissed=False
        self.show_detail()

    def detail_action(self,url):
        value=url.toString()
        if value.startswith('copy:'): QApplication.clipboard().setText(value[5:])
        elif value.startswith('map:'): self.map_requested.emit(value[4:])
        elif value.startswith('history:'): self.history_requested.emit(value[8:])
        elif value.startswith('connections:'): self.ip_connections_requested.emit(value[12:])
        else: self.show_technical()
