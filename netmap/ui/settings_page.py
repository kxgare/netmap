from dataclasses import replace
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget
from netmap.ui.common import label, page_header


class SettingsPage(QWidget):
    saved = Signal(object)
    clear_requested = Signal()
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0,0,0,0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32,26,32,26)
        page_header(layout,"Настройки","Локальные параметры мониторинга, карты и хранения")
        form = QFormLayout()
        form.setVerticalSpacing(18)
        form.setHorizontalSpacing(35)
        self.interval = self.number(.5,60,settings.interval,1)
        form.addRow("Интервал опроса, секунд",self.interval)
        self.autostart = self.check("Запускать мониторинг при открытии",settings.autostart)
        form.addRow("Мониторинг",self.autostart)
        self.animations = self.check("Мягкая подсветка точек и плавный масштаб",settings.animations)
        form.addRow("Визуальные эффекты",self.animations)
        self.map_limit = QComboBox()
        for count in (100,500,1000):
            self.map_limit.addItem(f"Не более {count} адресов",count)
        self.map_limit.setCurrentIndex(self.map_limit.findData(settings.map_limit))
        form.addRow("Производительность карты",self.map_limit)
        pathrow = QHBoxLayout()
        self.geo = QLineEdit(settings.geo_path)
        self.geo.setPlaceholderText("GeoLite2-City.mmdb")
        browse = QPushButton("Обзор…")
        browse.clicked.connect(self.browse)
        pathrow.addWidget(self.geo,1)
        pathrow.addWidget(browse)
        form.addRow("Локальная база геолокации",pathrow)
        self.days = QSpinBox()
        self.days.setRange(1,365)
        self.days.setValue(settings.retention_days)
        form.addRow("Хранить историю, дней",self.days)
        self.origin = self.check("Рисовать линии от точки, заданной вручную",settings.origin_enabled)
        form.addRow("Исходная локация",self.origin)
        self.lat = self.number(-90,90,settings.origin_lat,4)
        self.lon = self.number(-180,180,settings.origin_lon,4)
        form.addRow("Широта",self.lat)
        form.addRow("Долгота",self.lon)
        self.tiles = self.check("Загружать тайлы OpenStreetMap из интернета",settings.online_tiles)
        form.addRow("Детализация карты",self.tiles)
        self.diagnostics = self.check("Разрешить ручные TCP-проверки",settings.diagnostics_enabled)
        form.addRow("Диагностика",self.diagnostics)
        self.count = QSpinBox()
        self.count.setRange(1,20)
        self.count.setValue(settings.diagnostic_count)
        form.addRow("Попыток в проверке",self.count)
        self.timeout = self.number(.2,10,settings.diagnostic_timeout,1)
        form.addRow("TCP-таймаут попытки, секунд",self.timeout)
        layout.addLayout(form)
        self.origin.toggled.connect(self.origin_fields)
        self.origin_fields(settings.origin_enabled)
        layout.addWidget(label("Тайлы передают сервису OpenStreetMap ваш внешний IP и область просмотра карты. При выключенной настройке используется локальная карта. Начальная локация не определяется автоматически.","notice",True))
        layout.addWidget(label("GeoLite2-City: создайте учётную запись MaxMind, примите условия GeoLite2 и загрузите базу MMDB с официального сайта. Распакуйте её локально и выберите файл выше. Обновляйте базу согласно условиям MaxMind. База не включена в приложение.","subheading",True))
        buttons = QHBoxLayout()
        save = QPushButton("Сохранить настройки")
        save.setObjectName("primary")
        save.clicked.connect(self.apply)
        clear = QPushButton("Очистить историю и диагностику…")
        clear.clicked.connect(self.clear_requested)
        buttons.addWidget(save)
        buttons.addWidget(clear)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.feedback = label("", "subheading",True)
        layout.addWidget(self.feedback)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    @staticmethod
    def number(low,high,value,decimals):
        w = QDoubleSpinBox()
        w.setDecimals(decimals)
        w.setRange(low,high)
        w.setValue(value)
        return w

    @staticmethod
    def check(text,value):
        w = QCheckBox(text)
        w.setChecked(value)
        return w

    def origin_fields(self,enabled):
        self.lat.setEnabled(enabled)
        self.lon.setEnabled(enabled)

    def browse(self):
        path,_ = QFileDialog.getOpenFileName(self,"Выберите локальную GeoLite2-City",self.geo.text(),"База MaxMind (*.mmdb)")
        if path:
            self.geo.setText(path)

    def apply(self):
        settings = replace(self.settings, interval=self.interval.value(),autostart=self.autostart.isChecked(),
                animations=self.animations.isChecked(),map_limit=self.map_limit.currentData(),geo_path=self.geo.text().strip(),
                retention_days=self.days.value(),origin_enabled=self.origin.isChecked(),origin_lat=self.lat.value(),
                origin_lon=self.lon.value(),online_tiles=self.tiles.isChecked(),diagnostics_enabled=self.diagnostics.isChecked(),
                diagnostic_count=self.count.value(),diagnostic_timeout=self.timeout.value())
        try:
            settings.save()
            self.settings = settings
            self.feedback.setText("Настройки сохранены. Изменения применяются к текущему сеансу; автозапуск — при следующем открытии.")
            self.saved.emit(settings)
        except (OSError, ValueError) as exc:
            self.feedback.setText(f"Не удалось сохранить настройки: {exc}")
