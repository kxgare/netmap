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
    return card(title,value),value


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
    fields = [("Приложение",c.process),("PID",c.pid if c.pid is not None else "—"),
              ("Исполняемый файл",c.executable or "Недоступен"),("Протокол",c.protocol),
              ("Локальный адрес",c.local_address),("Удалённый адрес",c.remote_address),("Состояние",c.status),
              ("Страна",c.location.country or "Не определена"),("Город",c.location.city or "Не определён"),
              ("Первое обнаружение",display_time(c.first_seen or c.observed)),
              ("Последнее обнаружение",display_time(c.observed))]
    content = '<h2 style="color:#6ed5ed">'+esc(c.remote_ip or "Локальный сокет")+'</h2>'
    content += ''.join('<p><span style="color:#819bb9">'+esc(k)+'</span><br>'+esc(v)+'</p>' for k,v in fields)
    if c.location.mapped:
        content += '<p>Геолокация приблизительная'+(f' · радиус {c.location.accuracy_km} км' if c.location.accuracy_km else '')+'.</p>'
    else:
        content += '<p>'+esc(c.location.reason or "Координаты недоступны")+'</p>'
    return content
