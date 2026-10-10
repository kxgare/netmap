from pathlib import Path
from PySide6.QtCore import QEvent,QSize,Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget,QHBoxLayout,QPushButton

class CloseButton(QPushButton):
    def enterEvent(self,event):
        self.setIcon(QIcon(str(Path(__file__).resolve().parents[1]/'resources/close-hover.svg')))
        super().enterEvent(event)
    def leaveEvent(self,event):
        self.setIcon(self.normal_icon)
        super().leaveEvent(event)

class WindowControls(QWidget):
    def __init__(self,window):
        super().__init__(window); self.window=window
        self.resources=Path(__file__).resolve().parents[1]/'resources'
        layout=QHBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        self.minimize=self.button('minimize','Свернуть',window.showMinimized)
        self.maximize=self.button('maximize','Развернуть / восстановить',self.toggle)
        self.close_button=self.button('close','Закрыть',window.close)
        for button in (self.minimize,self.maximize,self.close_button): layout.addWidget(button)
        window.installEventFilter(self)
        self.set_theme(getattr(getattr(window,"settings",None),"theme","dark"))
    def button(self,icon,title,action):
        b=CloseButton() if icon=="close" else QPushButton(); b.setObjectName('close' if icon=='close' else 'window')
        b.setIcon(QIcon(str(self.resources/(icon+'.svg')))); b.normal_icon=b.icon(); b.setIconSize(QSize(18,18))
        b.setToolTip(title); b.setAccessibleName(title); b.setFixedSize(46,50)
        b.setCursor(Qt.CursorShape.PointingHandCursor); b.clicked.connect(action); return b
    def set_theme(self,theme):
        self.theme=theme
        for button,name in ((self.minimize,"minimize"),(self.maximize,"restore" if self.window.isMaximized() else "maximize"),(self.close_button,"close")):
            suffix="-light" if theme=="light" else ""
            button.normal_icon=QIcon(str(self.resources/(name+suffix+".svg")))
            button.setIcon(button.normal_icon)

    def toggle(self):
        self.window.showNormal() if self.window.isMaximized() else self.window.showMaximized()
    def eventFilter(self,obj,event):
        if obj is self.window and event.type()==QEvent.Type.WindowStateChange:
            name='restore' if self.window.isMaximized() else 'maximize'
            self.set_theme(self.theme)
            self.maximize.setAccessibleName('Восстановить' if self.window.isMaximized() else 'Развернуть')
        return False
