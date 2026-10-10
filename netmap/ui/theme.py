"""Network Atlas tokens shared by Qt, charts and the embedded map."""
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Tokens:
    bg: str
    surface: str
    raised: str
    text: str
    muted: str
    line: str
    accent: str
    selection: str
    ocean: str
    land: str
    border: str
    good: str
    warning: str
    font: str = "Segoe UI"
    body: int = 13
    heading: int = 28
    spacing: int = 24
    radius: int = 8

DARK = Tokens('#141513','#1c1e1b','#282b26','#e8e5dd','#a3a79c','#343730','#c5ad7f','#393e33','#535e6c','#d4c0aa','#9e9b8e','#83bf99','#d3b074')
LIGHT = Tokens('#f5f3ed','#eeece4','#e1dfd4','#242a23','#60685c','#d1d2c6','#79623c','#d9dfd0','#dce6e6','#e5d4bb','#b6ac98','#35794b','#8a6023')

def tokens(theme='dark'):
    return LIGHT if theme == 'light' else DARK

def stylesheet(theme='dark'):
    t=tokens(theme)
    arrow=(Path(__file__).resolve().parents[1]/'resources/chevron.svg').as_posix()
    return f'''
* {{ font-size:{t.body}px; }}
QWidget {{ color:{t.text}; }}
QMainWindow, QWidget#root, QDialog {{ background:{t.bg}; }}
QDialog#search-overlay {{ border:1px solid {t.line}; border-radius:8px; }}
QFrame#titlebar {{ background:{t.bg}; }}
QFrame#navigation {{ border-bottom:1px solid {t.line}; background:{t.bg}; }}
QLabel#brand {{ font-size:24px; font-weight:650; }}
QLabel#heading {{ font-size:{t.heading}px; font-weight:650; }}
QLabel#subheading, QLabel#eyebrow {{ color:{t.muted}; }}
QLabel#metric {{ font-size:31px; font-weight:600; }}
QLabel#status {{ color:{t.good}; }}
QLabel#notice {{ padding:8px 0; color:{t.muted}; }}
QFrame#card {{ border:none; border-top:1px solid {t.line}; background:transparent; }}
QFrame#metricBlock {{ background:transparent; border:none; }}
QFrame#context {{ background:{t.surface}; border-left:1px solid {t.line}; }}
QPushButton {{ background:{t.raised}; border:1px solid transparent; border-radius:{t.radius}px; padding:8px 13px; }}
QPushButton:hover {{ background:{t.selection}; border-color:{t.line}; }}
QPushButton:pressed {{ background:{t.line}; }}
QPushButton:disabled {{ color:{t.muted}; }}
QPushButton#primary {{ background:{t.accent}; color:{t.bg}; }}
QPushButton#nav, QPushButton#mode {{ border:none; background:transparent; color:{t.muted}; font-weight:600; padding:9px 14px; font-size:15px; }}
QPushButton#nav:checked {{ background:{t.text}; color:{t.bg}; border:1px solid {t.text}; border-radius:18px; }}
QPushButton#mode:checked {{ background:{t.raised}; color:{t.text}; border:1px solid {t.raised}; border-radius:18px; }}
QPushButton#window, QPushButton#close {{ background:transparent; border:none; border-radius:0; font-size:19px; padding:0; }}
QPushButton#window:hover {{ background:{t.raised}; }}
QPushButton#close:hover {{ background:#a63b3b; color:white; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{ background:{t.surface}; border:1px solid {t.line}; border-radius:6px; padding:7px; min-height:20px; selection-background-color:{t.selection}; }}
QLineEdit:focus {{ border-color:{t.accent}; }}
QComboBox QAbstractItemView {{ background:{t.surface}; selection-background-color:{t.selection}; }}
QCheckBox {{ spacing:9px; padding:5px 0; }}
QCheckBox::indicator {{ width:16px; height:16px; border:1px solid {t.muted}; border-radius:4px; }}
QCheckBox::indicator:checked {{ background:{t.accent}; }}
QTableView {{ background:{t.bg}; alternate-background-color:{t.surface}; border:none; selection-background-color:{t.selection}; selection-color:{t.text}; gridline-color:{t.line}; }}
QTableView::item {{ padding:8px; border-bottom:1px solid {t.line}; }}
QHeaderView::section {{ background:{t.bg}; color:{t.muted}; border:none; border-bottom:1px solid {t.line}; padding:10px 8px; font-weight:500; }}
QTextBrowser {{ background:transparent; border:none; padding:10px; }}
QListWidget, QTreeWidget {{ background:{t.bg}; border:none; alternate-background-color:{t.surface}; }}
QListWidget::item, QTreeWidget::item {{ padding:10px; border-bottom:1px solid {t.line}; }}
QListWidget::item:selected, QTreeWidget::item:selected {{ background:{t.selection}; }}
QScrollArea {{ border:none; background:transparent; }}
QScrollArea > QWidget > QWidget {{ background:{t.bg}; }}
QScrollBar:vertical {{ background:{t.bg}; width:8px; }}
QScrollBar::handle:vertical {{ background:{t.line}; border-radius:4px; min-height:24px; }}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{ height:0; }}
QSplitter::handle {{ background:{t.line}; width:1px; }}
QGroupBox {{ border:none; border-top:1px solid {t.line}; margin-top:22px; padding-top:20px; font-size:16px; font-weight:600; }}
QGroupBox::title {{ subcontrol-origin:margin; subcontrol-position:top left; padding:0 0 8px 0; }}
QToolTip,QMenu {{ background:{t.surface}; color:{t.text}; border:1px solid {t.line}; padding:5px; }}
QMenu::item {{ padding:7px 16px; }}
QMenu::item:selected {{ background:{t.selection}; }}
QPushButton:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTableView:focus, QTreeWidget:focus {{ border:1px solid {t.accent}; }}
QPushButton#nav:hover, QPushButton#mode:hover {{ background:{t.selection}; color:{t.text}; border:1px solid {t.line}; }}
QPushButton#nav:pressed, QPushButton#mode:pressed {{ background:{t.line}; }}
QPushButton#close:pressed {{ background:#7e2525; }}
QPushButton#window:pressed {{ background:{t.line}; }}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover, QLineEdit:hover {{ border-color:{t.muted}; }}
QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {{ color:{t.muted}; background:{t.bg}; }}
QComboBox::drop-down {{ border:none; width:26px; }}
QComboBox::down-arrow {{ image:url({arrow}); width:14px; height:14px; }}
QAbstractItemView {{ selection-color:{t.text}; outline:0; }}
QTableView::item:hover, QTreeWidget::item:hover, QListWidget::item:hover {{ background:{t.raised}; }}
QScrollBar:horizontal {{ background:{t.bg}; height:10px; }}
QScrollBar::handle:horizontal {{ background:{t.line}; border-radius:4px; min-width:24px; }}
QScrollBar::handle:hover {{ background:{t.muted}; }}
QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal {{ width:0; }}
'''
STYLE=stylesheet()
