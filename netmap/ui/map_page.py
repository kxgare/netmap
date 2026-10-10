import html
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox,QHBoxLayout,QSplitter,QPushButton,QVBoxLayout,QWidget
from netmap.core.statistics import map_points
from netmap.ui.common import connection_html,simple_connection_html,label,metric,page_header
from netmap.ui.context import ContextPanel
from netmap.ui.map_view import MapView

class MapPage(QWidget):
    history_requested=Signal(str)
    settings_requested=Signal()
    def __init__(self):
        super().__init__()
        self.connections=[]; self.historical=[]; self.settings=None; self.selected_ip=None; self.mode='simple'
        layout=QVBoxLayout(self); layout.setContentsMargins(24,22,24,12); layout.setSpacing(10)
        page_header(layout,'Карта','Ваши программы и география удалённых адресов')
        row=QHBoxLayout(); self.metrics={}
        for key,title in [('total','Сейчас подключений'),('public_ips','Публичных адресов'),('countries_count','Стран')]:
            block,value=metric(title); self.metrics[key]=value; row.addWidget(block,1)
            value.setToolTip({'total':'Обнаруженные сетевые сокеты, включая локальные и ожидающие. Это не объём трафика.','public_ips':'Уникальные публичные удалённые IP в текущем снимке.','countries_count':'Страны, найденные для текущих публичных IP в локальной базе.'}[key])
        layout.addLayout(row)
        tools=QHBoxLayout()
        self.apps=QComboBox(); self.apps.addItem('Все программы',''); self.apps.setMinimumWidth(200)
        self.recent=QComboBox(); self.recent.addItem('Последние адреса',''); self.recent.setMinimumWidth(200)
        tools.addWidget(self.apps); tools.addWidget(self.recent); tools.addStretch()
        tools.addWidget(label('● Сейчас   ○ Ранее','subheading'))
        layout.addLayout(tools)
        split=QSplitter(); self.map=MapView(); self.panel=ContextPanel('Удалённый адрес'); self.detail=self.panel.content
        self.panel.closed.connect(lambda:setattr(self,'selected_ip',None))
        self.detail.anchorClicked.connect(lambda url:self.select_ip(self.selected_ip,True))
        history=QPushButton('Найти в истории'); history.clicked.connect(lambda:self.history_requested.emit(self.selected_ip or ''))
        self.panel.actions.addWidget(history)
        split.addWidget(self.map); split.addWidget(self.panel); split.setSizes([1000,310]); layout.addWidget(split,1)
        bottom=QHBoxLayout(); self.notice=label('Геолокация IP приблизительная','notice',True)
        bottom.addWidget(self.notice,1)
        self.geo_button=QPushButton('Настроить геолокацию'); self.geo_button.clicked.connect(self.settings_requested)
        bottom.addWidget(self.geo_button); layout.addLayout(bottom)
        self.apps.currentIndexChanged.connect(self.render)
        self.recent.activated.connect(lambda:self.focus_ip(self.recent.currentData()))
        self.map.bridge.selected.connect(self.select_ip)
        self.map.ready.connect(lambda ok:self.notice.setText('Локальная карта недоступна. Откройте «Соединения».') if not ok else None)
    def set_mode(self,mode):
        self.mode=mode
        if self.selected_ip: self.select_ip(self.selected_ip)
        self.render()
    def render(self):
        if self.settings:
            self.map.update_data(map_points(self.connections,self.historical,self.apps.currentData() or ''),self.settings)
    def filter_app(self,key):
        index=self.apps.findData(key)
        if index<0:
            self.apps.addItem(key,key); index=self.apps.count()-1
        self.apps.setCurrentIndex(index)
    def focus_ip(self,ip):
        if not ip: return
        self.select_ip(ip)
        import json
        self.map.page().runJavaScript('window.focusIP('+json.dumps(ip)+')',lambda ok:self.notice.setText('Адрес не отображён: координаты отсутствуют или достигнут лимит карты. Сведения показаны справа.') if not ok else None)
    def select_ip(self,ip,technical=False):
        if not ip: return
        self.selected_ip=ip; app=self.apps.currentData()
        rows=[c for c in self.connections if c.remote_ip==ip and (not app or c.app_key==app)]
        if rows:
            renderer=connection_html if technical or self.mode=='expert' else simple_connection_html
            self.panel.show_html('<hr>'.join(renderer(c) for c in rows))
        else:
            past=[r for r in self.historical if r['remote_ip']==ip and (not app or (r['executable'] or r['process'])==app)]
            self.panel.show_html('<h2>'+html.escape(ip)+'</h2><p>Текущее подключение не наблюдается.</p>'+''.join('<p>'+html.escape(r['process'])+' · '+html.escape(r['country'] or 'страна не определена')+'</p>' for r in past[:20]))
    def update_data(self,payload,settings):
        self.connections=payload['connections']; self.historical=payload['historical']; self.settings=settings
        stats=payload['stats']
        for k,w in self.metrics.items(): w.setText(str(stats.get('countries_count',len([c for c in stats['countries'] if c!='Не определена'])) if k=='countries_count' else stats[k]))
        known={r['executable'] or r['process']:r['process'] for r in self.historical}
        known.update({c.app_key:c.process for c in self.connections})
        old=self.apps.currentData(); old_text=self.apps.currentText()
        if old and old not in known: known[old]=old_text
        entries=[('Все программы','')]+[(name,key) for key,name in sorted(known.items(),key=lambda p:p[1].casefold())]
        if entries!=[(self.apps.itemText(i),self.apps.itemData(i)) for i in range(self.apps.count())]:
            self.apps.blockSignals(True); self.apps.clear()
            for name,key in entries: self.apps.addItem(name,key)
            self.apps.setCurrentIndex(max(0,self.apps.findData(old))); self.apps.blockSignals(False)
        ips=list(dict.fromkeys(c.remote_ip for c in sorted(self.connections,key=lambda c:c.first_seen or c.observed,reverse=True) if c.remote_ip))[:12]
        self.recent.blockSignals(True); self.recent.clear(); self.recent.addItem('Последние адреса','')
        for ip in ips: self.recent.addItem(ip,ip)
        self.recent.blockSignals(False)
        available=any(c.location.mapped for c in self.connections)
        self.notice.setText(('Геолокация приблизительная' if available else 'Координаты не найдены. Адреса доступны в «Соединениях».')+(' · Тайлы OSM передают сервису ваш IP' if settings.online_tiles else ' · Локальная карта'))
        self.render()
        if self.selected_ip: self.select_ip(self.selected_ip)
