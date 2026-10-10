from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QLinearGradient
from PySide6.QtWidgets import QWidget


class Timeline(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.samples = []
        self.setMinimumHeight(230)

    def set_samples(self, samples):
        self.samples = samples
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        area = QRectF(45,25,self.width()-65,self.height()-65)
        p.setPen(QColor("#273c55"))
        maximum = max([s["total"] for s in self.samples] + [s["new"] for s in self.samples] + [1])
        for i in range(5):
            y = area.top()+area.height()*i/4
            p.drawLine(QPointF(area.left(),y),QPointF(area.right(),y))
            p.setPen(QColor("#829db9"))
            p.drawText(QRectF(0,y-10,37,20),Qt.AlignmentFlag.AlignRight,str(round(maximum*(1-i/4))))
            p.setPen(QColor("#273c55"))
        if not self.samples:
            p.setPen(QColor("#8da8c4"))
            p.drawText(area,Qt.AlignmentFlag.AlignCenter,"Пока нет наблюдений")
            return
        from datetime import datetime
        times = [datetime.fromisoformat(sample["time"]).timestamp() for sample in self.samples]
        duration = max(times[-1]-times[0],1)
        intervals = sorted(b-a for a,b in zip(times,times[1:]) if b>a)
        typical = intervals[len(intervals)//2] if intervals else 2
        for key, color in (("total","#61d6ef"),("new","#a992f7")):
            path = QPainterPath()
            for i, sample in enumerate(self.samples):
                x = area.left()+area.width()*(times[i]-times[0])/duration
                y = area.bottom()-area.height()*sample[key]/maximum
                if i == 0 or times[i]-times[i-1]>max(10,typical*3):
                    path.moveTo(x,y)
                else:
                    path.lineTo(x,y)
            p.setPen(QPen(QColor(color),2.5))
            p.drawPath(path)
            if len(self.samples) == 1:
                p.drawEllipse(QPointF(area.left(),area.bottom()-area.height()*self.samples[0][key]/maximum),3,3)
        from netmap.ui.table import display_time
        p.setPen(QColor("#829db9"))
        p.drawText(QRectF(area.left(),area.bottom()+10,180,25),display_time(self.samples[0]["time"]))
        p.drawText(QRectF(area.right()-180,area.bottom()+10,180,25),Qt.AlignmentFlag.AlignRight,display_time(self.samples[-1]["time"]))


class Bars(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = {}
        self.setMinimumHeight(220)

    def set_values(self, values):
        self.values = values
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.values:
            p.setPen(QColor("#8da8c4"))
            p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,"Нет данных")
            return
        max_value = max(self.values.values()) or 1
        rows = list(self.values.items())[:10]
        step = min(32,(self.height()-10)/len(rows))
        for i,(label,value) in enumerate(rows):
            y = 5+i*step
            p.setPen(QColor("#b3c8e1"))
            p.drawText(QRectF(0,y,145,step),Qt.AlignmentFlag.AlignVCenter,p.fontMetrics().elidedText(label,Qt.TextElideMode.ElideRight,140))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#273a55"))
            p.drawRoundedRect(QRectF(150,y+7,max(20,self.width()-198),12),5,5)
            p.setBrush(QColor("#759fea" if i%2 else "#5bc6df"))
            p.drawRoundedRect(QRectF(150,y+7,max(1,(self.width()-198)*value/max_value),12),5,5)
            p.setPen(QColor("#d9e9fc"))
            p.drawText(QRectF(self.width()-42,y,40,step),Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,str(value))
