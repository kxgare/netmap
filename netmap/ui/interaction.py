from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractButton

def apply_interactions(root):
    """Set cursors on concrete widgets; Qt owns hover, pressed and focus states."""
    buttons=root.findChildren(QAbstractButton)
    if isinstance(root,QAbstractButton): buttons.append(root)
    for button in buttons:
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAttribute(Qt.WidgetAttribute.WA_Hover,True)
