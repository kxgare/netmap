from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton

class Navigation(QFrame):
    selected=Signal(int)
    mode_changed=Signal(str)
    def __init__(self):
        super().__init__()
        self.setObjectName('navigation')
        layout=QHBoxLayout(self)
        layout.setContentsMargins(24,6,24,14)
        layout.setSpacing(7)
        self.buttons=[]
        for i,name in enumerate(['Карта','Соединения','Приложения','Аналитика','История']):
            button=QPushButton(name)
            button.setObjectName('nav'); button.setCheckable(True)
            button.clicked.connect(lambda checked=False,index=i:self.selected.emit(index))
            layout.addWidget(button); self.buttons.append(button)
        layout.addStretch()
        self.modes={}
        for key,name in [('simple','Простой'),('expert','Эксперт')]:
            button=QPushButton(name)
            button.setObjectName('mode'); button.setCheckable(True)
            button.clicked.connect(lambda checked=False,value=key:self.mode_changed.emit(value))
            layout.addWidget(button); self.modes[key]=button
    def select(self,index):
        for i,b in enumerate(self.buttons): b.setChecked(i==index)
    def set_mode(self,mode):
        for key,b in self.modes.items(): b.setChecked(key==mode)
