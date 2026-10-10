import logging
from logging.handlers import RotatingFileHandler
import sys
from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication, QMessageBox
from netmap.core.settings import Settings, data_dir


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NetMap")
    app.setApplicationVersion("0.2.0")
    app.setOrganizationName("NetMap")
    app.setApplicationDisplayName("NetMap — Network Intelligence")
    path = data_dir()
    path.mkdir(parents=True,exist_ok=True)
    lock = QLockFile(str(path/"netmap.lock"))
    if not lock.tryLock(100):
        box = QMessageBox()
        box.setWindowTitle("NetMap уже запущен")
        box.setText("Другой экземпляр использует эту папку данных. Откройте существующее окно NetMap.")
        box.addButton("Закрыть",QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        return 1
    handler = RotatingFileHandler(path/"netmap.log",maxBytes=512_000,backupCount=2,encoding="utf-8")
    logging.basicConfig(handlers=[handler],level=logging.WARNING)
    def report(kind,value,tb):
        logging.error("Unhandled exception",exc_info=(kind,value,tb))
        box = QMessageBox()
        box.setWindowTitle("Ошибка NetMap")
        box.setText(f"Не удалось выполнить действие: {value}\nПодробности сохранены в локальном журнале.")
        box.addButton("Закрыть",QMessageBox.ButtonRole.AcceptRole)
        box.exec()
    sys.excepthook = report
    try:
        settings = Settings.load()
    except (ValueError,TypeError,OSError) as exc:
        settings = Settings()
        box = QMessageBox()
        box.setWindowTitle("Настройки NetMap")
        box.setText(f"Не удалось прочитать настройки: {exc}\nПрименены значения по умолчанию. Исходный файл не изменён.")
        box.addButton("Продолжить",QMessageBox.ButtonRole.AcceptRole)
        box.exec()
    from netmap.ui.main_window import MainWindow
    window = MainWindow(settings)
    window.show()
    result = app.exec()
    lock.unlock()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
