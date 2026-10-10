STYLE = """
* { font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 13px; }
QMainWindow, QWidget#root { background: #0a101e; color: #dce7fb; }
QWidget { color: #dce7fb; }
QFrame#sidebar { background: #0d1527; border-right: 1px solid #213047; }
QFrame#titlebar { background: #0c1322; border-bottom: 1px solid #213047; }
QFrame#card { background: #111c30; border: 1px solid #25354d; border-radius: 14px; }
QLabel#brand { font-size: 25px; font-weight: 700; color: #eef6ff; }
QLabel#eyebrow { font-size: 11px; color: #7f9cbd; letter-spacing: 2px; }
QLabel#heading { font-size: 27px; font-weight: 650; color: #eef6ff; }
QLabel#subheading { color: #829bb9; font-size: 13px; }
QLabel#metric { font-size: 30px; font-weight: 650; color: #6bdaf3; }
QLabel#status { color: #6be4c1; }
QLabel#notice { color: #abc1dc; background: #152238; border: 1px solid #263d59; border-radius: 8px; padding: 8px; }
QPushButton { background: #19273e; border: 1px solid #2c405e; border-radius: 8px; padding: 9px 15px; color: #cfe1f9; }
QPushButton:hover { background: #253b5b; border-color: #4a7297; }
QPushButton:pressed { background: #304b70; }
QPushButton:disabled { color: #586c87; border-color: #203049; }
QPushButton#primary { background: #24587c; color: #d4f6ff; border-color: #3b94b7; }
QPushButton#nav { text-align: left; border: none; background: transparent; padding: 13px 18px; color: #91a7c5; }
QPushButton#nav:hover { background: #16263f; color: #e1eeff; }
QPushButton#nav:checked { background: #1d3253; color: #77dffc; border-left: 3px solid #75cfff; }
QPushButton#window { border: none; background: transparent; border-radius: 0px; font-size: 17px; padding: 0; }
QPushButton#window:hover { background: #233650; }
QPushButton#close:hover { background: #b83954; }
QPushButton#close { border: none; background: transparent; border-radius: 0; font-size: 19px; padding: 0; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit { background: #0e192b; border: 1px solid #2a3c57; border-radius: 7px; padding: 8px; min-height: 19px; selection-background-color: #296481; }
QLineEdit:focus, QComboBox:focus { border-color: #63c8e9; }
QComboBox QAbstractItemView { background: #14233b; selection-background-color: #294968; }
QCheckBox { spacing: 10px; padding: 5px 0; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #3e5678; border-radius: 4px; background: #152239; }
QCheckBox::indicator:checked { background: #50b4d1; border-color: #80d5ed; }
QTableView { background: #101a2c; alternate-background-color: #121e32; border: 1px solid #26364e; border-radius: 10px; gridline-color: #23334b; selection-background-color: #25425f; selection-color: #e9f7ff; }
QTableView::item { padding: 9px; border-bottom: 1px solid #1e2e44; }
QHeaderView::section { background: #17263d; color: #91abc9; border: none; border-bottom: 1px solid #30465f; padding: 11px; font-weight: 600; }
QTextBrowser { background: #101b2e; border: 1px solid #273b56; border-radius: 10px; padding: 12px; color: #cfdef0; }
QListWidget { background: #101a2c; border: 1px solid #273b56; border-radius: 10px; padding: 6px; }
QListWidget::item { padding: 12px; border-radius: 8px; }
QListWidget::item:selected { background: #243e5e; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #101a2c; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #34516d; border-radius: 4px; min-height: 25px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #22364f; color: #edf7ff; border: 1px solid #537da1; padding: 6px; }
QSplitter::handle { background: #19283f; width: 5px; }
QMenu { background: #17263c; border: 1px solid #3d536e; }
QMenu::item { padding: 8px 18px; }
QMenu::item:selected { background: #294664; }
QMessageBox { background: #101b2e; }
"""
