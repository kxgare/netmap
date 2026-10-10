from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor
from netmap.core.models import Connection

COLUMNS = ["Приложение", "PID", "Протокол", "Локальный адрес", "Удалённый IP", "Порт", "Состояние", "Страна", "Обнаружено"]


def display_time(value):
    from datetime import datetime
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%d.%m %H:%M:%S")
    except (ValueError, TypeError):
        return str(value)


def values(c):
    return [c.process,c.pid if c.pid is not None else "—",c.protocol,c.local_address,c.remote_ip or "—",
            c.remote_port if c.remote_ip else "—",c.status,c.location.country or "—",display_time(c.first_seen or c.observed)]


class ConnectionModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLUMNS[section]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        c = self.rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return values(c)[index.column()]
        if role == Qt.ItemDataRole.UserRole:
            # Numeric PID and port sort numerically; dates sort by UTC ISO string.
            if index.column() == 8:
                return c.first_seen or c.observed
            return values(c)[index.column()]
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{c.process}\n{c.executable or 'Путь недоступен'}\n{c.location.reason}"
        if role == Qt.ItemDataRole.ForegroundRole and index.column() == 6:
            return QColor("#83bf99" if c.status == "ESTABLISHED" else "#a3a79c")

    def update(self, connections):
        incoming = {c.key: c for c in connections}
        # Structural changes keep persistent indexes and unaffected selections alive.
        for row in range(len(self.rows)-1,-1,-1):
            if self.rows[row].key not in incoming:
                self.beginRemoveRows(QModelIndex(),row,row)
                self.rows.pop(row)
                self.endRemoveRows()
        existing = {c.key for c in self.rows}
        for row, old in enumerate(self.rows):
            new = incoming[old.key]
            if new != old:
                self.rows[row] = new
                self.dataChanged.emit(self.index(row,0),self.index(row,len(COLUMNS)-1))
        additions = [c for c in connections if c.key not in existing]
        if additions:
            start = len(self.rows)
            self.beginInsertRows(QModelIndex(),start,start+len(additions)-1)
            self.rows.extend(additions)
            self.endInsertRows()


class ConnectionFilter(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search = ""
        self.protocol = ""
        self.app = ""
        self.pid=None; self.state=""; self.family=""
        self.setSortRole(Qt.ItemDataRole.UserRole)
        self.setDynamicSortFilter(True)

    def set_filters(self, search="", protocol="", app="",pid=None,state="",family=""):
        self.beginFilterChange()
        self.search, self.protocol, self.app = search.casefold(), protocol, app
        self.pid,self.state,self.family=pid,state,family
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, row, parent):
        c = self.sourceModel().rows[row]
        return matches(c,self.search,self.protocol,self.app) and (self.pid is None or c.pid==self.pid) and (not self.state or c.status==self.state) and (not self.family or (":" in c.local_ip)==(self.family=="IPv6"))


def matches(c: Connection, search="", protocol="", app=""):
    text = " ".join(str(v) for v in values(c)).casefold() + " " + c.executable.casefold()
    return (not search or search.casefold() in text) and (not protocol or c.protocol == protocol) and (not app or c.app_key == app)
