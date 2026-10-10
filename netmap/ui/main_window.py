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
from netmap.ui.theme import stylesheet, tokens
from netmap.ui.navigation import Navigation
from netmap.ui.welcome import WelcomeStrip
from netmap.ui.notifications import NotificationBar
from netmap.diagnostics.tcp import normalize_host


class MainWindow(NativeFrameMixin,QMainWindow):
    enabled_requested = Signal(bool)
    configure_requested = Signal(object)
    history_requested = Signal(object)
    search_requested=Signal(object)
    clear_requested = Signal()
    diagnostic_saved = Signal(object)
    analytics_active_requested=Signal(bool)
    analytics_requested=Signal(int)
    export_requested=Signal(object)
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
        from netmap.ui.typography import apply_typography
        from PySide6.QtWidgets import QApplication
        apply_typography(QApplication.instance())
        self.setWindowTitle("NetMap — Network Intelligence")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(980,640)
        self.resize(1440,900)
        resources = Path(__file__).resolve().parents[1]/"resources"
        self.setWindowIcon(QIcon(str(resources/"logo.svg")))
        self.setStyleSheet(stylesheet(settings.theme))
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.title = TitleBar(self)
        layout.addWidget(self.title)
        self.navigation = Navigation()
        layout.addWidget(self.navigation)
        self.welcome=WelcomeStrip()
        layout.addWidget(self.welcome)
        self.welcome.setVisible(not settings.onboarding_done)
        self.welcome.finished.connect(self.finish_onboarding)
        self.welcome.settings_requested.connect(lambda:self.navigate(5))
        self.pages = QStackedWidget()
        self.map_page = MapPage()
        self.map_page.settings = settings
        self.map_page.render()
        self.connections_page = ConnectionsPage()
        self.apps_page = AppsPage()
        self.apps_page.set_favorites(settings.favorites)
        self.apps_page.favorites_changed.connect(self.save_favorites)
        self.analytics_page = AnalyticsPage()
        self.analytics_page.run.setEnabled(settings.diagnostics_enabled)
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage(settings)
        for page in (self.map_page,self.connections_page,self.apps_page,self.analytics_page,self.history_page,self.settings_page):
            self.pages.addWidget(page)
        self.nav_buttons = self.navigation.buttons
        layout.addWidget(self.pages,1)
        self.navigation.selected.connect(self.navigate)
        self.navigation.mode_changed.connect(self.set_mode)
        foot = QHBoxLayout()
        foot.setContentsMargins(14,0,0,0)
        self.message = NotificationBar()
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
        self.worker.analytics_ready.connect(self.analytics_page.show_period)
        self.worker.export_ready.connect(self.message.setText)
        self.worker.geo_ready.connect(self.settings_page.geo_status.setText)
        self.analytics_requested.connect(self.worker.query_analytics)
        self.analytics_active_requested.connect(self.worker.set_analytics_active)
        self.export_requested.connect(self.worker.export_history)
        self.analytics_page.period_requested.connect(self.analytics_requested)
        self.history_page.export_requested.connect(self.export_requested)
        self.connections_page.export_requested.connect(self.export_requested)
        self.settings_page.export_requested.connect(lambda:self.navigate(4))
        from netmap.ui.search_overlay import SearchOverlay
        from PySide6.QtGui import QShortcut,QKeySequence
        self.search_overlay=SearchOverlay(self)
        self.search_requested.connect(self.worker.query_search)
        self.worker.search_ready.connect(self.search_overlay.history_results)
        self.search_overlay.requested.connect(self.search_requested)
        self.search_overlay.activated.connect(self.search_action)
        self.search_shortcut=QShortcut(QKeySequence('Ctrl+K'),self); self.search_shortcut.activated.connect(self.search_overlay.open_search)
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
        self.apps_page.ip_requested.connect(self.show_ip_map)
        self.apps_page.map_requested.connect(self.show_app_map)
        self.apps_page.connections_requested.connect(self.show_app_connections)
        self.apps_page.open_history_requested.connect(self.show_app_history)
        self.connections_page.map_requested.connect(self.show_ip_map)
        self.connections_page.app_requested.connect(self.show_app)
        self.connections_page.history_requested.connect(self.show_ip_history)
        self.map_page.history_requested.connect(self.show_ip_history)
        self.map_page.connections_requested.connect(self.show_ip_connections)
        self.connections_page.ip_connections_requested.connect(self.show_ip_connections)
        self.map_page.settings_requested.connect(lambda:self.navigate(5))
        self.history_page.map_requested.connect(self.show_ip_map)
        self.history_page.app_requested.connect(self.show_app)
        self.history_page.requested.connect(self.history_requested)
        self.apps_page.history_requested.connect(self.history_requested)
        self.history_page.clear_requested.connect(self.confirm_clear)
        self.settings_page.clear_requested.connect(self.confirm_clear)
        self.settings_page.saved.connect(self.apply_settings)
        self.analytics_page.map_requested.connect(self.show_ip_map)
        self.analytics_page.probe_requested.connect(self.start_probe)
        self.analytics_page.cancel_requested.connect(self.cancel_probe)
        self.title.pause.clicked.connect(self.toggle_monitor)
        self.set_mode(settings.mode, persist=False)
        self.navigate(0)
        self.update_status()
        from netmap.ui.interaction import apply_interactions
        apply_interactions(self)
        self.thread.start()

    def set_mode(self,mode,persist=True):
        self.settings = replace(self.settings,mode=mode)
        self.navigation.set_mode(mode)
        self.settings_page.theme.setCurrentIndex(self.settings_page.theme.findData(self.settings.theme))
        for chart in (self.analytics_page.timeline,self.analytics_page.apps,self.analytics_page.protocols,self.analytics_page.countries):
            chart.theme=self.settings.theme; chart.update()
        for i in range(self.pages.count()):
            page=self.pages.widget(i)
            if hasattr(page,'set_mode'): page.set_mode(mode)
        self.settings_page.settings=self.settings
        self.map_page.settings=self.settings
        if self.enabled: self.map_page.render()
        if persist:
            try: self.settings.save()
            except OSError: self.message.setText('Не удалось сохранить режим. Проверьте доступ к папке данных.')
        if self.last_payload and self.enabled: self.map_page.update_data(self.last_payload,self.settings)
        elif not self.enabled: self.map_page.map.update_data([],self.settings)

    def finish_onboarding(self):
        self.settings=replace(self.settings,onboarding_done=True)
        self.settings_page.settings=self.settings
        try: self.settings.save()
        except OSError: self.message.setText('Мастер завершён, но настройки не удалось сохранить.')

    def search_action(self,action,value):
        if action=='page': self.navigate(int(value))
        elif action=='ip': self.show_ip_map(value)
        elif action=='app': self.show_app(value)
        elif action=='history': self.show_app_history(value)
        elif action=='map': self.show_app_map(value)

    def save_favorites(self,keys):
        updated=replace(self.settings,favorites=keys)
        try: updated.save()
        except (OSError,ValueError):
            self.message.notify('Не удалось сохранить избранное.'); return
        self.settings=updated; self.settings_page.settings=updated; self.apps_page.set_favorites(keys)

    def show_ip_connections(self,ip):
        self.navigate(1); self.connections_page.apps.setCurrentIndex(0)
        if self.settings.mode=='expert': self.connections_page.search.setText(ip)
        else: self.connections_page.groups.search.setText(ip)

    def show_ip_map(self,ip):
        self.navigate(0); self.map_page.apps.setCurrentIndex(0); self.map_page.focus_ip(ip)
        self.history_requested.emit({"ip":ip,"limit":1,"_target":"map"})

    def show_ip_history(self,ip):
        self.navigate(4); self.history_page.find_ip(ip)

    def show_app_history(self,key):
        self.navigate(4); self.history_page.filter_app(key)

    def show_app_map(self,key):
        self.navigate(0); self.map_page.filter_app(key)

    def show_app_connections(self,key):
        self.navigate(1)
        index=self.connections_page.apps.findData(key)
        if index>=0: self.connections_page.apps.setCurrentIndex(index)
        if self.settings.mode=='simple': self.connections_page.groups.select_app(key)

    def show_app(self,key):
        if not any(row['key']==key for row in self.apps_page.groups.model.rows):
            self.show_app_history(key)
            self.message.setText('Программа сейчас не наблюдается. Открыты её сохранённые сеансы.')
            return
        self.navigate(2); self.apps_page.groups.select_app(key)

    def showEvent(self,event):
        super().showEvent(event)
        if not getattr(self,"_native_frame_enabled",False):
            self._native_frame_enabled = True
            self.enable_native_frame()

    def navigate(self,index):
        self.pages.setCurrentIndex(index)
        self.navigation.select(index)
        self.analytics_active_requested.emit(index==3)
        if index==4:
            self.history_page.query(False)
        if index==3:
            self.analytics_requested.emit(self.analytics_page.period.currentData())

    def update_status(self):
        self.title.status.setText("●  Мониторинг включён" if self.enabled else "○  Мониторинг остановлен")
        self.title.status.setStyleSheet("color:"+(tokens(self.settings.theme).good if self.enabled else tokens(self.settings.theme).warning))
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
        self.search_overlay.connections=payload['connections']
        self.connections_page.update_data(payload['connections'])
        self.apps_page.update_data(payload['connections'])
        self.map_page.update_data(payload,self.settings)
        self.analytics_page.update_data(payload)
        self.poll_count += 1
        if self.pages.currentWidget() == self.apps_page and self.poll_count % 5 == 0:
            self.apps_page.request_history()
        self.title.status.setText("●  Мониторинг включён")
        self.title.status.setStyleSheet("color:"+tokens(self.settings.theme).good)
        from netmap.ui.table import display_time
        self.message.setText(payload['warning'] or f"Обновлено: {display_time(payload['time'])} · интервал {self.settings.interval:g} с · короткие соединения могут быть пропущены")

    @Slot(str)
    def on_error(self,message):
        self.message.notify(message)
        if any(word in message.lower() for word in ("сбор","мониторинг","обработки","ос запретила")):
            self.title.status.setText("●  Сбор ограничен" if self.enabled else "○  Мониторинг остановлен")
            self.title.status.setStyleSheet("color:"+tokens(self.settings.theme).warning)

    @Slot(object)
    def on_history(self,payload):
        if payload['query'].get('_target')=='map':
            ip=payload['query']['ip']
            if self.map_page.selected_ip!=ip: return
            for row in payload['rows']:
                if row['latitude'] is not None and row['longitude'] is not None:
                    self.map_page.historical.insert(0,row)
            self.map_page.render(); self.map_page.focus_ip(ip)
        elif payload['query'].get('_target')=='app':
            self.apps_page.show_history(payload)
        else:
            self.history_page.show_rows(payload)

    def apply_settings(self,settings):
        self.settings = settings
        self.apps_page.set_favorites(settings.favorites)
        self.setStyleSheet(stylesheet(settings.theme))
        self.title.controls.set_theme(settings.theme)
        self.set_mode(settings.mode, persist=False)
        self.update_status()
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
        if self.settings_page.validator and self.settings_page.validator.isRunning():
            self.message.setText("Дождитесь завершения проверки локальной базы.")
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
