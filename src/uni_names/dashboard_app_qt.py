import sys
from PyQt6 import QtCore, QtGui, QtWidgets


def try_qtawesome(name: str) -> QtGui.QIcon:
    try:
        import qtawesome as qta  # type: ignore
        return qta.icon(name)
    except Exception:
        # Fixed: Correctly access SP_ComputerIcon through StandardPixmap
        return QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)

#explain this code

class StatCard(QtWidgets.QFrame):
    def __init__(self, title: str, value: str, icon_name: str = "fa.users", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setMinimumHeight(120)
        self.setMaximumHeight(140)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        icon_lbl = QtWidgets.QLabel()
        ic = try_qtawesome(icon_name)
        if ic.isNull():
            ic = QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)
        icon_lbl.setPixmap(ic.pixmap(28, 28))
        icon_lbl.setFixedSize(32, 32)
        lay.addWidget(icon_lbl)

        text_box = QtWidgets.QVBoxLayout()
        title_lbl = QtWidgets.QLabel(title)
        title_lbl.setObjectName("CardTitle")
        value_lbl = QtWidgets.QLabel(value)
        value_lbl.setObjectName("CardValue")
        text_box.addWidget(title_lbl)
        text_box.addStretch()  # Fixed: removed argument
        text_box.addWidget(value_lbl)
        lay.addLayout(text_box)


