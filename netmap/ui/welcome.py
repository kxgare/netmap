from dataclasses import replace
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame,QHBoxLayout,QPushButton
from netmap.ui.common import label

class WelcomeStrip(QFrame):
    finished=Signal()
    settings_requested=Signal()
    def __init__(self):
        super().__init__(); self.step=0; self.setObjectName('card')
        layout=QHBoxLayout(self); layout.setContentsMargins(24,12,24,12)
        self.text=label('Добро пожаловать. NetMap показывает сетевые подключения программ и хранит историю только на этом компьютере.','notice',True)
        layout.addWidget(self.text,1)
        self.configure=QPushButton('Настроить карту'); self.configure.hide(); self.configure.clicked.connect(self.settings_requested)
        self.next=QPushButton('Далее'); self.next.clicked.connect(self.advance)
        layout.addWidget(self.configure); layout.addWidget(self.next)
    def advance(self):
        if self.step==0:
            self.step=1; self.text.setText('Карта работает офлайн. Для точек адресов выберите свою базу GeoLite2. Пауза останавливает сбор; координаты всегда приблизительные.')
            self.configure.show(); self.next.setText('Начать работу')
        else: self.finished.emit(); self.hide()
