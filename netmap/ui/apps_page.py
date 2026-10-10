import html
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QSplitter,QPushButton,QTableView
from netmap.ui.groups import GroupsView
from netmap.ui.context import ContextPanel
from netmap.ui.common import page_header,friendly_name,setup_table
from netmap.ui.table import ConnectionModel,ConnectionFilter,display_time

class AppsPage(QWidget):
    history_requested=Signal(object)
    map_requested=Signal(str)
    connections_requested=Signal(str)
    open_history_requested=Signal(str)
    favorites_changed=Signal(object)
    ip_requested=Signal(str)
    def __init__(self):
        super().__init__(); self.mode='simple'; self.connections=[]; self.history_payload=None; self.selected_key=None
        layout=QVBoxLayout(self); layout.setContentsMargins(24,22,24,20)
        page_header(layout,'Приложения','Сетевая активность ваших программ')
        self.favorite=QPushButton('Закрепить программу'); self.favorite.setEnabled(False); self.favorite.setMaximumWidth(230); self.favorite.clicked.connect(self.toggle_favorite); layout.addWidget(self.favorite)
        split=QSplitter(); self.groups=GroupsView(); self.groups.table.hideColumn(3)
        for col,width in ((0,210),(1,75),(2,105),(4,130)): self.groups.table.setColumnWidth(col,width)
        self.panel=ContextPanel('Программа')
        self.panel.setMaximumWidth(850); self.detail=self.panel.content
        self.detail.anchorClicked.connect(lambda url:self.ip_requested.emit(url.toString()[3:]) if url.toString().startswith("ip:") else None)
        self.table=QTableView(); self.model=ConnectionModel(self); self.proxy=ConnectionFilter(self); self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy); setup_table(self.table); self.table.setMinimumHeight(240)
        self.panel.layout().insertWidget(2,self.table,1); self.table.hide()
        for title,signal in [('На карте',self.map_requested),('Соединения',self.connections_requested),('История',self.open_history_requested)]:
            button=QPushButton(title); button.clicked.connect(lambda checked=False,target=signal:target.emit(self.selected_key or '')); self.panel.actions.addWidget(button)
        split.addWidget(self.groups); split.addWidget(self.panel); split.setSizes([480,850]); layout.addWidget(split,1)
        self.groups.selected.connect(self.select_app); self.panel.closed.connect(lambda:setattr(self,'selected_key',None))
    def set_favorites(self,keys):
        self.groups.model.favorites=set(keys); self.groups.update_data(self.connections); self.groups.proxy.invalidate()
        self.favorite.setText('Открепить программу' if self.selected_key in keys else 'Закрепить программу')

    def toggle_favorite(self):
        if not self.selected_key: return
        keys=set(self.groups.model.favorites)
        if self.selected_key in keys: keys.remove(self.selected_key)
        else: keys.add(self.selected_key)
        self.favorites_changed.emit(sorted(keys))

    def select_app(self,key):
        self.selected_key=key; self.favorite.setEnabled(True); self.favorite.setText('Открепить программу' if key in self.groups.model.favorites else 'Закрепить программу'); self.history_payload=None; self.render(); self.request_history()
    def request_history(self):
        if self.selected_key: self.history_requested.emit({'app':self.selected_key,'limit':100,'_target':'app'})
    def update_data(self,connections):
        self.connections=connections; self.groups.update_data(connections); self.model.update(connections)
        if self.selected_key: self.render()
    def set_mode(self,mode):
        self.mode=mode; self.table.setVisible(mode=='expert' and self.selected_key is not None)
        if self.selected_key: self.render()
    def render(self):
        rows=[c for c in self.connections if c.app_key==self.selected_key]
        if not rows:
            self.panel.show_html('<h2>'+html.escape(self.selected_key or '')+'</h2><p>Сейчас сокеты не наблюдаются. Сохранённая активность доступна ниже и в истории.</p>'+ (self.history_html(self.history_payload['rows']) if self.history_payload else '')); self.table.hide(); return
        esc=html.escape; countries=sorted({c.location.country for c in rows if c.location.country})
        ips=sorted({c.remote_ip for c in rows if c.remote_ip})
        from netmap.geo.resolver import public_ip
        local=sum(not public_ip(c.remote_ip) for c in rows)
        text='<h2>'+esc(friendly_name(rows[0].process))+'</h2><p>'+esc(rows[0].executable or 'Путь недоступен')+'</p>'
        from collections import Counter
        text+='<h3>Протоколы</h3><p>'+esc(' · '.join(f'{k}: {v} сокетов' for k,v in Counter(c.protocol for c in rows).items()))+'</p>'
        text+=f'<p>Программа {esc(friendly_name(rows[0].process))} использует {len(rows)} наблюдаемых сокетов · {len(ips)} удалённых IP</p><p>Последняя активность: {display_time(max(c.observed for c in rows))}</p>'
        text+='<h3>География</h3><p>'+esc(', '.join(countries) or 'Страны не определены')+'</p>'
        public=[ip for ip in ips if public_ip(ip)]
        text+='<h3>Удалённые серверы</h3><p>'+(' · '.join('<a href="ip:'+esc(ip,quote=True)+'">'+esc(ip)+'</a>' for ip in public) or 'Публичные адреса не обнаружены')+'</p>'
        if local: text+='<p>Часть подключений используется для обмена данными внутри компьютера или локальной сети.</p>'
        text+=f'<p>Локальные и служебные сокеты: {local}. Технические строки доступны в экспертном режиме.</p>'
        if self.mode=='expert':
            text+='<p>'+esc(rows[0].executable or 'Путь недоступен')+'</p><h3>Группы по адресам</h3>'
            from collections import defaultdict
            addresses=defaultdict(list)
            for c in rows: addresses[c.remote_ip or 'Локальные сокеты'].append(c)
            for ip,members in sorted(addresses.items()):
                pids=', '.join(str(p) for p in sorted({c.pid for c in members if c.pid is not None})) or 'недоступен'
                protocols=', '.join(sorted({c.protocol for c in members}))
                ports=', '.join(str(p) for p in sorted({c.remote_port for c in members if c.remote_ip})) or '—'
                states=', '.join(sorted({c.status for c in members}))
                text+='<p><b>'+esc(ip)+f' · {len(members)} сокетов</b><br>PID: '+esc(pids)+'<br>'+esc(protocols)+' · порты: '+esc(ports)+'<br>'+esc(states)+'</p>'
        self.base_html=text
        if self.history_payload: text+=self.history_html(self.history_payload['rows'])
        self.panel.show_html(text); self.table.setVisible(self.mode=='expert')
        self.proxy.set_filters(app=self.selected_key)
    def history_html(self,rows):
        from collections import defaultdict
        groups=defaultdict(list)
        for row in rows: groups[(row['remote_ip'] or 'Без удалённого адреса',row['protocol'])].append(row)
        text='<h3>Последние сеансы (до 100) · сгруппированы по адресам</h3>'
        for (ip,protocol),members in groups.items():
            text+='<p>'+html.escape(ip)+' · '+html.escape(protocol)+f' · {len(members)} сеансов<br>'+display_time(min(r['first_seen'] for r in members))+' → '+display_time(max(r['last_seen'] for r in members))+'</p>'
        return text
    def show_history(self,payload):
        if payload['query'].get('app')!=self.selected_key: return
        self.history_payload=payload
        self.render()
