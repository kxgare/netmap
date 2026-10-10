import json
from pathlib import Path
from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineProfileBuilder, QWebEngineSettings, QWebEngineUrlRequestInterceptor
from PySide6.QtWebEngineWidgets import QWebEngineView
from netmap.core.settings import data_dir
from netmap.ui.theme import tokens
from dataclasses import asdict


class MapBridge(QObject):
    selected = Signal(str)
    @Slot(str)
    def select(self, ip):
        self.selected.emit(ip)


class MapRequestPolicy(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.online = False

    def interceptRequest(self, info):
        url = info.requestUrl()
        if url.scheme() in ("file","qrc","data","blob"):
            return
        # Online map exposes only tile coordinates; no IP observation data leaves this page.
        allowed = self.online and url.scheme() == "https" and url.host() == "tile.openstreetmap.org"
        info.block(not allowed)


class LocalMapPage(QWebEnginePage):
    def acceptNavigationRequest(self,url,kind,is_main_frame):
        # No external navigation from popup content or attribution.
        return url.scheme() in ("file","qrc","data")


class MapView(QWebEngineView):
    ready = Signal(bool)
    def __init__(self, parent=None):
        super().__init__(parent)
        cache = data_dir()/"tile-cache"
        builder = QWebEngineProfileBuilder()
        builder.setCachePath(str(cache/"http"))
        builder.setPersistentStoragePath(str(cache/"storage"))
        builder.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        builder.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        builder.setHttpCacheMaximumSize(64*1024*1024)
        self.profile = builder.createProfile("NetMapMap",self)
        self.profile.setHttpUserAgent(self.profile.httpUserAgent()+" NetMap/0.2")
        self.policy = MapRequestPolicy(self.profile)
        self.profile.setUrlRequestInterceptor(self.policy)
        page = LocalMapPage(self.profile,self)
        self.setPage(page)
        self.channel = QWebChannel(page)
        self.bridge = MapBridge(self.channel)
        self.channel.registerObject("bridge",self.bridge)
        page.setWebChannel(self.channel)
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,True)
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,True)
        self.loaded = False
        self.pending = None
        self.loadFinished.connect(self._loaded)
        path = Path(__file__).resolve().parents[1] / "resources/map/index.html"
        self.setUrl(QUrl.fromLocalFile(str(path)))

    def _loaded(self, ok):
        self.loaded = ok
        self.ready.emit(ok)
        if ok and self.pending:
            self.update_data(*self.pending)

    def update_data(self, points, settings):
        self.pending = points,settings
        self.policy.online = settings.online_tiles
        if not self.loaded:
            return
        payload = {"points": sorted(points,key=lambda p:not p["active"])[:settings.map_limit],"total_points":len(points),"limit": settings.map_limit,"animations": settings.animations,
                   "tiles": settings.online_tiles,"mode":settings.mode,"palette":asdict(tokens(settings.theme)),
                   "origin": [settings.origin_lat,settings.origin_lon] if settings.origin_enabled else None}
        self.page().runJavaScript("window.updateNetMap("+json.dumps(payload,ensure_ascii=True)+");")

    def dispose(self):
        self.stop()
        self.page().deleteLater()
