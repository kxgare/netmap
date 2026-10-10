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
    def __init__(self):
        super().__init__(); self.mode='simple'; self.connections=[]; self.history_payload=None; self.selected_key=None
        layout=QVBoxLayout(self); layout.setContentsMargins(24,22,24,20)
        page_header(layout,'Приложения','Сетевая активность ваших программ')
        split=QSplitter(); self.groups=GroupsView(); self.panel=ContextPanel('Программа')
        self.panel.setMaximumWidth(700); self.detail=self.panel.content
        self.table=QTableView(); self.model=ConnectionModel(self); self.proxy=ConnectionFilter(self); self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy); setup_table(self.table); self.table.setMinimumHeight(240)
        self.panel.layout().insertWidget(2,self.table,1); self.table.hide()
        for title,signal in [('На карте',self.map_requested),('Соединения',self.connections_requested)]:
            button=QPushButton(title); button.clicked.connect(lambda checked=False,target=signal:target.emit(self.selected_key or '')); self.panel.actions.addWidget(button)
        split.addWidget(self.groups); split.addWidget(self.panel); layout.addWidget(split,1)
        self.groups.selected.connect(self.select_app); self.panel.closed.connect(lambda:setattr(self,'selected_key',None))
    def select_app(self,key):
        self.selected_key=key; self.history_payload=None; self.render(); self.request_history()
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
            self.panel.hide(); return
        esc=html.escape; countries=sorted({c.location.country for c in rows if c.location.country})
        ips=sorted({c.remote_ip for c in rows if c.remote_ip})
        from netmap.geo.resolver import public_ip
        local=sum(not public_ip(c.remote_ip) for c in rows)
        text='<h2>'+esc(friendly_name(rows[0].process))+'</h2>'
        text+=f'<p>{len(rows)} наблюдаемых сокетов · {len(ips)} удалённых IP</p><p>Последняя активность: {display_time(max(c.observed for c in rows))}</p>'
        text+='<h3>География</h3><p>'+esc(', '.join(countries) or 'Страны не определены')+'</p>'
        text+='<h3>Удалённые адреса</h3><p>'+esc(', '.join(ips) or 'Не обнаружены')+'</p>'
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
        return '<h3>Последние сеансы (до 100)</h3>'+''.join('<p>'+html.escape(r['remote_ip'] or r['local_ip'])+' · '+display_time(r['first_seen'])+' → '+display_time(r['last_seen'])+'</p>' for r in rows[:100])
    def show_history(self,payload):
        if payload['query'].get('app')!=self.selected_key: return
        self.history_payload=payload
        if hasattr(self,'base_html'): self.panel.show_html(self.base_html+self.history_html(payload['rows']))
