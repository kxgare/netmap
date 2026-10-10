from PySide6.QtWidgets import QFrame,QHBoxLayout,QPushButton,QMessageBox,QSizePolicy
from netmap.ui.common import label

class NotificationBar(QFrame):
    """Shared status surface: concise text, accessible details, no traceback."""
    def __init__(self):
        super().__init__()
        layout=QHBoxLayout(self); layout.setContentsMargins(0,0,0,0)
        self.label=label('Ожидание данных…','subheading',True)
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);self.label.setMaximumHeight(38)
        layout.addWidget(self.label,1)
        self.details=QPushButton('Подробнее');self.details.hide();self.details.clicked.connect(self.show_details);layout.addWidget(self.details)
        self.close_button=QPushButton('×');self.close_button.hide();self.close_button.clicked.connect(self.dismiss);layout.addWidget(self.close_button)
        self.full='';self.latest='Ожидание данных…';self.error_active=False
    def setText(self,text):
        self.latest=text
        if not self.error_active: self.full=text;self.label.setText(text);self.details.hide()
    def notify(self,text):
        self.full=text;self.error_active=True;self.close_button.show()
        self.label.setText(text.split(':',1)[0] if ':' in text else text)
        self.details.show()
    def dismiss(self):
        self.error_active=False;self.close_button.hide();self.setText(self.latest)
    def show_details(self):
        box=QMessageBox(self);box.setWindowTitle('Сведения NetMap');box.setText(self.full)
        box.addButton('Закрыть',QMessageBox.ButtonRole.AcceptRole);box.exec()