class DonutWidget(QtWidgets.QWidget):
    def __init__(self, segments=None, center_text="$ 272,98", subtext="+2.52%", parent=None):
        super().__init__(parent)
        self.segments = segments or [
            (0.35, QtGui.QColor(124, 92, 255)),
            (0.25, QtGui.QColor(170, 130, 255)),
            (0.20, QtGui.QColor(110, 210, 120)),
            (0.20, QtGui.QColor(85, 70, 180)),
        ]
        self.center_text = center_text
        self.subtext = subtext
        self.setMinimumSize(260, 260)

    def paintEvent(self, ev: QtGui.QPaintEvent):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)
        outer = QtCore.QRectF(rect)
        inner = QtCore.QRectF(rect.adjusted(32, 32, -32, -32))
        start_angle = -90 * 16
        for ratio, color in self.segments:
            span = int(ratio * 360 * 16)
            pen = QtGui.QPen(color, 24, QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawArc(outer.adjusted(14, 14, -14, -14), start_angle, span)
            start_angle += span + 3 * 16
        # Center circle (background)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(20, 22, 35))
        p.drawEllipse(inner)
        # Center text
        p.setPen(QtGui.QColor(230, 232, 245))
        font = p.font(); font.setPointSize(18); font.setBold(True)
        p.setFont(font)
        p.drawText(inner, QtCore.Qt.AlignmentFlag.AlignCenter, self.center_text)
        # Subtext
        sub_rect = QtCore.QRectF(inner)
        sub_rect.moveTop(inner.center().y() + 8)
        p.setPen(QtGui.QColor(120, 255, 170))
        font2 = p.font(); font2.setPointSize(10); font2.setBold(False)
        p.setFont(font2)
        p.drawText(sub_rect, QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop, self.subtext)


class LineChartWidget(QtWidgets.QWidget):
    def __init__(self, series=None, parent=None):
        super().__init__(parent)
        self.series = series or [10, 11, 12, 13, 15, 16, 15.5, 16.2, 17.0, 18.0, 17.2]
        self.setMinimumHeight(260)

    def paintEvent(self, ev: QtGui.QPaintEvent):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        # gradient background
        grad = QtGui.QLinearGradient(QtCore.QPointF(rect.topLeft()), QtCore.QPointF(rect.bottomRight()))
        grad.setColorAt(0.0, QtGui.QColor(32, 24, 60))
        grad.setColorAt(1.0, QtGui.QColor(24, 20, 45))
        p.fillRect(rect, grad)
        # axes (subtle)
        p.setPen(QtGui.QPen(QtGui.QColor(70, 70, 100), 1))
        margin = 24
        chart = rect.adjusted(margin, margin, -margin, -margin)
        for i in range(5):
            y = chart.top() + i * chart.height() / 4
            p.drawLine(chart.left(), int(y), chart.right(), int(y))
        # polyline
        mx = max(self.series) if self.series else 1
        mn = min(self.series) if self.series else 0
        range_y = (mx - mn) or 1
        pts = []
        for i, v in enumerate(self.series):
            x = chart.left() + i * chart.width() / max(1, len(self.series) - 1)
            y = chart.bottom() - (v - mn) / range_y * chart.height()
            pts.append(QtCore.QPointF(x, y))
        p.setPen(QtGui.QPen(QtGui.QColor(140, 120, 255), 2.5))
        if len(pts) > 1:
            p.drawPolyline(QtGui.QPolygonF(pts))


class DashboardWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Uni Names Dashboard")
        self.resize(1280, 800)
        self._build_ui()
        # Always load dark theme
        import os
        qss_path = os.path.join(os.path.dirname(__file__), 'styles.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())

    def _build_ui(self):
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Sidebar
        side = QtWidgets.QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(64)
        v = QtWidgets.QVBoxLayout(side)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(10)
        for i, icon in enumerate(["fa.th", "fa.car", "fa.users", "fa.lock", "fa.cog"]):
            btn = QtWidgets.QToolButton()
            btn.setIcon(try_qtawesome(icon))
            btn.setIconSize(QtCore.QSize(24, 24))
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setObjectName("SideBtn")
            if i == 0:
                btn.setChecked(True)
            v.addWidget(btn)
        v.addStretch()
        root.addWidget(side)

        # Main area
        main = QtWidgets.QWidget()
        main_lay = QtWidgets.QVBoxLayout(main)
        main_lay.setSpacing(12)
        main_lay.setContentsMargins(0, 0, 0, 0)
        root.addWidget(main, 1)

        # Top bar
        top = QtWidgets.QFrame()
        top.setObjectName("TopBar")
        h = QtWidgets.QHBoxLayout(top)
        h.setContentsMargins(16, 12, 16, 12)
        h.setSpacing(12)
        search = QtWidgets.QLineEdit()
        search.setPlaceholderText("Search your today analysis")
        search.setObjectName("Search")
        h.addWidget(search, 1)
        notif = QtWidgets.QToolButton()
        notif.setIcon(try_qtawesome("fa.bell"))
        notif.setIconSize(QtCore.QSize(20, 20))
        h.addWidget(notif)
        avatar = QtWidgets.QToolButton()
        avatar.setText("LS")
        avatar.setObjectName("Avatar")
        avatar.setFixedSize(40, 40)
        h.addWidget(avatar)
        main_lay.addWidget(top)

        # Stat cards row
        cards = QtWidgets.QWidget()
        gc = QtWidgets.QGridLayout(cards)
        gc.setContentsMargins(0, 0, 0, 0)
        gc.setHorizontalSpacing(12)
        gc.setVerticalSpacing(12)
        gc.addWidget(StatCard("Total Cars", "750+", "fa.car"), 0, 0)
        gc.addWidget(StatCard("Daily trips", "1697+", "fa.road"), 0, 1)
        gc.addWidget(StatCard("Clients Annually", "85k+", "fa.users"), 0, 2)
        gc.addWidget(StatCard("Kilometers Daily", "2167+", "fa.tachometer"), 0, 3)
        main_lay.addWidget(cards)

        # Charts row
        charts = QtWidgets.QHBoxLayout()
        miles = QtWidgets.QFrame(); miles.setObjectName("Panel")
        miles_l = QtWidgets.QVBoxLayout(miles)
        miles_l.setContentsMargins(12, 12, 12, 12)
        miles_title = QtWidgets.QLabel("Miles Statistics")
        miles_title.setObjectName("PanelTitle")
        miles_l.addWidget(miles_title)
        miles_l.addWidget(LineChartWidget(), 1)
        charts.addWidget(miles, 2)

        analytic = QtWidgets.QFrame(); analytic.setObjectName("Panel")
        a_l = QtWidgets.QVBoxLayout(analytic)
        a_l.setContentsMargins(12, 12, 12, 12)
        a_l.addWidget(QtWidgets.QLabel("Analytic view"))
        a_l.addWidget(DonutWidget(), 1, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        charts.addWidget(analytic, 1)
        main_lay.addLayout(charts, 1)

        # Footer row placeholder
        footer = QtWidgets.QFrame(); footer.setObjectName("Footer")
        footer.setMinimumHeight(140)
        main_lay.addWidget(footer)


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = DashboardWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
