from dataclasses import replace
import time
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from netmap.core.settings import data_dir
from netmap.core.statistics import statistics
from netmap.database.store import HistoryStore
from netmap.geo.resolver import GeoResolver
from netmap.network.collector import Collector
from netmap.diagnostics.tcp import probe_tcp


class MonitorWorker(QObject):
    updated = Signal(object)
    history_ready = Signal(object)
    diagnostics_ready = Signal(object)
    error = Signal(str)
    stopped = Signal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.enabled = settings.autostart
        self.store = None
        self.geo = None
        self.timer = None
        self.last_prune = 0.0
        self.last_observation_clock = None
        self.collector = Collector()

    @Slot()
    def start(self):
        try:
            self.store = HistoryStore(data_dir() / "history.sqlite3")
            self.geo = GeoResolver(self.settings.geo_path)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.poll)
            self.timer.start(round(self.settings.interval*1000))
            self.diagnostics_ready.emit(self.store.diagnostic_history())
            self.poll()
        except Exception as exc:
            self.error.emit(f"Не удалось запустить мониторинг: {exc}")

    @Slot()
    def poll(self):
        if not self.enabled or self.store is None or self.geo is None:
            return
        try:
            snapshot = self.collector.collect()
            if not snapshot.valid:
                self.error.emit(snapshot.warning)
                return
            connections = [replace(c, location=self.geo.lookup(c.remote_ip)) for c in snapshot.connections]
            clock = time.time()
            if self.last_observation_clock is not None and (clock-self.last_observation_clock > max(10,self.settings.interval*3) or clock < self.last_observation_clock):
                # Suspend, delayed collection or a clock correction breaks observation continuity.
                self.store.end_observation()
            connections, new = self.store.observe(connections,snapshot.observed)
            self.last_observation_clock = clock
            if time.monotonic()-self.last_prune > 3600:
                self.store.prune(self.settings.retention_days)
                self.last_prune = time.monotonic()
            self.updated.emit({"connections": connections, "stats": statistics(connections), "new": new,
                "samples": self.store.samples(), "historical": self.store.recent_map(self.settings.map_limit*2),
                "geo_message": self.geo.message, "warning": snapshot.warning, "time": snapshot.observed})
        except Exception as exc:
            self.error.emit(f"Ошибка обработки данных: {exc}")

    @Slot(bool)
    def set_enabled(self, enabled):
        self.enabled = enabled
        if self.store:
            if not enabled:
                self.store.end_observation()
            else:
                self.poll()

    @Slot(object)
    def configure(self, settings):
        old_path = self.settings.geo_path
        self.settings = settings
        if self.timer:
            self.timer.setInterval(round(settings.interval*1000))
        if self.geo and old_path != settings.geo_path:
            self.geo.close()
            self.geo = GeoResolver(settings.geo_path)
        if self.store:
            self.store.prune(settings.retention_days)
        self.poll()

    @Slot(object)
    def query_history(self, query):
        if self.store:
            try:
                args = {k:v for k,v in query.items() if not k.startswith("_")}
                rows = self.store.history(**args)
                self.history_ready.emit({"query": query,"rows": rows})
            except Exception as exc:
                self.error.emit(f"Ошибка поиска истории: {exc}")

    @Slot()
    def clear(self):
        if self.store:
            try:
                self.store.clear()
                self.history_ready.emit({"query": {}, "rows": []})
                self.diagnostics_ready.emit([])
                self.poll()
            except Exception as exc:
                self.error.emit(f"Не удалось очистить историю: {exc}")

    @Slot(object)
    def save_diagnostic(self, result):
        if self.store:
            try:
                self.store.add_diagnostic(result)
                self.diagnostics_ready.emit(self.store.diagnostic_history())
            except Exception as exc:
                self.error.emit(f"Не удалось сохранить диагностику: {exc}")

    @Slot()
    def stop(self):
        if self.timer:
            self.timer.stop()
        if self.geo:
            self.geo.close()
        if self.store:
            self.store.close()
        self.stopped.emit()


class DiagnosticThread(QThread):
    result = Signal(object)
    error = Signal(str)
    progress = Signal(int, object)

    def __init__(self, host, port, settings, parent=None):
        super().__init__(parent)
        self.host, self.port, self.settings = host, port, settings

    def run(self):
        try:
            result = probe_tcp(self.host,self.port,self.settings.diagnostic_count,self.settings.diagnostic_timeout,
                               self.isInterruptionRequested,self.progress.emit)
            self.result.emit(result)
        except Exception as exc:
            self.error.emit(f"Проверка не выполнена: {exc}")
