from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame,QVBoxLayout,QHBoxLayout,QPushButton,QTextBrowser
from netmap.ui.common import label

class ContextPanel(QFrame):
    closed=Signal()
    def __init__(self,title='Подробности'):
        super().__init__()
        self.setObjectName('context')
        self.setMinimumWidth(280); self.setMaximumWidth(440)
        layout=QVBoxLayout(self)
        top=QHBoxLayout(); top.addWidget(label(title)); top.addStretch()
        close=QPushButton('×'); close.setFixedWidth(32); close.setToolTip('Закрыть подробности')
        close.clicked.connect(self.dismiss); top.addWidget(close)
        layout.addLayout(top)
        self.content=QTextBrowser(); self.content.setOpenLinks(False)
        layout.addWidget(self.content,1)
        self.actions=QHBoxLayout(); layout.addLayout(self.actions)
        self.hide()
    def dismiss(self):
        self.hide(); self.closed.emit()
    def show_html(self,text):
        scroll=self.content.verticalScrollBar().value()
        self.content.setHtml(text); self.content.verticalScrollBar().setValue(scroll)
        self.show()
