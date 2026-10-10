import ctypes
import os
from pathlib import Path
from PySide6.QtGui import QIcon
from netmap.ui.window_controls import WindowControls
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton


class TitleBar(QFrame):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setObjectName("titlebar")
        self.setFixedHeight(66)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22,0,0,0)
        title = QLabel("NetMap")
        title.setObjectName("brand")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        logo=QLabel(); logo.setPixmap(QIcon(str(Path(__file__).resolve().parents[1]/"resources/logo.svg")).pixmap(28,28))
        logo.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addStretch()
        self.status = QLabel("●  Мониторинг")
        self.status.setObjectName("status")
        layout.addWidget(self.status)
        self.pause = QPushButton("Пауза")
        self.pause.setFixedHeight(32)
        layout.addWidget(self.pause)
        layout.addSpacing(15)
        self.settings = self.button("", "Настройки", lambda: window.navigate(5))
        self.settings.setIcon(QIcon(str(Path(__file__).resolve().parents[1]/"resources/settings.svg")))
        layout.addWidget(self.settings)
        self.controls=WindowControls(window)
        self.minimize=self.controls.minimize
        self.maximize=self.controls.maximize
        self.close_button=self.controls.close_button
        layout.addWidget(self.controls)

    def button(self, text, tooltip, action, name="window"):
        b = QPushButton(text)
        b.setObjectName(name)
        b.setToolTip(tooltip)
        b.setFixedSize(42,60)
        b.clicked.connect(action)
        return b

    def toggle_maximize(self):
        if self.window.isMaximized():
            self.window.showNormal()
        else:
            self.window.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.window.windowHandle():
            self.window.windowHandle().startSystemMove()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()


class NativeFrameMixin:
    """Native Windows edge hit-testing; Qt handles drag and double-click.

    Windows coordinates are physical pixels, unlike Qt layout coordinates.
    WM_GETMINMAXINFO constrains maximization to the monitor work area.
    """
    def enable_native_frame(self):
        if os.name != "nt":
            return
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        # Pointer-sized signatures are essential on 64-bit Windows.
        get_style = user32.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p)==8 else user32.GetWindowLongW
        set_style = user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p)==8 else user32.SetWindowLongW
        get_style.argtypes = [wintypes.HWND,ctypes.c_int]
        get_style.restype = ctypes.c_ssize_t
        set_style.argtypes = [wintypes.HWND,ctypes.c_int,ctypes.c_ssize_t]
        set_style.restype = ctypes.c_ssize_t
        hwnd = wintypes.HWND(int(self.winId()))
        # Keep native resize, minimize/maximize and system move support.
        style = get_style(hwnd,-16) | 0x00C00000 | 0x00040000 | 0x00020000 | 0x00010000 | 0x00080000
        set_style(hwnd,-16,style)
        user32.SetWindowPos.argtypes = [wintypes.HWND,wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.UINT]
        user32.SetWindowPos(hwnd,None,0,0,0,0,0x0020|0x0001|0x0002|0x0004|0x0010)

    def nativeEvent(self, event_type, message):
        if os.name != "nt":
            return super().nativeEvent(event_type,message)
        from ctypes import wintypes
        class MSG(ctypes.Structure):
            _fields_ = [("hwnd",wintypes.HWND),("message",wintypes.UINT),
                        ("wParam",wintypes.WPARAM),("lParam",wintypes.LPARAM),
                        ("time",wintypes.DWORD),("pt",wintypes.POINT)]
        msg = MSG.from_address(int(message))
        user32 = ctypes.windll.user32
        if msg.message == 0x0083: # WM_NCCALCSIZE: custom client area covers the native caption
            return True,0
        user32.GetWindowRect.argtypes = [wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
        if msg.message == 0x0084 and not self.isMaximized(): # WM_NCHITTEST
            rect = wintypes.RECT()
            user32.GetWindowRect(msg.hwnd,ctypes.byref(rect))
            x = ctypes.c_short(msg.lParam & 0xffff).value
            y = ctypes.c_short((msg.lParam >> 16) & 0xffff).value
            border = max(6,round(7*self.devicePixelRatioF()))
            left,right = x < rect.left+border,x >= rect.right-border
            top,bottom = y < rect.top+border,y >= rect.bottom-border
            hit = (13 if left else 14 if right else 12) if top else ((16 if left else 17 if right else 15) if bottom else (10 if left else 11 if right else 0))
            if hit:
                return True,hit
        if msg.message == 0x0024: # WM_GETMINMAXINFO
            class MINMAXINFO(ctypes.Structure):
                _fields_ = [(n,wintypes.POINT) for n in ("reserved","max_size","max_position","min_track","max_track")]
            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize",wintypes.DWORD),("monitor",wintypes.RECT),("work",wintypes.RECT),("flags",wintypes.DWORD)]
            user32.MonitorFromWindow.argtypes = [wintypes.HWND,wintypes.DWORD]
            user32.MonitorFromWindow.restype = wintypes.HANDLE
            user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE,ctypes.POINTER(MONITORINFO)]
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(info)
            monitor = user32.MonitorFromWindow(msg.hwnd,2)
            if user32.GetMonitorInfoW(monitor,ctypes.byref(info)):
                mmi = MINMAXINFO.from_address(msg.lParam)
                mmi.max_position.x = info.work.left-info.monitor.left
                mmi.max_position.y = info.work.top-info.monitor.top
                mmi.max_size.x = info.work.right-info.work.left
                mmi.max_size.y = info.work.bottom-info.work.top
                mmi.min_track.x = round(self.minimumWidth()*self.devicePixelRatioF())
                mmi.min_track.y = round(self.minimumHeight()*self.devicePixelRatioF())
                return True,0
        return super().nativeEvent(event_type,message)
