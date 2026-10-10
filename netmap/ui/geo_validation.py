from PySide6.QtCore import QThread,Signal
from pathlib import Path
import geoip2.database

class GeoValidation(QThread):
    validated=Signal(bool,str,object)
    def __init__(self,settings,parent=None):
        super().__init__(parent); self.settings=settings
    def run(self):
        path=self.settings.geo_path
        if not path: self.validated.emit(True,'База не выбрана',self.settings); return
        if not Path(path).is_file(): self.validated.emit(False,'Файл базы не найден. Выберите существующий файл MMDB.',self.settings); return
        try:
            with geoip2.database.Reader(path) as reader:
                if 'City' not in reader.metadata().database_type:
                    self.validated.emit(False,'Для карты нужна база GeoLite2 City, а не Country или ASN.',self.settings); return
            self.validated.emit(True,'База геолокации доступна',self.settings)
        except Exception:
            self.validated.emit(False,'Не удалось прочитать базу. Проверьте формат и целостность файла MMDB.',self.settings)
