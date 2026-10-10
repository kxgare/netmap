# Реализуемость и выбранные решения

PySide6/QtWebEngine подходит для нативного Windows-интерфейса с локальным
Leaflet и двусторонним QtWebChannel. psutil даёт снимки TCP/UDP и процессы,
но не пакеты, байты по процессам и не гарантирует обнаружение коротких сокетов.
Поэтому графики показывают наблюдения, а диагностика запускается отдельно.
SQLite WAL работает в одном worker-потоке; GUI не выполняет SQL-запросы.

Первоначально проверены официальные источники через GitHub, поскольку
документационные сайты были недоступны через прокси текущей среды:

- [Qt QWindow, startSystemMove/startSystemResize](https://github.com/qt/qtbase/blob/dev/src/gui/kernel/qwindow.cpp)
- [Microsoft WM_NCHITTEST](https://github.com/MicrosoftDocs/win32/blob/docs/desktop-src/inputdev/wm-nchittest.md)
- [psutil](https://github.com/giampaolo/psutil/tree/master/docs)
- [MaxMind GeoIP2 database API](https://github.com/maxmind/GeoIP2-python)
- [Leaflet Map API](https://github.com/Leaflet/Leaflet/blob/main/src/map/Map.js)

Версии реально установленного стека: Python 3.12.14, PySide6 6.10.2,
psutil 7.2.2, geoip2 5.2.0, pytest 9.0.2, PyInstaller 6.19.0.
Обычная установка pip сохраняет TLS-проверку; Leaflet дополнительно проверен
по integrity npm. База реального GeoLite2 требует действий пользователя
по условиям MaxMind, поэтому вместо скрытого скачивания предоставлен выбор файла.

Офлайн-контуры Natural Earth позволяют запускать полезную карту сразу,
не запрашивая внешние сервисы. Кластеризация сделана по пиксельным ячейкам
при текущем масштабе. Кластер расположен в координатах одного из его реальных
участников; его размер означает число IP, не физический размер сервера.
Ограничение адресов может скрыть часть точек; счётчик показывает размер
полного входного набора и показанной части. На таблицу это ограничение не влияет.

Для надёжного EXE выбран PyInstaller one-folder с штатными Qt hooks.
Windows-рамка содержит нативный hit-test для краёв и поправку рабочей области
монитора. Hover Snap Layouts не включён в MVP: это требует отдельной проверки
DWM/Win32 на Windows 11. Точность и производительность рамки оцениваются
на целевых системах, а не по успешному импорту ctypes в Linux.
