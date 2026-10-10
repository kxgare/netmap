import html
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QFrame, QHBoxLayout, QLabel, QTableView, QVBoxLayout
from netmap.ui.table import display_time


def label(text, name="", wrap=False):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def page_header(layout, title, subtitle):
    layout.addWidget(label(title,"heading"))
    layout.addWidget(label(subtitle,"subheading",True))
    layout.addSpacing(10)


def card(title, widget):
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20,16,20,16)
    layout.addWidget(label(title,"subheading"))
    layout.addWidget(widget)
    return frame


def metric(title):
    value = label("0","metric")
    block=card(title,value)
    block.setObjectName("metricBlock")
    block.layout().setContentsMargins(0,8,20,8)
    return block,value


def setup_table(table: QTableView):
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.verticalHeader().hide()
    table.verticalHeader().setDefaultSectionSize(44)
    table.horizontalHeader().setStretchLastSection(True)
    table.setSortingEnabled(True)


def connection_html(c):
    esc = lambda s: html.escape(str(s))
    fields = [("Приложение",c.process),("PID",c.pid if c.pid is not None else "—"),("Идентификатор наблюдения",c.key),
              ("Исполняемый файл",c.executable or "Недоступен"),("Протокол",c.protocol),
              ("Локальный адрес",c.local_address),("Удалённый адрес",c.remote_address),("Состояние",c.status),
              ("Страна",c.location.country or "Не определена"),("Город",c.location.city or "Не определён"),
              ("Первое обнаружение",display_time(c.first_seen or c.observed)),
              ("Последнее обнаружение",display_time(c.observed))]
    content = '<h2 >'+esc(c.remote_ip or "Локальный сокет")+'</h2>'
    content += ''.join('<p><span>'+esc(k)+'</span><br>'+esc(v)+'</p>' for k,v in fields)
    if c.location.mapped:
        content += '<p>Геолокация приблизительная'+(f' · радиус {c.location.accuracy_km} км' if c.location.accuracy_km else '')+'.</p>'
    else:
        content += '<p>'+esc(c.location.reason or "Координаты недоступны")+'</p>'
    return content


def friendly_name(name):
    # Strip only the executable extension: never invent an app/product identity.
    return name[:-4] if name.lower().endswith('.exe') else name


def simple_connection_html(c):
    name=html.escape(friendly_name(c.process))
    text=f'<h2>{name}</h2><p>{"Удалённый адрес наблюдается" if c.remote_ip else "Локальный сетевой сокет"}</p>'
    text+='<p>'+html.escape(c.remote_ip or c.local_ip)+'</p>'
    text+='<p>Страна: '+html.escape(c.location.country or 'не определена')+'</p>'
    text+='<p>Геолокация приблизительная и не определяет владельца сервера.</p>'
    text+='<p><a href="technical">Показать технические сведения</a></p>'
    return text
