"""Apply one Qt font to widgets, menus and editor popups."""
from PySide6.QtGui import QFont, QFontDatabase

def apply_typography(app):
    available=set(QFontDatabase.families())
    family=next((f for f in ('Segoe UI Variable','Segoe UI','Noto Sans','DejaVu Sans') if f in available),'sans-serif')
    font=QFont(family); font.setPixelSize(13)
    app.setFont(font)
    for widget in ('QComboBox','QAbstractItemView','QSpinBox','QDoubleSpinBox','QDateEdit','QMenu','QToolTip'):
        app.setFont(font,widget)
    return family
