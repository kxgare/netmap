import html
from datetime import datetime,time,timezone
from collections import defaultdict
from PySide6.QtCore import QDate,QTimer,Qt,Signal
from PySide6.QtGui import QStandardItem,QStandardItemModel
from PySide6.QtWidgets import QComboBox,QDateEdit,QHBoxLayout,QLineEdit,QPushButton,QSplitter,QTableView,QTreeWidget,QTreeWidgetItem,QStackedWidget,QVBoxLayout,QWidget,QFileDialog
from netmap.ui.common import label,page_header,setup_table,friendly_name
from netmap.ui.context import ContextPanel
from netmap.ui.table import display_time

class HistoryPage(QWidget):
    requested=Signal(object)
    export_requested=Signal(object)
    clear_requested=Signal()
    map_requested=Signal(str)
    app_requested=Signal(str)
    PAGE_SIZE=100
    def __init__(self):
        super().__init__(); self.mode='simple'; self.rows=[]; self.offset=0; self.total=0; self.app_filter=''; self.sort='last_seen'; self.descending=True
        layout=QVBoxLayout(self); layout.setContentsMargins(24,22,24,20)
        page_header(layout,'История','Сеансы наблюдения, сохранённые на этом компьютере')
        bar=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText('Найти программу или адрес…')
        self.since=QDateEdit(QDate.currentDate().addDays(-30)); self.until=QDateEdit(QDate.currentDate())
        for d in (self.since,self.until): d.setCalendarPopup(True); d.setDisplayFormat('dd.MM.yyyy')
        bar.addWidget(self.search,1); bar.addWidget(label('С')); bar.addWidget(self.since); bar.addWidget(label('По')); bar.addWidget(self.until)
        refresh=QPushButton('Обновить'); refresh.clicked.connect(lambda:self.query()); bar.addWidget(refresh)
        export=QPushButton('Экспорт CSV'); export.clicked.connect(self.export_csv); bar.addWidget(export)
        layout.addLayout(bar)
        self.advanced=QWidget(); adv=QHBoxLayout(self.advanced); adv.setContentsMargins(0,0,0,0)
        self.pid=QLineEdit(); self.pid.setPlaceholderText('PID'); self.pid.setMaximumWidth(100)
        self.ip=QLineEdit(); self.ip.setPlaceholderText('Точный удалённый IP')
        self.protocol=QComboBox(); self.protocol.addItems(['Все протоколы','TCP','UDP'])
        adv.addWidget(self.pid); adv.addWidget(self.ip,1); adv.addWidget(self.protocol); layout.addWidget(self.advanced)
        reset=QPushButton('Сбросить фильтры'); reset.clicked.connect(self.reset_filters)
        filters=QHBoxLayout(); self.filter_note=label('','subheading'); filters.addWidget(self.filter_note,1); filters.addWidget(reset); layout.addLayout(filters)
        self.split=QSplitter(); self.views=QStackedWidget(); self.tree=QTreeWidget(); self.tree.setHeaderLabels(['Программа / сеанс','Время','Наблюдений']); self.tree.setColumnWidth(0,320); self.tree.setColumnWidth(1,280)
        self.table=QTableView(); self.model=QStandardItemModel(self); self.model.setHorizontalHeaderLabels(['Программа','PID','Удалённый IP','Порт','Протокол','Состояние','Страна','Первое','Последнее'])
        self.table.setModel(self.model); setup_table(self.table); self.table.setSortingEnabled(False)
        for i,w in enumerate([180,75,175,75,85,140,120,140,140]): self.table.setColumnWidth(i,w)
        self.table.horizontalHeader().setSortIndicatorShown(True); self.table.horizontalHeader().setSortIndicator(8,Qt.SortOrder.DescendingOrder)
        self.table.horizontalHeader().sectionClicked.connect(self.change_sort)
        self.views.addWidget(self.tree); self.views.addWidget(self.table)
        self.panel=ContextPanel('Сеанс'); self.detail=self.panel.content
        self.detail.anchorClicked.connect(lambda url:self.show_detail(True))
        for title,signal in [('На карте',self.map_requested),('Программа',self.app_requested)]:
            b=QPushButton(title); b.clicked.connect(lambda checked=False,target=signal:self.context_action(target)); self.panel.actions.addWidget(b)
        self.split.addWidget(self.views); self.split.addWidget(self.panel); layout.addWidget(self.split,1)
        bottom=QHBoxLayout(); self.count=label('История пока пуста','subheading'); bottom.addWidget(self.count,1)
        self.prev=QPushButton('←'); self.next=QPushButton('→'); self.prev.setToolTip('Предыдущая страница'); self.next.setToolTip('Следующая страница')
        self.prev.clicked.connect(lambda:self.turn_page(-1)); self.next.clicked.connect(lambda:self.turn_page(1)); bottom.addWidget(self.prev); bottom.addWidget(self.next)
        clear=QPushButton('Очистить…'); clear.clicked.connect(self.clear_requested); bottom.addWidget(clear); layout.addLayout(bottom)
        self.debounce=QTimer(self); self.debounce.setSingleShot(True); self.debounce.setInterval(300); self.debounce.timeout.connect(self.query)
        for w in (self.search,self.pid,self.ip): w.textChanged.connect(lambda:self.debounce.start())
        for d in (self.since,self.until): d.dateChanged.connect(lambda:self.debounce.start())
        self.protocol.currentIndexChanged.connect(lambda:self.debounce.start())
        self.table.selectionModel().selectionChanged.connect(lambda:self.show_detail())
        self.tree.itemSelectionChanged.connect(lambda:self.show_detail())
    def set_mode(self,mode):
        chosen=self.selected_row()
        self.mode=mode; self.advanced.setVisible(mode=='expert'); self.views.setCurrentIndex(int(mode=='expert')); self.panel.hide()
        if chosen:
            for i,r in enumerate(self.rows):
                if r['id']==chosen['id']: self.table.setCurrentIndex(self.model.index(i,0)); break
            for i in range(self.tree.topLevelItemCount()):
                parent=self.tree.topLevelItem(i)
                for j in range(parent.childCount()):
                    if parent.child(j).data(0,Qt.ItemDataRole.UserRole)==chosen['id']: self.tree.setCurrentItem(parent.child(j)); parent.setExpanded(True)
            self.show_detail()
    def reset_filters(self):
        self.app_filter=''
        for w in (self.search,self.pid,self.ip): w.clear()
        self.protocol.setCurrentIndex(0); self.query()
    def find_ip(self,ip):
        self.reset_filters(); self.search.setText(ip); self.query()
    def filter_app(self,key):
        self.app_filter=key; self.query()
    def query(self,reset=True):
        if reset: self.offset=0
        if self.since.date()>self.until.date(): self.count.setText('Проверьте порядок дат'); return
        if self.pid.text() and not self.pid.text().isdigit(): self.count.setText('PID должен быть числом'); return
        start=datetime.combine(self.since.date().toPython(),time.min).astimezone(timezone.utc).isoformat(timespec='milliseconds')
        end=datetime.combine(self.until.date().toPython(),time.max).astimezone(timezone.utc).isoformat(timespec='milliseconds')
        self.last_query={'search':self.search.text(),'since':start,'until':end,'app':self.app_filter,'pid':int(self.pid.text()) if self.pid.text() else None,
                         'ip':self.ip.text().strip(),'protocol':self.protocol.currentText() if self.protocol.currentIndex() else '',
                         'limit':self.PAGE_SIZE,'offset':self.offset,'sort':self.sort,'descending':self.descending,'_target':'history'}
        self.filter_note.setText('Фильтр программы: '+self.app_filter if self.app_filter else ('Дополнительные фильтры применены' if self.pid.text() or self.ip.text() or self.protocol.currentIndex() else 'Каждый раскрываемый пункт — отдельный сеанс'))
        self.requested.emit(self.last_query)
    def turn_page(self,step):
        self.offset=max(0,self.offset+step*self.PAGE_SIZE); self.query(False)
    def change_sort(self,column):
        columns={0:'process',1:'pid',2:'remote_ip',3:'remote_port',4:'protocol',6:'country',7:'first_seen',8:'last_seen'}
        if column not in columns: return
        new=columns[column]; self.descending=not self.descending if self.sort==new else True; self.sort=new
        self.table.horizontalHeader().setSortIndicator(column,Qt.SortOrder.DescendingOrder if self.descending else Qt.SortOrder.AscendingOrder); self.query()
    def selected_row(self):
        if self.mode=='simple':
            item=self.tree.currentItem(); sid=item.data(0,Qt.ItemDataRole.UserRole) if item else None
        else:
            index=self.table.currentIndex(); sid=self.model.item(index.row(),0).data(Qt.ItemDataRole.UserRole) if index.isValid() else None
        return next((r for r in self.rows if r['id']==sid),None)
    def show_rows(self,payload):
        if payload['query'] and payload['query']!=getattr(self,'last_query',{}): return
        chosen=self.selected_row(); chosen_id=chosen['id'] if chosen else None
        expanded={self.tree.topLevelItem(i).text(0) for i in range(self.tree.topLevelItemCount()) if self.tree.topLevelItem(i).isExpanded()}
        self.rows=payload['rows']; self.total=payload.get('total',len(self.rows))
        self.model.removeRows(0,self.model.rowCount()); self.tree.blockSignals(True); self.tree.clear()
        groups=defaultdict(list)
        for r in self.rows:
            values=[r['process'],r['pid'] if r['pid'] is not None else '—',r['remote_ip'] or '—',r['remote_port'],r['protocol'],
                    'Наблюдается' if r['active'] else 'Завершено',r['country'] or '—',display_time(r['first_seen']),display_time(r['last_seen'])]
            items=[QStandardItem(str(v)) for v in values]
            for item in items: item.setData(r['id'],Qt.ItemDataRole.UserRole)
            self.model.appendRow(items)
            if r['id']==chosen_id: self.table.setCurrentIndex(self.model.index(self.model.rowCount()-1,0))
            groups[(r['executable'] or r['process'],r['first_seen'][:10])].append(r)
        for (_,day),rows in groups.items():
            title=friendly_name(rows[0]['process'])+' · '+day
            parent=QTreeWidgetItem([title,'',str(len(rows))]); self.tree.addTopLevelItem(parent)
            parent.setExpanded(title in expanded)
            for r in rows:
                child=QTreeWidgetItem([r['remote_ip'] or 'Локальное подключение',display_time(r['first_seen'])+' → '+display_time(r['last_seen']),'Сеанс '+str(r['id'])]); child.setData(0,Qt.ItemDataRole.UserRole,r['id']); parent.addChild(child)
                if r['id']==chosen_id: self.tree.setCurrentItem(child); parent.setExpanded(True)
        self.tree.blockSignals(False)
        self.count.setText(f'{self.offset+1 if self.rows else 0}–{self.offset+len(self.rows)} из {self.total} сеансов' if self.total else 'История пока пуста. Запустите мониторинг или измените фильтры.')
        self.prev.setEnabled(self.offset>0); self.next.setEnabled(self.offset+len(self.rows)<self.total)
        if chosen_id and self.selected_row(): self.show_detail()
        else: self.panel.hide()
    def show_detail(self,technical=False):
        r=self.selected_row()
        if not r: self.panel.hide(); return
        if technical or self.mode=='expert':
            names={'process':'Программа','pid':'PID','protocol':'Протокол','local_ip':'Локальный IP','local_port':'Локальный порт','remote_ip':'Удалённый IP','remote_port':'Порт','status':'Состояние','first_seen':'Первое наблюдение','last_seen':'Последнее наблюдение','country':'Страна','city':'Город'}
            text='<h2>Сеанс '+str(r['id'])+'</h2>'+''.join('<p>'+title+'<br>'+html.escape(str(r[k] if r[k] is not None else '—'))+'</p>' for k,title in names.items())
        else:
            text='<h2>'+html.escape(friendly_name(r['process']))+'</h2><p>Наблюдался адрес '+html.escape(r['remote_ip'] or r['local_ip'])+'</p><p>'+display_time(r['first_seen'])+' → '+display_time(r['last_seen'])+'</p><p>Страна: '+html.escape(r['country'] or 'не определена')+'</p><p><a href="technical">Технические сведения</a></p>'
        self.panel.show_html(text+'<p>Период наблюдения не доказывает непрерывность подключения.</p>')
    def context_action(self,signal):
        r=self.selected_row()
        if r: signal.emit(r['remote_ip'] if signal==self.map_requested else r['executable'] or r['process'])
    def export_csv(self):
        path,_=QFileDialog.getSaveFileName(self,'Экспорт всех отфильтрованных сеансов','history.csv','CSV (*.csv)')
        if path:
            self.export_requested.emit({'path':path,'query':getattr(self,'last_query',{})})
