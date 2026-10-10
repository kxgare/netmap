from dataclasses import replace
from pathlib import Path
from PySide6.QtCore import QThread, Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QSizeGrip, QStackedWidget, QVBoxLayout, QWidget
from netmap.core.worker import DiagnosticThread, MonitorWorker
from netmap.ui.analytics_page import AnalyticsPage
from netmap.ui.apps_page import AppsPage
from netmap.ui.common import label
from netmap.ui.connections_page import ConnectionsPage
from netmap.ui.history_page import HistoryPage
from netmap.ui.map_page import MapPage
from netmap.ui.settings_page import SettingsPage
from netmap.ui.window_frame import NativeFrameMixin, TitleBar
from netmap.ui.theme import STYLE
from netmap.diagnostics.tcp import normalize_host


class MainWindow(NativeFrameMixin,QMainWindow):
    enabled_requested = Signal(bool)
    configure_requested = Signal(object)
    history_requested = Signal(object)
    clear_requested = Signal()
    diagnostic_saved = Signal(object)
    stop_requested = Signal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.enabled = settings.autostart
        self.last_payload = None
        self.diag = None
        self.closing = False
        self.can_close = False
        self.poll_count = 0
        self.setWindowTitle("NetMap — Network Intelligence")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(1080,700)
        self.resize(1440,900)
        resources = Path(__file__).resolve().parents[1]/"resources"
        self.setWindowIcon(QIcon(str(resources/"logo.svg")))
        self.setStyleSheet(STYLE)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.title = TitleBar(self)
        layout.addWidget(self.title)
        body = QHBoxLayout()
        body.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(16,28,16,20)
        nav.addWidget(label("NetMap","brand"))
        nav.addWidget(label("ВАША СЕТЬ НА КАРТЕ","eyebrow"))
        nav.addSpacing(28)
        self.pages = QStackedWidget()
        self.map_page = MapPage()
        self.map_page.settings = settings
        self.map_page.render()
        self.connections_page = ConnectionsPage()
        self.apps_page = AppsPage()
        self.analytics_page = AnalyticsPage()
        self.analytics_page.run.setEnabled(settings.diagnostics_enabled)
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage(settings)
        self.nav_buttons = []
        specs = [("Карта","map",self.map_page),("Соединения","connections",self.connections_page),
                 ("Приложения","apps",self.apps_page),("Аналитика","analytics",self.analytics_page),
                 ("История","history",self.history_page),("Настройки","settings",self.settings_page)]
        for index,(name,icon,page) in enumerate(specs):
            self.pages.addWidget(page)
            button = QPushButton(name)
            button.setIcon(QIcon(str(resources/(icon+'.svg'))))
            button.setCheckable(True)
            button.setObjectName("nav")
            button.clicked.connect(lambda checked=False,i=index:self.navigate(i))
            nav.addWidget(button)
            self.nav_buttons.append(button)
        nav.addStretch()
        nav.addWidget(label("ЛОКАЛЬНО · ПРИВАТНО","eyebrow"))
        nav.addWidget(label("Содержимое пакетов\nне собирается","subheading",True))
        nav.addSpacing(15)
        nav.addWidget(label("Версия 0.1 · MVP","subheading"))
        body.addWidget(sidebar)
        body.addWidget(self.pages,1)
        layout.addLayout(body,1)
        foot = QHBoxLayout()
        foot.setContentsMargins(14,0,0,0)
        self.message = label("Ожидание первого опроса…","subheading")
        foot.addWidget(self.message,1)
        grip = QSizeGrip(self)
        foot.addWidget(grip)
        layout.addLayout(foot)
        self.thread = QThread(self)
        self.worker = MonitorWorker(settings)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.start)
        self.worker.updated.connect(self.on_update)
        self.worker.error.connect(self.on_error)
        self.worker.history_ready.connect(self.on_history)
        self.worker.diagnostics_ready.connect(self.analytics_page.show_diagnostics)
        self.enabled_requested.connect(self.worker.set_enabled)
        self.configure_requested.connect(self.worker.configure)
        self.history_requested.connect(self.worker.query_history)
        self.clear_requested.connect(self.worker.clear)
        self.diagnostic_saved.connect(self.worker.save_diagnostic)
        self.stop_requested.connect(self.worker.stop)
        self.worker.stopped.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.finish_close)
        self.history_page.requested.connect(self.history_requested)
        self.apps_page.history_requested.connect(self.history_requested)
        self.history_page.clear_requested.connect(self.confirm_clear)
        self.settings_page.clear_requested.connect(self.confirm_clear)
        self.settings_page.saved.connect(self.apply_settings)
        self.analytics_page.probe_requested.connect(self.start_probe)
        self.analytics_page.cancel_requested.connect(self.cancel_probe)
        self.title.pause.clicked.connect(self.toggle_monitor)
        self.navigate(0)
        self.update_status()
        self.thread.start()

    def showEvent(self,event):
        super().showEvent(event)
        if not getattr(self,"_native_frame_enabled",False):
            self._native_frame_enabled = True
            self.enable_native_frame()

    def navigate(self,index):
        self.pages.setCurrentIndex(index)
        for i,button in enumerate(self.nav_buttons):
            button.setChecked(i==index)
        if index==4:
            self.history_page.query()

    def update_status(self):
        self.title.status.setText("●  Мониторинг включён" if self.enabled else "○  Мониторинг остановлен")
        self.title.status.setStyleSheet("color:"+("#6be4c1" if self.enabled else "#e3bb79"))
        self.title.pause.setText("Пауза" if self.enabled else "Продолжить")

    def toggle_monitor(self):
        self.enabled = not self.enabled
        self.enabled_requested.emit(self.enabled)
        self.update_status()
        if not self.enabled:
            self.message.setText("Мониторинг остановлен. На экране последний снимок; новые данные не собираются.")
            if self.last_payload:
                self.map_page.map.update_data([],self.settings)

    @Slot(object)
    def on_update(self,payload):
        if not self.enabled or self.closing:
            return
        self.last_payload = payload
        self.connections_page.update_data(payload['connections'])
        self.apps_page.update_data(payload['connections'])
        self.map_page.update_data(payload,self.settings)
        self.analytics_page.update_data(payload)
        self.poll_count += 1
        if self.pages.currentWidget() == self.apps_page and self.poll_count % 5 == 0:
            self.apps_page.request_history()
        self.title.status.setText("●  Мониторинг включён")
        self.title.status.setStyleSheet("color:#6be4c1")
        from netmap.ui.table import display_time
        self.message.setText(payload['warning'] or f"Обновлено: {display_time(payload['time'])} · интервал {self.settings.interval:g} с · короткие соединения могут быть пропущены")

    @Slot(str)
    def on_error(self,message):
        self.message.setText(message)
        self.title.status.setText("●  Сбор ограничен" if self.enabled else "○  Мониторинг остановлен")
        self.title.status.setStyleSheet("color:#e3bb79")

    @Slot(object)
    def on_history(self,payload):
        if payload['query'].get('_target')=='app':
            self.apps_page.show_history(payload)
        else:
            self.history_page.show_rows(payload)

    def apply_settings(self,settings):
        self.settings = settings
        self.configure_requested.emit(settings)
        self.analytics_page.run.setEnabled(settings.diagnostics_enabled and not (self.diag and self.diag.isRunning()))
        if not settings.diagnostics_enabled:
            self.cancel_probe()
        if self.last_payload and self.enabled:
            self.map_page.update_data(self.last_payload,settings)
        else:
            self.map_page.map.update_data([],settings)

    def confirm_clear(self):
        box = QMessageBox(self)
        box.setWindowTitle("Очистить локальные данные?")
        box.setText("Будут удалены история соединений, графики наблюдений и результаты диагностики. Настройки сохранятся. Действие необратимо.")
        yes=box.addButton("Очистить",QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Отмена",QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton()==yes:
            self.clear_requested.emit()
            self.last_payload = None
            self.map_page.historical = []
            self.map_page.map.update_data([],self.settings)
            self.analytics_page.timeline.set_samples([])

    def start_probe(self,host,port):
        if not self.settings.diagnostics_enabled or (self.diag and self.diag.isRunning()):
            return
        try:
            host = normalize_host(host)
        except (ValueError,UnicodeError) as exc:
            self.analytics_page.progress.setText(str(exc))
            return
        self.diag = DiagnosticThread(host,port,replace(self.settings),self)
        self.diag.result.connect(self.diagnostic_saved)
        self.diag.error.connect(self.analytics_page.progress.setText)
        self.diag.progress.connect(lambda count,ms:self.analytics_page.progress.setText(f"Попытка {count}: "+(f"{ms:.1f} мс" if ms is not None else "соединение не установлено")))
        self.diag.finished.connect(self.probe_finished)
        self.analytics_page.run.setEnabled(False)
        self.analytics_page.cancel.setEnabled(True)
        self.analytics_page.progress.setText("Проверка запущена · разрешение DNS и TCP выполняются в фоне…")
        self.diag.start()

    def cancel_probe(self):
        if self.diag and self.diag.isRunning():
            self.diag.requestInterruption()
            self.analytics_page.progress.setText("Остановка после текущей TCP-попытки…")

    def probe_finished(self):
        self.analytics_page.run.setEnabled(self.settings.diagnostics_enabled)
        self.analytics_page.cancel.setEnabled(False)
        if self.diag:
            self.diag.deleteLater()
            self.diag = None
        if self.closing:
            # Store remains alive until an in-flight diagnostic has emitted its result.
            self.stop_requested.emit()
            self.finish_close()

    def closeEvent(self,event):
        if self.can_close:
            event.accept()
            return
        event.ignore()
        if self.closing:
            return
        self.closing = True
        self.enabled = False
        self.enabled_requested.emit(False)
        self.title.status.setText("Завершение работы…")
        self.title.pause.setEnabled(False)
        if self.diag and self.diag.isRunning():
            self.cancel_probe()
        else:
            self.stop_requested.emit()

    def finish_close(self):
        if self.closing and not self.thread.isRunning() and not (self.diag and self.diag.isRunning()):
            self.can_close = True
            self.map_page.map.dispose()
            self.close()
