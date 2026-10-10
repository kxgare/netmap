from dataclasses import replace
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget
from netmap.core.settings import data_dir
from netmap.ui.geo_validation import GeoValidation
from netmap.ui.common import label, page_header


class SettingsPage(QWidget):
    saved = Signal(object)
    clear_requested = Signal()
    export_requested = Signal()
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
        self.mode='simple'; self.validator=None
        self.sections={}
        def section(title):
            box=QGroupBox(title); inner=QFormLayout(box); inner.setVerticalSpacing(13); inner.setHorizontalSpacing(28)
            layout.addWidget(box); self.sections[title]=box; return inner
        form=section('Основные')
        self.theme=QComboBox(); self.theme.addItem('Atlas Dark','dark'); self.theme.addItem('Atlas Light','light'); self.theme.setCurrentIndex(self.theme.findData(settings.theme))
        form.addRow('Тема',self.theme)
        self.interface_mode=QComboBox(); self.interface_mode.addItem('Простой','simple'); self.interface_mode.addItem('Эксперт','expert'); self.interface_mode.setCurrentIndex(self.interface_mode.findData(settings.mode))
        form.addRow('Режим интерфейса',self.interface_mode)
        form.setVerticalSpacing(18)
        form.setHorizontalSpacing(35)
        self.interval = self.number(.5,60,settings.interval,1)
        form.addRow("Интервал опроса, секунд",self.interval)
        self.autostart = self.check("Запускать мониторинг при открытии",settings.autostart)
        form.addRow("Мониторинг",self.autostart)
        form=section("Карта")
        self.geo_status=label("Проверка геолокации…","subheading",True)
        form.addRow(self.geo_status)
        self.animations = self.check("Плавное масштабирование карты",settings.animations)
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
        form=section("Данные")
        form.addRow("Папка данных",label(str(data_dir()),"subheading",True))
        export=QPushButton("Экспорт истории…"); export.clicked.connect(self.export_requested); form.addRow(export)
        self.days = QSpinBox()
        self.days.setRange(1,365)
        self.days.setValue(settings.retention_days)
        form.addRow("Хранить историю, дней",self.days)
        form=section("Дополнительные настройки карты")
        self.origin = self.check("Рисовать линии от точки, заданной вручную",settings.origin_enabled)
        form.addRow("Исходная локация",self.origin)
        self.lat = self.number(-90,90,settings.origin_lat,4)
        self.lon = self.number(-180,180,settings.origin_lon,4)
        form.addRow("Широта",self.lat)
        form.addRow("Долгота",self.lon)
        form=self.sections["Карта"].layout()
        self.tiles = self.check("Загружать тайлы OpenStreetMap из интернета",settings.online_tiles)
        form.addRow("Детализация карты",self.tiles)
        form=section("Диагностика")
        self.diagnostics = self.check("Разрешить ручные TCP-проверки",settings.diagnostics_enabled)
        form.addRow("Диагностика",self.diagnostics)
        self.count = QSpinBox()
        self.count.setRange(1,20)
        self.count.setValue(settings.diagnostic_count)
        form.addRow("Попыток в проверке",self.count)
        self.timeout = self.number(.2,10,settings.diagnostic_timeout,1)
        form.addRow("TCP-таймаут попытки, секунд",self.timeout)

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
        settings = replace(self.settings, theme=self.theme.currentData(),mode=self.interface_mode.currentData(), interval=self.interval.value(),autostart=self.autostart.isChecked(),
                animations=self.animations.isChecked(),map_limit=self.map_limit.currentData(),geo_path=self.geo.text().strip(),
                retention_days=self.days.value(),origin_enabled=self.origin.isChecked(),origin_lat=self.lat.value(),
                origin_lon=self.lon.value(),online_tiles=self.tiles.isChecked(),diagnostics_enabled=self.diagnostics.isChecked(),
                diagnostic_count=self.count.value(),diagnostic_timeout=self.timeout.value())
        if self.validator and self.validator.isRunning(): return
        self.feedback.setText('Проверяю настройки…')
        self.validator=GeoValidation(settings,self)
        self.validator.validated.connect(self.validated)
        self.validator.finished.connect(self.validator.deleteLater)
        self.validator.finished.connect(lambda:setattr(self,"validator",None))
        self.validator.start()

    def validated(self,ok,message,settings):
        self.geo_status.setText(message)
        if not ok:
            self.feedback.setText(message); return
        try:
            settings.save(); self.settings=settings
            self.feedback.setText('Настройки сохранены. Автозапуск применяется при следующем открытии.')
            self.saved.emit(settings)
        except (OSError,ValueError):
            self.feedback.setText('Не удалось сохранить настройки. Проверьте доступ к папке данных.')

    def set_mode(self,mode):
        self.mode=mode
        self.interface_mode.setCurrentIndex(self.interface_mode.findData(mode))
        expert=mode=='expert'
        if not hasattr(self,'advanced_toggle'):
            self.advanced_toggle=QCheckBox('Дополнительные настройки')
            self.layout().itemAt(0).widget().widget().layout().insertWidget(2,self.advanced_toggle)
            self.advanced_toggle.toggled.connect(self.toggle_advanced)
        self.advanced_toggle.setVisible(not expert)
        self.toggle_advanced(expert or self.advanced_toggle.isChecked())

    def toggle_advanced(self,show):
        visible=self.mode=='expert' or show
        self.sections['Дополнительные настройки карты'].setVisible(visible)
        # Keep consent controls visible; technical diagnostic parameters are optional.
        for w in (self.count,self.timeout):
            w.setVisible(visible)
            label_widget=self.sections['Диагностика'].layout().labelForField(w)
            if label_widget: label_widget.setVisible(visible)
