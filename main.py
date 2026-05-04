import sys
import os
import math
import hashlib
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QFrame, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QGridLayout, QFileDialog, QDialog, QFormLayout, QMessageBox,
    QComboBox, QTextEdit, QDateEdit, QScrollArea, QSizePolicy,
    QGraphicsDropShadowEffect, QScrollBar, QProgressBar, QSpacerItem
)
from PySide6.QtGui import (
    QPixmap, QColor, QCursor, QFont, QPainter, QPainterPath,
    QBrush, QPen, QLinearGradient, QRadialGradient, QPolygonF,
    QFontMetrics
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QDate, QSize,
    QRectF, QPointF, QTimer, Property
)

import qtawesome as qta
import database

# ─────────────────────────────────────────────
#  THEME
# ─────────────────────────────────────────────
class Theme:
    DARK = {
        "bg":          "#0D1117",
        "surface":     "#161B22",
        "surface2":    "#21262D",
        "border":      "#30363D",
        "text":        "#FFFFFF",
        "text_muted":  "#8B949E",
        "accent":      "#FFD700",
        "accent_dim":  "rgba(255,215,0,0.12)",
        "blue":        "#58A6FF",
        "green":       "#3FB950",
        "red":         "#FF6B6B",
        "orange":      "#F0883E",
        "purple":      "#D2A8FF",
        "teal":        "#79C0FF",
    }
    LIGHT = {
        "bg":          "#F6F8FA",
        "surface":     "#FFFFFF",
        "surface2":    "#EAEEF2",
        "border":      "#D0D7DE",
        "text":        "#1F2328",
        "text_muted":  "#636C76",
        "accent":      "#B8860B",
        "accent_dim":  "rgba(184,134,11,0.12)",
        "blue":        "#0969DA",
        "green":       "#1A7F37",
        "red":         "#CF222E",
        "orange":      "#BC4C00",
        "purple":      "#8250DF",
        "teal":        "#0969DA",
    }
    _current = "DARK"

    @classmethod
    def get(cls):
        return cls.DARK if cls._current == "DARK" else cls.LIGHT

    @classmethod
    def toggle(cls):
        cls._current = "LIGHT" if cls._current == "DARK" else "DARK"

    @classmethod
    def is_dark(cls):
        return cls._current == "DARK"


def T(key):
    return Theme.get()[key]


def table_style():
    t = Theme.get()
    return f"""
        QTableWidget {{ background-color: {t['surface']}; color: {t['text']}; gridline-color: {t['border']}; border: none; font-size: 13px; }}
        QHeaderView::section {{ background-color: {t['surface2']}; color: {t['text_muted']}; padding: 10px; border: 1px solid {t['border']}; font-weight: bold; }}
        QTableWidget::item {{ padding: 8px; border-bottom: 1px solid {t['surface2']}; }}
        QTableWidget::item:selected {{ background-color: {t['accent_dim']}; color: {t['accent']}; }}
        QScrollBar:vertical {{ background: {t['bg']}; width: 8px; border-radius: 4px; }}
        QScrollBar::handle:vertical {{ background: {t['border']}; border-radius: 4px; }}
    """


def input_style():
    t = Theme.get()
    return f"background-color: {t['bg']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 8px 12px; font-size: 13px;"


def dialog_style():
    t = Theme.get()
    return f"background-color: {t['surface']}; color: {t['text']};"


def label_style():
    return f"color: {T('text_muted')}; font-size: 13px;"


def make_btn(text, color=None, text_color="black", width=None, height=40, icon=None, icon_color=None):
    if color is None:
        color = T("accent")
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    if icon:
        btn.setIcon(qta.icon(icon, color=icon_color or text_color))
        btn.setIconSize(QSize(16, 16))
    w = f"min-width: {width}px;" if width else ""
    btn.setStyleSheet(f"""
        QPushButton {{ background-color: {color}; color: {text_color};
            border-radius: 8px; font-weight: bold; font-size: 13px;
            padding: 6px 18px; {w} min-height: {height}px; }}
        QPushButton:hover {{ border: 1px solid rgba(255,255,255,0.2); opacity: 0.9; }}
    """)
    return btn


def page_header(title, btn_text=None, btn_callback=None, btn_icon=None):
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    lbl = QLabel(title)
    lbl.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
    h.addWidget(lbl)
    h.addStretch()
    if btn_text and btn_callback:
        btn = make_btn(btn_text, T("green"), "white", icon=btn_icon, icon_color="white")
        btn.clicked.connect(btn_callback)
        h.addWidget(btn)
    return w


# ─────────────────────────────────────────────
#  AVATAR
# ─────────────────────────────────────────────
class AvatarWidget(QLabel):
    COLORS = ["#FF6B6B","#FFD700","#58A6FF","#3FB950","#F0883E",
              "#D2A8FF","#79C0FF","#A8D8A8","#FFA07A","#87CEEB"]

    def __init__(self, name="?", size=48, image_path=None):
        super().__init__()
        self.avatar_size = size
        self.setFixedSize(size, size)
        self.set_avatar(name, image_path)

    def set_avatar(self, name="?", image_path=None):
        self.name = name
        self.image_path = image_path
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        s = self.avatar_size
        path = QPainterPath()
        path.addEllipse(QRectF(0, 0, s, s))
        painter.setClipPath(path)

        if self.image_path and os.path.exists(self.image_path):
            pix = QPixmap(self.image_path).scaled(s, s, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap(0, 0, pix)
        else:
            initial = self.name[0].upper() if self.name else "?"
            idx = sum(ord(c) for c in self.name) % len(self.COLORS)
            color = QColor(self.COLORS[idx])
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(0, 0, s, s))
            painter.setPen(QPen(QColor("white")))
            font = QFont("Segoe UI", int(s * 0.36), QFont.Bold)
            painter.setFont(font)
            painter.drawText(QRectF(0, 0, s, s), Qt.AlignCenter, initial)
        painter.end()


# ─────────────────────────────────────────────
#  CHARTS
# ─────────────────────────────────────────────
class BarChartWidget(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.title = title
        self.data = []
        self._anim_progress = 0.0
        self._hover_index = -1
        self._bar_rects = []
        self.setMinimumHeight(200)
        self.setMouseTracking(True)
        self._animation = QPropertyAnimation(self, b"animationProgress")
        self._animation.setDuration(900)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def animationProgress(self):
        return self._anim_progress

    def setAnimationProgress(self, value):
        self._anim_progress = value
        self.update()

    animationProgress = Property(float, animationProgress, setAnimationProgress)

    def set_data(self, data):
        self.data = data
        self._hover_index = -1
        self._animation.stop()
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.start()
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        t = Theme.get()
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 40, 10, 30, 40
        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b
        max_val = max((v for _, v, _ in self.data), default=1) or 1
        bar_count = len(self.data)
        bar_gap = 12
        bar_w = (chart_w - bar_gap * (bar_count + 1)) / bar_count
        painter.setPen(QPen(QColor(t['text'])))
        font = QFont("Segoe UI", 11, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(pad_l, 4, chart_w, 22), Qt.AlignLeft, self.title)
        self._bar_rects = []
        for i, (label, value, color) in enumerate(self.data):
            x = pad_l + bar_gap * (i + 1) + bar_w * i
            animated_value = value * self._anim_progress
            bar_h = (animated_value / max_val) * (chart_h - 20)
            y = pad_t + chart_h - bar_h
            c = QColor(color)
            if i == self._hover_index:
                painter.setBrush(QBrush(c.lighter(130)))
            else:
                grad = QLinearGradient(x, y, x, y + bar_h)
                grad.setColorAt(0, c.lighter(120))
                grad.setColorAt(1, c.darker(110))
                painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            path = QPainterPath()
            rect = QRectF(x, y, bar_w, bar_h)
            path.addRoundedRect(rect, 4, 4)
            painter.drawPath(path)
            if i == self._hover_index:
                painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
                painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 6, 6)
            painter.setPen(QPen(QColor(t['text'])))
            font2 = QFont("Segoe UI", 9, QFont.Bold)
            painter.setFont(font2)
            painter.drawText(QRectF(x, y - 18, bar_w, 16), Qt.AlignCenter, str(int(animated_value)))
            font3 = QFont("Segoe UI", 8)
            painter.setFont(font3)
            painter.setPen(QPen(QColor(t['text_muted'])))
            painter.drawText(QRectF(x - 4, pad_t + chart_h + 4, bar_w + 8, 24), Qt.AlignCenter, label)
            self._bar_rects.append(rect)
        painter.end()

    def mouseMoveEvent(self, event):
        pos = event.position() if hasattr(event, 'position') else event.pos()
        hover_index = -1
        for i, rect in enumerate(self._bar_rects):
            if rect.contains(pos):
                hover_index = i
                break
        if hover_index != self._hover_index:
            self._hover_index = hover_index
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_index = -1
        self.update()
        super().leaveEvent(event)


class DonutChartWidget(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.title = title
        self.data = []
        self._anim_progress = 0.0
        self._hover_index = -1
        self._segment_angles = []
        self.setMinimumSize(200, 200)
        self.setMouseTracking(True)
        self._animation = QPropertyAnimation(self, b"animationProgress")
        self._animation.setDuration(900)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def animationProgress(self):
        return self._anim_progress

    def setAnimationProgress(self, value):
        self._anim_progress = value
        self.update()

    animationProgress = Property(float, animationProgress, setAnimationProgress)

    def set_data(self, data):
        self.data = data
        self._hover_index = -1
        self._animation.stop()
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.start()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        t = Theme.get()
        w, h = self.width(), self.height()
        side = min(w, h) - 40
        cx = w // 2
        cy = h // 2
        outer_r = side // 2
        inner_r = int(outer_r * 0.58)
        total = sum(v for _, v, _ in self.data) or 1
        start_angle = -90 * 16
        self._segment_angles = []
        current_start = start_angle
        for i, (label, value, color) in enumerate(self.data):
            span = int((value / total) * 360 * 16 * self._anim_progress)
            segment_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(Qt.NoPen)
            painter.drawPie(segment_rect, current_start, span)
            norm_start = current_start % (360 * 16)
            norm_end = (current_start + span) % (360 * 16)
            self._segment_angles.append((norm_start, norm_end, outer_r, inner_r))
            if i == self._hover_index and span > 0:
                highlight_path = QPainterPath()
                rect = QRectF(cx - outer_r - 4, cy - outer_r - 4, (outer_r + 4) * 2, (outer_r + 4) * 2)
                highlight_path.addEllipse(rect)
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor(255, 255, 255, 120), 3))
                painter.drawPath(highlight_path)
            current_start += span
        painter.setBrush(QBrush(QColor(t['surface'])))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2))
        painter.setPen(QPen(QColor(t['text'])))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(QRectF(cx - inner_r, cy - 14, inner_r * 2, 28), Qt.AlignCenter, self.title)
        legend_y = cy + outer_r + 8
        legend_x = cx - (len(self.data) * 70) // 2
        for i, (label, value, color) in enumerate(self.data):
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(legend_x, legend_y, 10, 10), 2, 2)
            painter.setPen(QPen(QColor(t['text_muted'])))
            painter.setFont(QFont("Segoe UI", 8))
            text = f"{label} ({value})"
            if i == self._hover_index:
                painter.setPen(QPen(QColor(t['text']), 1))
                painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(legend_x + 14, legend_y - 1, 56, 14), Qt.AlignLeft, text)
            legend_x += 80
        painter.end()

    def mouseMoveEvent(self, event):
        pos = event.position() if hasattr(event, 'position') else event.pos()
        rel_x = pos.x() - self.width() / 2
        rel_y = pos.y() - self.height() / 2
        dist = math.hypot(rel_x, rel_y)
        angle = int((90 - math.degrees(math.atan2(rel_y, rel_x))) * 16) % (360 * 16)
        hover_index = -1
        for i, (start, end, outer_r, inner_r) in enumerate(self._segment_angles):
            if inner_r < dist < outer_r:
                if start <= end:
                    if start <= angle <= end:
                        hover_index = i
                        break
                else:
                    if angle >= start or angle <= end:
                        hover_index = i
                        break
        if hover_index != self._hover_index:
            self._hover_index = hover_index
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_index = -1
        self.update()
        super().leaveEvent(event)


# ─────────────────────────────────────────────
#  LINE CHART WIDGET  (revenue trend)
# ─────────────────────────────────────────────
class LineChartWidget(QWidget):
    """Smooth animated line/area chart for revenue trends."""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.title = title
        self.datasets = []        # list of (label, [(x_label, value)], color)
        self._anim_progress = 0.0
        self._hover_x = -1
        self._point_positions = []  # list of list of (px, py, value, label)
        self.setMinimumHeight(220)
        self.setMouseTracking(True)

        self._animation = QPropertyAnimation(self, b"animProgress")
        self._animation.setDuration(1000)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def animProgress(self):
        return self._anim_progress

    def setAnimProgress(self, v):
        self._anim_progress = v
        self.update()

    animProgress = Property(float, animProgress, setAnimProgress)

    def set_data(self, datasets):
        """datasets: list of (label, [(x_label, value), ...], color)"""
        self.datasets = datasets
        self._hover_x = -1
        self._animation.stop()
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.start()

    def paintEvent(self, event):
        if not self.datasets:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        t = Theme.get()
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 56, 20, 36, 44

        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b

        # Collect all values to find global max
        all_values = [v for _, pts, _ in self.datasets for _, v in pts]
        max_val = max(all_values, default=1) or 1

        # Draw title
        painter.setPen(QPen(QColor(t['text'])))
        painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
        painter.drawText(QRectF(pad_l, 4, chart_w, 24), Qt.AlignLeft | Qt.AlignVCenter, self.title)

        # Y-axis gridlines + labels
        grid_steps = 4
        painter.setFont(QFont("Segoe UI", 8))
        for i in range(grid_steps + 1):
            y = pad_t + chart_h - (i / grid_steps) * chart_h
            val = (i / grid_steps) * max_val
            painter.setPen(QPen(QColor(t['border']), 1, Qt.DashLine))
            painter.drawLine(int(pad_l), int(y), int(w - pad_r), int(y))
            painter.setPen(QPen(QColor(t['text_muted'])))
            if val >= 1000:
                lbl = f"₱{val/1000:.0f}k"
            else:
                lbl = f"₱{val:.0f}"
            painter.drawText(QRectF(0, y - 8, pad_l - 4, 16), Qt.AlignRight | Qt.AlignVCenter, lbl)

        # Determine x positions from first dataset
        if not self.datasets[0][1]:
            painter.end()
            return
        x_labels = [lbl for lbl, _ in self.datasets[0][1]]
        n = len(x_labels)
        if n < 2:
            painter.end()
            return
        x_step = chart_w / (n - 1)

        # X-axis labels
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QPen(QColor(t['text_muted'])))
        for i, lbl in enumerate(x_labels):
            px = pad_l + i * x_step
            painter.drawText(QRectF(px - 30, pad_t + chart_h + 6, 60, 20),
                             Qt.AlignCenter, lbl)

        # Hover vertical line
        self._point_positions = []
        if 0 <= self._hover_x < n:
            hx = pad_l + self._hover_x * x_step
            painter.setPen(QPen(QColor(t['text_muted']), 1, Qt.DashLine))
            painter.drawLine(int(hx), pad_t, int(hx), pad_t + chart_h)

        # Draw each dataset as filled area + line
        for ds_idx, (ds_label, pts, color) in enumerate(self.datasets):
            if len(pts) < 2:
                continue
            pts_draw = []
            for i, (lbl, val) in enumerate(pts):
                px = pad_l + i * x_step
                animated = val * self._anim_progress
                py = pad_t + chart_h - (animated / max_val) * chart_h
                pts_draw.append((px, py, val, lbl))

            c = QColor(color)

            # Filled area under line
            area_path = QPainterPath()
            area_path.moveTo(pts_draw[0][0], pad_t + chart_h)
            for px, py, _, _ in pts_draw:
                area_path.lineTo(px, py)
            area_path.lineTo(pts_draw[-1][0], pad_t + chart_h)
            area_path.closeSubpath()
            fill_color = QColor(c)
            fill_color.setAlpha(40)
            painter.setBrush(QBrush(fill_color))
            painter.setPen(Qt.NoPen)
            painter.drawPath(area_path)

            # Line
            line_pen = QPen(c, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(line_pen)
            painter.setBrush(Qt.NoBrush)
            line_path = QPainterPath()
            line_path.moveTo(pts_draw[0][0], pts_draw[0][1])
            for px, py, _, _ in pts_draw[1:]:
                line_path.lineTo(px, py)
            painter.drawPath(line_path)

            # Data points
            self._point_positions.append(pts_draw)
            for i, (px, py, val, lbl) in enumerate(pts_draw):
                is_hover = (self._hover_x == i)
                r = 6 if is_hover else 4
                painter.setBrush(QBrush(c))
                painter.setPen(QPen(QColor(t['surface']), 2))
                painter.drawEllipse(QRectF(px - r, py - r, r * 2, r * 2))

                # Tooltip on hover
                if is_hover:
                    tooltip = f"₱{val:,.0f}"
                    fm = QFontMetrics(QFont("Segoe UI", 9, QFont.Bold))
                    tw = fm.horizontalAdvance(tooltip) + 16
                    th = 24
                    tx = min(px - tw / 2, w - pad_r - tw)
                    ty = py - th - 8
                    painter.setBrush(QBrush(QColor(t['surface2'])))
                    painter.setPen(QPen(QColor(c), 1))
                    painter.drawRoundedRect(QRectF(tx, ty, tw, th), 6, 6)
                    painter.setPen(QPen(c))
                    painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    painter.drawText(QRectF(tx, ty, tw, th), Qt.AlignCenter, tooltip)

        # Legend (multi-dataset)
        if len(self.datasets) > 1:
            lx = pad_l
            ly = pad_t + chart_h + 28
            for ds_label, _, color in self.datasets:
                c = QColor(color)
                painter.setBrush(QBrush(c))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(QRectF(lx, ly, 10, 10), 2, 2)
                painter.setPen(QPen(QColor(t['text_muted'])))
                painter.setFont(QFont("Segoe UI", 8))
                painter.drawText(QRectF(lx + 14, ly - 1, 80, 14), Qt.AlignLeft, ds_label)
                lx += 100

        painter.end()

    def mouseMoveEvent(self, event):
        pos = event.position() if hasattr(event, 'position') else event.pos()
        if self.datasets and self.datasets[0][1]:
            n = len(self.datasets[0][1])
            if n >= 2:
                pad_l, pad_r = 56, 20
                chart_w = self.width() - pad_l - pad_r
                x_step = chart_w / (n - 1)
                hover = round((pos.x() - pad_l) / x_step) if x_step > 0 else -1
                hover = max(0, min(n - 1, hover))
                if hover != self._hover_x:
                    self._hover_x = hover
                    self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_x = -1
        self.update()
        super().leaveEvent(event)


class ThemeToggleBtn(QWidget):
    def __init__(self, on_toggle):
        super().__init__()
        self.on_toggle = on_toggle
        self.setFixedSize(56, 28)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        Theme.toggle()
        self.update()
        self.on_toggle()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        is_dark = Theme.is_dark()
        track_color = QColor("#30363D") if is_dark else QColor("#D0D7DE")
        painter.setBrush(QBrush(track_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(0, 4, 56, 20), 10, 10)
        thumb_x = 32 if is_dark else 4
        thumb_color = QColor("#FFD700") if is_dark else QColor("#636C76")
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(QRectF(thumb_x, 2, 24, 24))
        icon_name = "fa5s.moon" if is_dark else "fa5s.sun"
        icon_color = "#FFD700" if is_dark else "white"
        pix = qta.icon(icon_name, color=icon_color).pixmap(QSize(14, 14))
        painter.drawPixmap(int(thumb_x + 5), 7, pix)
        painter.end()


# ─────────────────────────────────────────────
#  INTERACTIVE STAT CARD (clickable)
# ─────────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, title, value, color, icon_name=None, subtitle=None, on_click=None):
        super().__init__()
        self.on_click = on_click
        self.setMinimumSize(160, 120)
        self.setFrameShape(QFrame.NoFrame)
        self.setCursor(Qt.PointingHandCursor if on_click else Qt.ArrowCursor)
        self._color = color
        self._apply_style(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        top_row.addWidget(t_lbl)
        top_row.addStretch()
        if icon_name:
            icon_lbl = QLabel()
            pix = qta.icon(icon_name, color=color).pixmap(QSize(20, 20))
            icon_lbl.setPixmap(pix)
            icon_lbl.setStyleSheet("border: none; background: transparent;")
            top_row.addWidget(icon_lbl)
        layout.addLayout(top_row)

        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"color: {color}; font-size: 36px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(self.value_label)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 11px; border: none; background: transparent;")
            layout.addWidget(sub_lbl)

        if on_click:
            arrow = QLabel("→ View details")
            arrow.setStyleSheet(f"color: {color}; font-size: 11px; border: none; background: transparent; margin-top: 2px;")
            layout.addWidget(arrow)

    def _apply_style(self, hovered):
        t = Theme.get()
        border = self._color if hovered else t['border']
        bg = t['surface2'] if hovered else t['surface']
        self.setStyleSheet(f"background-color: {bg}; border-radius: 16px; border: 1px solid {border};")

    def set_value(self, v):
        self.value_label.setText(str(v))

    def enterEvent(self, event):
        if self.on_click:
            self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click()
        super().mousePressEvent(event)


# ─────────────────────────────────────────────
#  MAINTENANCE CARD (interactive inline card)
# ─────────────────────────────────────────────
class MaintenanceCardWidget(QFrame):
    def __init__(self, request, on_resolve, on_view):
        super().__init__()
        t = Theme.get()
        priority_colors = {"High": t['red'], "Medium": t['accent'], "Low": t['green']}
        p_color = priority_colors.get(request.get('priority', 'Low'), t['text_muted'])
        self.setStyleSheet(f"background: {t['surface2']}; border-radius: 12px; border-left: 4px solid {p_color};")
        self.setMinimumHeight(90)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(3)

        title_row = QHBoxLayout()
        room_lbl = QLabel(f"Room {request.get('room_number','?')}")
        room_lbl.setStyleSheet(f"color: {t['text']}; font-weight: bold; font-size: 13px; background: transparent; border: none;")
        priority_badge = QLabel(request.get('priority','?'))
        priority_badge.setStyleSheet(f"color: {p_color}; font-size: 11px; font-weight: bold; background: transparent; border: none; padding: 2px 8px;")
        title_row.addWidget(room_lbl)
        title_row.addWidget(priority_badge)
        title_row.addStretch()
        info.addLayout(title_row)

        issue_lbl = QLabel(str(request.get('description',''))[:80] + ('…' if len(str(request.get('description',''))) > 80 else ''))
        issue_lbl.setStyleSheet(f"color: {t['text_muted']}; font-size: 12px; background: transparent; border: none;")
        info.addWidget(issue_lbl)

        renter_lbl = QLabel(f"Reported by: {request.get('renter_name','?')}")
        renter_lbl.setStyleSheet(f"color: {t['text_muted']}; font-size: 11px; background: transparent; border: none;")
        info.addWidget(renter_lbl)

        row.addLayout(info, stretch=1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(6)
        resolve_btn = QPushButton("✓ Resolve")
        resolve_btn.setCursor(Qt.PointingHandCursor)
        resolve_btn.setStyleSheet(f"background: {t['green']}; color: white; border-radius: 6px; font-size: 11px; font-weight: bold; padding: 4px 12px; border: none;")
        resolve_btn.clicked.connect(on_resolve)
        view_btn = QPushButton("View")
        view_btn.setCursor(Qt.PointingHandCursor)
        view_btn.setStyleSheet(f"background: transparent; color: {t['blue']}; border: 1px solid {t['blue']}; border-radius: 6px; font-size: 11px; padding: 4px 12px;")
        view_btn.clicked.connect(on_view)
        btn_col.addWidget(resolve_btn)
        btn_col.addWidget(view_btn)
        row.addLayout(btn_col)


# ─────────────────────────────────────────────
#  ROOM CARD WIDGET
# ─────────────────────────────────────────────
class RoomCardWidget(QFrame):
    def __init__(self, room, on_click=None):
        super().__init__()
        t = Theme.get()
        status = room.get('status', 'Available')
        status_colors = {
            'Available': t['green'],
            'Full': t['red'],
            'Under Maintenance': t['orange'],
            'Reserved': t['blue'],
        }
        s_color = status_colors.get(status, t['text_muted'])

        self.setStyleSheet(f"""
            QFrame {{
                background: {t['surface']};
                border-radius: 14px;
                border: 1px solid {t['border']};
            }}
            QFrame:hover {{
                border: 1px solid {s_color};
            }}
        """)
        self.setFixedSize(200, 160)
        self.setCursor(Qt.PointingHandCursor if on_click else Qt.ArrowCursor)
        if on_click:
            self.mousePressEvent = lambda e: on_click(room)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(5)

        top = QHBoxLayout()
        room_no = QLabel(f"Room {room.get('room_number','?')}")
        room_no.setStyleSheet(f"color: {t['text']}; font-size: 15px; font-weight: bold; background: transparent; border: none;")
        status_dot = QLabel(f"● {status}")
        status_dot.setStyleSheet(f"color: {s_color}; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        top.addWidget(room_no)
        top.addStretch()
        layout.addLayout(top)
        layout.addWidget(status_dot)

        floor_lbl = QLabel(f"Floor: {room.get('floor_level','?')}")
        floor_lbl.setStyleSheet(f"color: {t['text_muted']}; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(floor_lbl)

        # Occupancy bar
        cap = room.get('capacity', 1) or 1
        occ = room.get('occupied', 0)
        pct = int((occ / cap) * 100)
        occ_lbl = QLabel(f"{occ}/{cap} occupied")
        occ_lbl.setStyleSheet(f"color: {t['text_muted']}; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(occ_lbl)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(pct)
        bar.setFixedHeight(6)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ background: {t['border']}; border-radius: 3px; border: none; }}
            QProgressBar::chunk {{ background: {s_color}; border-radius: 3px; }}
        """)
        layout.addWidget(bar)

        rate_lbl = QLabel(f"₱{room.get('monthly_rate',0):,.0f}/mo")
        rate_lbl.setStyleSheet(f"color: {t['accent']}; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(rate_lbl)


# ─────────────────────────────────────────────
#  DIALOGS
# ─────────────────────────────────────────────
class PersonDetailDialog(QDialog):
    def __init__(self, parent, person_data, person_type="renter"):
        super().__init__(parent)
        self.person_data = person_data
        self.person_type = person_type
        self.setWindowTitle("Person Details")
        self.setFixedWidth(480)
        self.setStyleSheet(dialog_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)
        header = QHBoxLayout()
        name = f"{person_data.get('first_name','')} {person_data.get('last_name','')}".strip()
        profile_path = person_data.get('profile_path') or person_data.get('profile_pic_path')
        avatar = AvatarWidget(name, 80, profile_path)
        header.addWidget(avatar)
        info_col = QVBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color: {T('text')}; font-size: 20px; font-weight: bold;")
        info_col.addWidget(name_lbl)
        if person_type == "renter":
            status = person_data.get('renter_status', '—')
            status_colors = {"Active": T("green"), "Inactive": T("text_muted"), "Blacklisted": T("red")}
            s_color = status_colors.get(status, T("text_muted"))
        else:
            status = person_data.get('role', '—')
            s_color = T("blue")
        status_lbl = QLabel(f"● {status}")
        status_lbl.setStyleSheet(f"color: {s_color}; font-size: 13px; font-weight: bold;")
        info_col.addWidget(status_lbl)
        header.addLayout(info_col)
        header.addStretch()
        layout.addLayout(header)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {T('border')}; max-height: 1px;")
        layout.addWidget(line)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        grid = QGridLayout(scroll_content)
        grid.setSpacing(10)
        if person_type == "renter":
            fields = [
                ("Gender",        person_data.get('gender')),
                ("Occupation",    person_data.get('occupation_type')),
                ("Institution",   person_data.get('institution_employer')),
                ("Contact",       person_data.get('contact_number')),
                ("Email",         person_data.get('email')),
                ("ID Type",       person_data.get('id_type')),
                ("ID Number",     person_data.get('id_number')),
                ("Address",       person_data.get('address')),
                ("Emerg. Name",   person_data.get('emergency_contact_name')),
                ("Emerg. Number", person_data.get('emergency_contact_number')),
            ]
        else:
            fields = [
                ("Username",   person_data.get('username')),
                ("Role",       person_data.get('role')),
                ("Email",      person_data.get('email')),
                ("Contact",    person_data.get('contact_number')),
                ("Joined",     str(person_data.get('created_at', '—'))),
            ]
        row = 0
        for label_text, value in fields:
            if value:
                lbl = QLabel(label_text + ":")
                lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px; font-weight: bold;")
                val = QLabel(str(value))
                val.setStyleSheet(f"color: {T('text')}; font-size: 13px;")
                val.setWordWrap(True)
                grid.addWidget(lbl, row, 0)
                grid.addWidget(val, row, 1)
                row += 1
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        close_btn = make_btn("Close", T("surface2"), T("text"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class MaintenanceDetailDialog(QDialog):
    def __init__(self, parent, request):
        super().__init__(parent)
        self.setWindowTitle("Maintenance Request Detail")
        self.setFixedWidth(440)
        self.setStyleSheet(dialog_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)
        t = Theme.get()
        priority_colors = {"High": t['red'], "Medium": t['accent'], "Low": t['green']}
        p_color = priority_colors.get(request.get('priority', ''), t['text'])
        title_lbl = QLabel(f"Room {request.get('room_number','?')} — Maintenance")
        title_lbl.setStyleSheet(f"color: {T('text')}; font-size: 18px; font-weight: bold;")
        layout.addWidget(title_lbl)
        fields = [
            ("Renter", request.get('renter_name', '—')),
            ("Issue", request.get('description', '—')),
            ("Priority", request.get('priority', '—')),
            ("Status", request.get('status', '—')),
            ("Date", str(request.get('request_date', '—'))),
        ]
        for lbl, val in fields:
            row = QHBoxLayout()
            l = QLabel(f"{lbl}:")
            l.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px; font-weight: bold; min-width: 80px;")
            v = QLabel(str(val))
            v.setStyleSheet(f"color: {T('text')}; font-size: 13px;")
            v.setWordWrap(True)
            row.addWidget(l)
            row.addWidget(v, stretch=1)
            layout.addLayout(row)
        close_btn = make_btn("Close", T("surface2"), T("text"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class RenterSelfProfileDialog(QDialog):
    def __init__(self, parent, name, person_id, person_type="renter"):
        super().__init__(parent)
        self.person_id = person_id
        self.person_type = person_type
        self.chosen_path = None
        self.setWindowTitle(f"Set Profile Picture — {name}")
        self.setFixedWidth(380)
        self.setStyleSheet(dialog_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignCenter)
        title = QLabel(f"Hello, {name}!")
        title.setStyleSheet(f"color: {T('text')}; font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        sub = QLabel("You can set your profile picture here.\nThis step is optional — you can skip it.")
        sub.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px;")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        layout.addWidget(sub)
        self.avatar_preview = AvatarWidget(name, 100)
        layout.addWidget(self.avatar_preview, alignment=Qt.AlignCenter)
        choose_btn = make_btn("  Choose Photo", T("blue"), "white", icon="fa5s.camera", icon_color="white")
        choose_btn.clicked.connect(self._choose_photo)
        layout.addWidget(choose_btn)
        self.path_label = QLabel("No photo selected")
        self.path_label.setStyleSheet(f"color: {T('text_muted')}; font-size: 11px;")
        self.path_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.path_label)
        btns = QHBoxLayout()
        skip_btn = make_btn("Skip", T("surface2"), T("text"))
        save_btn = make_btn("  Save", T("green"), "white", icon="fa5s.save", icon_color="white")
        skip_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self.accept)
        btns.addWidget(skip_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _choose_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose Profile Picture", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.chosen_path = path
            self.path_label.setText(f"✓ {os.path.basename(path)[:30]}")
            self.avatar_preview.set_avatar(self.avatar_preview.name, path)
            self.avatar_preview.update()


class StaffDialog(QDialog):
    def __init__(self, parent, staff=None):
        super().__init__(parent)
        self.setWindowTitle("Add Staff" if not staff else "Edit Staff")
        self.setFixedWidth(460)
        self.setStyleSheet(dialog_style())
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        def inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        self.full_name = inp("Full Name")
        self.username  = inp("Username")
        self.password  = inp("Password (leave blank to keep)")
        self.password.setEchoMode(QLineEdit.Password)
        self.role = QComboBox()
        self.role.addItems(["Admin", "Staff", "Maintenance", "Security"])
        self.role.setStyleSheet(input_style())
        self.email   = inp("email@example.com")
        self.contact = inp("09XXXXXXXXX")
        layout.addRow("Full Name*:", self.full_name)
        layout.addRow("Username*:",  self.username)
        layout.addRow("Password:",   self.password)
        layout.addRow("Role:",       self.role)
        layout.addRow("Email:",      self.email)
        layout.addRow("Contact:",    self.contact)
        if staff:
            self.full_name.setText(staff.get('full_name', ''))
            self.username.setText(staff.get('username', ''))
            self.role.setCurrentText(staff.get('role', 'Staff'))
            self.email.setText(staff.get('email', '') or '')
            self.contact.setText(staff.get('contact_number', '') or '')
        save_btn = make_btn("  Save", T("green"), "white", icon="fa5s.save", icon_color="white")
        save_btn.clicked.connect(self._validate_and_accept)
        layout.addRow(save_btn)

    def _validate_and_accept(self):
        if not self.full_name.text().strip() or not self.username.text().strip():
            QMessageBox.warning(self, "Missing", "Full name and username are required.")
            return
        self.accept()

    def get_data(self):
        d = dict(
            full_name=self.full_name.text().strip(),
            username=self.username.text().strip(),
            role=self.role.currentText(),
            email=self.email.text().strip() or None,
            contact_number=self.contact.text().strip() or None,
        )
        pw = self.password.text().strip()
        if pw:
            d['password'] = pw
        return d


class RoomDialog(QDialog):
    def __init__(self, parent, room=None):
        super().__init__(parent)
        self.setWindowTitle("Add Room" if not room else "Edit Room")
        self.setFixedWidth(460)
        self.setStyleSheet(dialog_style())
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        def inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        self.room_number  = inp("e.g. 101")
        self.floor_level  = QComboBox()
        self.floor_level.addItems(["Ground Floor", "2nd Floor", "3rd Floor", "4th Floor"])
        self.floor_level.setStyleSheet(input_style())
        self.monthly_rate = inp("e.g. 3500")
        self.capacity     = inp("e.g. 4")
        self.status       = QComboBox()
        self.status.addItems(["Available", "Full", "Under Maintenance", "Reserved"])
        self.status.setStyleSheet(input_style())
        self.description  = QTextEdit()
        self.description.setFixedHeight(70)
        self.description.setStyleSheet(input_style())

        layout.addRow("Room No.*:", self.room_number)
        layout.addRow("Floor:",     self.floor_level)
        layout.addRow("Rate (₱):",  self.monthly_rate)
        layout.addRow("Capacity:",  self.capacity)
        layout.addRow("Status:",    self.status)
        layout.addRow("Notes:",     self.description)

        if room:
            self.room_number.setText(str(room.get('room_number', '')))
            self.floor_level.setCurrentText(room.get('floor_level', ''))
            self.monthly_rate.setText(str(room.get('monthly_rate', '')))
            self.capacity.setText(str(room.get('capacity', '')))
            self.status.setCurrentText(room.get('status', 'Available'))
            self.description.setPlainText(room.get('description', '') or '')

        save_btn = make_btn("  Save", T("green"), "white", icon="fa5s.save", icon_color="white")
        save_btn.clicked.connect(self.accept)
        layout.addRow(save_btn)

    def get_data(self):
        return dict(
            room_number=self.room_number.text().strip(),
            floor_level=self.floor_level.currentText(),
            monthly_rate=float(self.monthly_rate.text() or 0),
            capacity=int(self.capacity.text() or 0),
            status=self.status.currentText(),
            description=self.description.toPlainText().strip()
        )


class PaymentDialog(QDialog):
    def __init__(self, parent, renters):
        super().__init__(parent)
        self.setWindowTitle("Record Payment")
        self.setFixedWidth(440)
        self.setStyleSheet(dialog_style())
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        def inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        self.invoice      = inp("e.g. INV-2026-001")
        self.renter_combo = QComboBox()
        self.renter_combo.setStyleSheet(input_style())
        self._renter_ids  = []
        for r in renters:
            self.renter_combo.addItem(f"{r['first_name']} {r['last_name']}")
            self._renter_ids.append(r['renter_id'])
        self.amount       = inp("e.g. 1800.00")
        self.balance      = inp("Remaining balance (0 if fully paid)")
        self.method       = QComboBox()
        self.method.addItems(["Cash", "GCash", "Bank Transfer", "Other"])
        self.method.setStyleSheet(input_style())
        self.reference    = inp("Reference # (optional)")
        self.billing_month= inp("e.g. May 2026")
        self.pay_date     = QDateEdit(QDate.currentDate())
        self.pay_date.setCalendarPopup(True)
        self.pay_date.setStyleSheet(input_style())
        self.status       = QComboBox()
        self.status.addItems(["Paid", "Partial", "Pending", "Overdue", "Advanced"])
        self.status.setStyleSheet(input_style())
        self.remarks      = inp("Remarks (optional)")

        layout.addRow("Invoice No*:",   self.invoice)
        layout.addRow("Renter*:",       self.renter_combo)
        layout.addRow("Amount*:",       self.amount)
        layout.addRow("Balance:",       self.balance)
        layout.addRow("Method:",        self.method)
        layout.addRow("Reference #:",   self.reference)
        layout.addRow("Billing Month:", self.billing_month)
        layout.addRow("Payment Date:",  self.pay_date)
        layout.addRow("Status:",        self.status)
        layout.addRow("Remarks:",       self.remarks)

        save_btn = make_btn("  Save", T("green"), "white", icon="fa5s.save", icon_color="white")
        save_btn.clicked.connect(self.accept)
        layout.addRow(save_btn)

    def get_data(self):
        return dict(
            invoice_number=self.invoice.text().strip(),
            renter_id=self._renter_ids[self.renter_combo.currentIndex()] if self._renter_ids else None,
            amount=float(self.amount.text() or 0),
            balance_amount=float(self.balance.text() or 0),
            payment_method=self.method.currentText(),
            billing_month=self.billing_month.text().strip(),
            payment_date=self.pay_date.date().toString("yyyy-MM-dd"),
            status=self.status.currentText(),
            reference_number=self.reference.text().strip() or None,
            remarks=self.remarks.text().strip() or None,
            processed_by=None
        )


class MaintenanceDialog(QDialog):
    def __init__(self, parent, rooms, renters):
        super().__init__(parent)
        self.setWindowTitle("Add Maintenance Request")
        self.setFixedWidth(440)
        self.setStyleSheet(dialog_style())
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        self.room_combo = QComboBox()
        self.room_combo.setStyleSheet(input_style())
        self._room_ids = []
        for r in rooms:
            self.room_combo.addItem(f"Room {r['room_number']} ({r['floor_level']})")
            self._room_ids.append(r['room_id'])
        self.renter_combo = QComboBox()
        self.renter_combo.setStyleSheet(input_style())
        self._renter_ids = []
        for r in renters:
            self.renter_combo.addItem(f"{r['first_name']} {r['last_name']}")
            self._renter_ids.append(r['renter_id'])
        self.description = QTextEdit()
        self.description.setFixedHeight(80)
        self.description.setStyleSheet(input_style())
        self.priority = QComboBox()
        self.priority.addItems(["Low", "Medium", "High"])
        self.priority.setCurrentText("Medium")
        self.priority.setStyleSheet(input_style())
        layout.addRow("Room*:",    self.room_combo)
        layout.addRow("Renter*:",  self.renter_combo)
        layout.addRow("Issue*:",   self.description)
        layout.addRow("Priority:", self.priority)
        save_btn = make_btn("  Save", T("green"), "white", icon="fa5s.save", icon_color="white")
        save_btn.clicked.connect(self.accept)
        layout.addRow(save_btn)

    def get_data(self):
        return dict(
            room_id=self._room_ids[self.room_combo.currentIndex()] if self._room_ids else None,
            renter_id=self._renter_ids[self.renter_combo.currentIndex()] if self._renter_ids else None,
            description=self.description.toPlainText().strip(),
            priority=self.priority.currentText()
        )


class VisitorDialog(QDialog):
    def __init__(self, parent, renters):
        super().__init__(parent)
        self.setWindowTitle("Log Visitor In")
        self.setFixedWidth(400)
        self.setStyleSheet(dialog_style())
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        def inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        self.visitor_name = inp("Visitor Full Name")
        self.relationship = inp("e.g. Parent, Sibling, Friend")
        self.renter_combo = QComboBox()
        self.renter_combo.setStyleSheet(input_style())
        self._renter_ids  = []
        for r in renters:
            self.renter_combo.addItem(f"{r['first_name']} {r['last_name']}")
            self._renter_ids.append(r['renter_id'])
        layout.addRow("Visitor Name*:", self.visitor_name)
        layout.addRow("Relationship:",  self.relationship)
        layout.addRow("Visiting*:",     self.renter_combo)
        save_btn = make_btn("  Log In", T("green"), "white", icon="fa5s.sign-in-alt", icon_color="white")
        save_btn.clicked.connect(self.accept)
        layout.addRow(save_btn)

    def get_data(self):
        return dict(
            renter_id=self._renter_ids[self.renter_combo.currentIndex()] if self._renter_ids else None,
            visitor_name=self.visitor_name.text().strip(),
            relationship=self.relationship.text().strip()
        )


class RenterDialog(QDialog):
    def __init__(self, parent, renter=None):
        super().__init__(parent)
        self.setWindowTitle("Register Renter" if not renter else "Edit Renter")
        self.setFixedWidth(500)
        self.setStyleSheet(dialog_style())
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 24, 24, 24)

        def inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        self.first_name  = inp("First Name")
        self.middle_name = inp("Middle Name (optional)")
        self.last_name   = inp("Last Name")
        self.gender      = QComboBox()
        self.gender.addItems(["Male", "Female", "Other"])
        self.gender.setStyleSheet(input_style())
        self.occ_type    = QComboBox()
        self.occ_type.addItems(["Student", "Professional", "Other"])
        self.occ_type.setStyleSheet(input_style())
        self.institution = inp("School / Company")
        self.contact     = inp("09XXXXXXXXX")
        self.email       = inp("email@example.com")
        self.id_type     = QComboBox()
        self.id_type.addItems(["School ID","National ID","Driver's License","Passport","Other"])
        self.id_type.setStyleSheet(input_style())
        self.id_number   = inp("ID Number")
        self.address     = inp("Home Address")
        self.emerg_name  = inp("Emergency Contact Name")
        self.emerg_num   = inp("Emergency Contact Number")
        self.status      = QComboBox()
        self.status.addItems(["Active", "Inactive", "Blacklisted"])
        self.status.setStyleSheet(input_style())

        layout.addRow("First Name*:",      self.first_name)
        layout.addRow("Middle Name:",      self.middle_name)
        layout.addRow("Last Name*:",       self.last_name)
        layout.addRow("Gender:",           self.gender)
        layout.addRow("Occupation:",       self.occ_type)
        layout.addRow("Institution:",      self.institution)
        layout.addRow("Contact*:",         self.contact)
        layout.addRow("Email:",            self.email)
        layout.addRow("ID Type:",          self.id_type)
        layout.addRow("ID Number:",        self.id_number)
        layout.addRow("Address:",          self.address)
        layout.addRow("Emergency Name:",   self.emerg_name)
        layout.addRow("Emergency Number:", self.emerg_num)
        layout.addRow("Status:",           self.status)

        if renter:
            self.first_name.setText(renter.get('first_name',''))
            self.middle_name.setText(renter.get('middle_name','') or '')
            self.last_name.setText(renter.get('last_name',''))
            self.gender.setCurrentText(renter.get('gender','Male'))
            self.occ_type.setCurrentText(renter.get('occupation_type','Student'))
            self.institution.setText(renter.get('institution_employer','') or '')
            self.contact.setText(renter.get('contact_number','') or '')
            self.email.setText(renter.get('email','') or '')
            self.id_type.setCurrentText(renter.get('id_type','School ID') or 'School ID')
            self.id_number.setText(renter.get('id_number','') or '')
            self.address.setText(renter.get('address','') or '')
            self.emerg_name.setText(renter.get('emergency_contact_name','') or '')
            self.emerg_num.setText(renter.get('emergency_contact_number','') or '')
            self.status.setCurrentText(renter.get('renter_status','Active'))

        save_btn = make_btn("  Save", T("green"), "white", icon="fa5s.save", icon_color="white")
        save_btn.clicked.connect(self._validate)
        layout.addRow(save_btn)

    def _validate(self):
        if not self.first_name.text().strip() or not self.last_name.text().strip():
            QMessageBox.warning(self, "Missing", "First name and last name are required.")
            return
        self.accept()

    def get_data(self):
        return dict(
            first_name=self.first_name.text().strip(),
            middle_name=self.middle_name.text().strip() or None,
            last_name=self.last_name.text().strip(),
            gender=self.gender.currentText(),
            occupation_type=self.occ_type.currentText(),
            institution_employer=self.institution.text().strip() or None,
            contact_number=self.contact.text().strip(),
            email=self.email.text().strip() or None,
            id_type=self.id_type.currentText(),
            id_number=self.id_number.text().strip() or None,
            address=self.address.text().strip() or None,
            emergency_contact_name=self.emerg_name.text().strip() or None,
            emergency_contact_number=self.emerg_num.text().strip() or None,
            renter_status=self.status.currentText(),
        )


# ─────────────────────────────────────────────
#  RENTER REGISTRATION REQUEST DIALOG (public)
# ─────────────────────────────────────────────
class RentRequestDialog(QDialog):
    """Public-facing dialog for prospective renters to request a room."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Apply to Rent a Room")
        self.setFixedWidth(520)
        self.setStyleSheet(dialog_style())

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(16)

        hdr = QLabel("Room Rental Application")
        hdr.setStyleSheet(f"color: {T('accent')}; font-size: 20px; font-weight: bold;")
        main_layout.addWidget(hdr)

        info = QLabel(
            "Fill out this form to apply for a room. Your request will be reviewed by the admin.\n"
            "Once approved, you will receive login credentials to access your tenant dashboard."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px;")
        main_layout.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        form_widget = QWidget()
        form_widget.setStyleSheet(f"background: {T('surface')};")
        layout = QFormLayout(form_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        def inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        self.first_name  = inp("First Name*")
        self.last_name   = inp("Last Name*")
        self.gender      = QComboBox()
        self.gender.addItems(["Male", "Female", "Other"])
        self.gender.setStyleSheet(input_style())
        self.occ_type    = QComboBox()
        self.occ_type.addItems(["Student", "Professional", "Other"])
        self.occ_type.setStyleSheet(input_style())
        self.institution = inp("School / Company")
        self.contact     = inp("09XXXXXXXXX*")
        self.email       = inp("email@example.com*")
        self.address     = inp("Current Home Address")
        self.emerg_name  = inp("Emergency Contact Name")
        self.emerg_num   = inp("Emergency Contact Number")
        self.preferred_room = inp("Preferred room type / floor (optional)")
        self.message     = QTextEdit()
        self.message.setPlaceholderText("Additional message or questions for the admin (optional)...")
        self.message.setFixedHeight(70)
        self.message.setStyleSheet(input_style())

        layout.addRow("First Name*:",      self.first_name)
        layout.addRow("Last Name*:",       self.last_name)
        layout.addRow("Gender:",           self.gender)
        layout.addRow("Occupation:",       self.occ_type)
        layout.addRow("Institution:",      self.institution)
        layout.addRow("Contact*:",         self.contact)
        layout.addRow("Email*:",           self.email)
        layout.addRow("Address:",          self.address)
        layout.addRow("Emerg. Contact:",   self.emerg_name)
        layout.addRow("Emerg. Number:",    self.emerg_num)
        layout.addRow("Preference:",       self.preferred_room)
        layout.addRow("Message:",          self.message)

        scroll.setWidget(form_widget)
        main_layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        cancel_btn = make_btn("Cancel", T("surface2"), T("text"))
        submit_btn = make_btn("  Submit Application", T("accent"), "black", icon="fa5s.paper-plane", icon_color="black")
        cancel_btn.clicked.connect(self.reject)
        submit_btn.clicked.connect(self._validate)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(submit_btn)
        main_layout.addLayout(btn_row)

    def _validate(self):
        if not self.first_name.text().strip() or not self.last_name.text().strip():
            QMessageBox.warning(self, "Missing Fields", "First name and last name are required.")
            return
        if not self.contact.text().strip() and not self.email.text().strip():
            QMessageBox.warning(self, "Contact Required", "Please provide at least a contact number or email.")
            return
        self.accept()

    def get_data(self):
        return dict(
            first_name=self.first_name.text().strip(),
            last_name=self.last_name.text().strip(),
            gender=self.gender.currentText(),
            occupation_type=self.occ_type.currentText(),
            institution_employer=self.institution.text().strip() or None,
            contact_number=self.contact.text().strip() or None,
            email=self.email.text().strip() or None,
            address=self.address.text().strip() or None,
            emergency_contact_name=self.emerg_name.text().strip() or None,
            emergency_contact_number=self.emerg_num.text().strip() or None,
            preferred_room=self.preferred_room.text().strip() or None,
            message=self.message.toPlainText().strip() or None,
        )


# ─────────────────────────────────────────────
#  WELCOME PAGE
# ─────────────────────────────────────────────
class WelcomeRoomCard(QFrame):
    """Compact room card for the Welcome page — shows photo, beds available."""
    def __init__(self, room, amenities, on_apply):
        super().__init__()
        status = room.get('status', 'Available')
        cap  = int(room.get('capacity', 0) or 0)
        occ  = int(room.get('occupied', 0) or 0)
        avail = cap - occ

        self.setFixedSize(220, 280)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background: rgba(22,27,34,0.92);
                border-radius: 16px;
                border: 1px solid rgba(255,215,0,0.25);
            }
            QFrame:hover { border: 1px solid #FFD700; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(6)

        # Photo area
        photo_lbl = QLabel()
        photo_lbl.setFixedSize(220, 120)
        photo_lbl.setAlignment(Qt.AlignCenter)
        photo_path = room.get('photo_path') or ''
        if photo_path and os.path.exists(photo_path):
            pix = QPixmap(photo_path).scaled(220, 120, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            photo_lbl.setPixmap(pix)
            photo_lbl.setStyleSheet("border-radius: 16px 16px 0 0; background: #0D1117;")
        else:
            photo_lbl.setText("🏠")
            photo_lbl.setStyleSheet("font-size: 40px; background: rgba(255,215,0,0.08); border-radius: 16px 16px 0 0; color: #FFD700;")
        layout.addWidget(photo_lbl)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        il = QVBoxLayout(inner)
        il.setContentsMargins(12, 4, 12, 0)
        il.setSpacing(3)

        rn = QLabel(f"Room {room.get('room_number','?')}")
        rn.setStyleSheet("color: white; font-size: 15px; font-weight: bold; background: transparent; border: none;")
        il.addWidget(rn)

        fl = QLabel(f"📍 {room.get('floor_level','?')}")
        fl.setStyleSheet("color: #8B949E; font-size: 11px; background: transparent; border: none;")
        il.addWidget(fl)

        # Available beds — the key info
        beds_color = "#3FB950" if avail > 0 else "#FF6B6B"
        bed_txt = f"🛏  {avail} bed{'s' if avail != 1 else ''} available" if avail > 0 else "🔴  Full"
        beds_lbl = QLabel(bed_txt)
        beds_lbl.setStyleSheet(f"color: {beds_color}; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        il.addWidget(beds_lbl)

        rate_lbl = QLabel(f"₱{float(room.get('monthly_rate',0)):,.0f} / month")
        rate_lbl.setStyleSheet("color: #FFD700; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        il.addWidget(rate_lbl)

        # Amenity pills (first 2)
        if amenities:
            ap_row = QHBoxLayout()
            ap_row.setSpacing(4)
            for am in amenities[:2]:
                pill = QLabel(am.get('amenity_name','')[:12])
                pill.setStyleSheet("background: rgba(255,215,0,0.1); color: #FFD700; border: 1px solid rgba(255,215,0,0.3); padding: 2px 6px; border-radius: 8px; font-size: 9px;")
                ap_row.addWidget(pill)
            if len(amenities) > 2:
                more = QLabel(f"+{len(amenities)-2}")
                more.setStyleSheet("color: #8B949E; font-size: 9px; background: transparent; border: none;")
                ap_row.addWidget(more)
            ap_row.addStretch()
            il.addLayout(ap_row)

        layout.addWidget(inner)

        if avail > 0:
            ab = QPushButton("Apply for this Room")
            ab.setFixedHeight(30)
            ab.setStyleSheet("""
                QPushButton { background: #FFD700; color: black; border-radius: 8px;
                              font-size: 11px; font-weight: bold; margin: 0 12px; }
                QPushButton:hover { background: #E6C200; }
            """)
            ab.clicked.connect(lambda: on_apply(room))
            layout.addWidget(ab)


class WelcomePage(QWidget):
    # ── Contact / dorm info — edit these to match the real dorm ──
    CONTACT_PHONE = "09674897575"
    CONTACT_EMAIL = "dormnorm@gmail.com"

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self._room_db = database.RoomModule()

        self.bg_label = QLabel(self)
        current_dir = os.path.dirname(__file__)
        image_path = os.path.join(current_dir, "images", "dorm_bg.png")
        if os.path.exists(image_path):
            self.bg_label.setPixmap(QPixmap(image_path))
            self.bg_label.setScaledContents(True)

        self.overlay = QFrame(self)
        self.overlay.setStyleSheet("background-color: rgba(0,0,0,130);")

        # ── Outer scroll so everything is accessible at any window size ──
        outer_scroll = QScrollArea(self)
        outer_scroll.setWidgetResizable(True)
        outer_scroll.setStyleSheet("border: none; background: transparent;")
        outer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._outer_scroll = outer_scroll

        page_widget = QWidget()
        page_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── HERO SECTION ─────────────────────────────────
        hero = QWidget()
        hero.setStyleSheet("background: transparent;")
        hero.setMinimumHeight(480)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setAlignment(Qt.AlignCenter)
        hero_layout.setSpacing(10)
        hero_layout.setContentsMargins(40, 60, 40, 40)

        title_container = QWidget()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QHBoxLayout(title_container)
        title_layout.setAlignment(Qt.AlignCenter)
        dorm_label = QLabel("Dorm")
        dorm_label.setStyleSheet("color: white; font-size: 100px; font-family: 'Brush Script MT'; background: transparent; margin-right: -10px;")
        norm_label = QLabel("Norm")
        norm_label.setStyleSheet("color: white; font-size: 100px; font-family: 'Segoe UI'; font-weight: bold; background: transparent;")
        title_layout.addWidget(dorm_label)
        title_layout.addWidget(norm_label)

        tagline = QLabel("Making you feel at home away from home")
        tagline.setStyleSheet("color: #DADCE0; font-size: 20px; font-family: 'Segoe UI'; font-weight: 300; background: transparent;")

        # Contact strip
        contact_widget = QWidget()
        contact_widget.setStyleSheet("background: rgba(255,215,0,0.08); border-radius: 12px; border: 1px solid rgba(255,215,0,0.25);")
        contact_layout = QHBoxLayout(contact_widget)
        contact_layout.setContentsMargins(20, 8, 20, 8)
        contact_layout.setSpacing(30)
        ph_lbl = QLabel(f"📞  CONTACT US: {self.CONTACT_PHONE}")
        ph_lbl.setStyleSheet("color: #FFD700; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        em_lbl = QLabel(f"✉  EMAIL: {self.CONTACT_EMAIL}")
        em_lbl.setStyleSheet("color: #FFD700; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        contact_layout.addStretch()
        contact_layout.addWidget(ph_lbl)
        contact_layout.addWidget(em_lbl)
        contact_layout.addStretch()

        # Amenities toggle
        self.toggle_btn = QPushButton("◈ VIEW AMENITIES & INCLUSIONS ▼")
        self.toggle_btn.setFixedWidth(300)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #FFD700; border: 1px solid #FFD700;
                          border-radius: 15px; padding: 8px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: rgba(255,215,0,0.1); }
        """)
        self.toggle_btn.clicked.connect(self.toggle_amenities)

        self.feature_container = QWidget()
        self.feature_container.setStyleSheet("background: transparent;")
        self.feature_container.setVisible(False)
        feature_layout = QGridLayout(self.feature_container)
        feature_layout.setSpacing(10)
        all_features = [
            ("📶", "Fiber Wi-Fi"), ("💡", "Utilities Included"), ("🔒", "24/7 Security"),
            ("🍳", "Shared Kitchen"), ("🛁", "Private Bath"), ("📺", "Smart TV"),
            ("🍽️", "Dining Area"), ("🛋️", "Living Room"),
        ]
        row, col = 0, 0
        for icon, feat in all_features:
            pill = QLabel(f"{icon}  {feat}")
            pill.setStyleSheet("background-color: rgba(255,215,0,0.12); color: #FFD700; border: 1px solid rgba(255,215,0,0.4); padding: 8px 15px; border-radius: 18px; font-size: 12px; font-weight: bold;")
            feature_layout.addWidget(pill, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        btn_row.setAlignment(Qt.AlignCenter)

        login_btn = QPushButton("GET STARTED — LOGIN")
        login_btn.setFixedSize(280, 60)
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setStyleSheet("""
            QPushButton { background-color: #FFD700; color: black; border-radius: 30px; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background-color: #E6C200; border: 2px solid white; }
        """)
        login_btn.clicked.connect(lambda: self.controller.parent().fade_to_page(1))

        apply_btn = QPushButton("APPLY TO RENT")
        apply_btn.setFixedSize(200, 60)
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #FFD700; border: 2px solid #FFD700; border-radius: 30px; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background-color: rgba(255,215,0,0.1); }
        """)
        apply_btn.clicked.connect(lambda: self._open_application())

        btn_row.addWidget(login_btn)
        btn_row.addWidget(apply_btn)

        hero_layout.addWidget(title_container, alignment=Qt.AlignCenter)
        hero_layout.addWidget(tagline, alignment=Qt.AlignCenter)
        hero_layout.addSpacing(12)
        hero_layout.addWidget(contact_widget, alignment=Qt.AlignCenter)
        hero_layout.addSpacing(8)
        hero_layout.addWidget(self.toggle_btn, alignment=Qt.AlignCenter)
        hero_layout.addWidget(self.feature_container, alignment=Qt.AlignCenter)
        hero_layout.addSpacing(20)
        hero_layout.addLayout(btn_row)

        layout.addWidget(hero)

        # ── BROWSE ROOMS SECTION ──────────────────────────
        browse_section = QWidget()
        browse_section.setStyleSheet("background: rgba(13,17,23,0.85);")
        browse_layout = QVBoxLayout(browse_section)
        browse_layout.setContentsMargins(50, 40, 50, 50)
        browse_layout.setSpacing(20)

        browse_hdr = QHBoxLayout()
        browse_title = QLabel("🏠  Browse Available Rooms")
        browse_title.setStyleSheet("color: white; font-size: 24px; font-weight: bold; background: transparent; border: none;")
        self.room_avail_badge = QLabel("Loading...")
        self.room_avail_badge.setStyleSheet("color: #3FB950; font-size: 13px; font-weight: bold; background: rgba(63,185,80,0.12); border: 1px solid #3FB950; padding: 4px 12px; border-radius: 12px;")
        browse_hdr.addWidget(browse_title)
        browse_hdr.addStretch()
        browse_hdr.addWidget(self.room_avail_badge)
        browse_layout.addLayout(browse_hdr)

        sub_lbl = QLabel("See bed availability and amenities before applying. Click a room card's Apply button to get started.")
        sub_lbl.setStyleSheet("color: #8B949E; font-size: 13px; background: transparent; border: none;")
        browse_layout.addWidget(sub_lbl)

        self.room_cards_scroll = QScrollArea()
        self.room_cards_scroll.setWidgetResizable(True)
        self.room_cards_scroll.setFixedHeight(310)
        self.room_cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.room_cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.room_cards_scroll.setStyleSheet("border: none; background: transparent;")
        self.room_cards_inner = QWidget()
        self.room_cards_inner.setStyleSheet("background: transparent;")
        self.room_cards_row = QHBoxLayout(self.room_cards_inner)
        self.room_cards_row.setContentsMargins(0, 8, 0, 8)
        self.room_cards_row.setSpacing(16)
        self.room_cards_row.addStretch()
        self.room_cards_scroll.setWidget(self.room_cards_inner)
        browse_layout.addWidget(self.room_cards_scroll)

        layout.addWidget(browse_section)

        outer_scroll.setWidget(page_widget)

        # Load rooms after widgets are set up
        QTimer.singleShot(200, self._load_rooms)

    def _load_rooms(self):
        try:
            rooms = self._room_db.get_all_rooms()
        except Exception:
            rooms = []

        # Clear
        while self.room_cards_row.count() > 1:
            item = self.room_cards_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        avail_total = 0
        for room in rooms:
            cap = int(room.get('capacity', 0) or 0)
            occ = int(room.get('occupied', 0) or 0)
            avail_total += max(0, cap - occ)
            try:
                ams = self._room_db.get_amenities(room.get('room_id'))
            except Exception:
                ams = []
            card = WelcomeRoomCard(room, ams, on_apply=self._open_application_for_room)
            self.room_cards_row.insertWidget(self.room_cards_row.count() - 1, card)

        self.room_avail_badge.setText(f"{avail_total} bed{'s' if avail_total != 1 else ''} available")

        if not rooms:
            lbl = QLabel("No rooms listed yet. Contact the admin.")
            lbl.setStyleSheet("color: #8B949E; font-size: 14px; padding: 20px; background: transparent; border: none;")
            self.room_cards_row.insertWidget(0, lbl)

    def _open_application_for_room(self, room=None):
        self._open_application(preferred=f"Room {room.get('room_number','')}" if room else "")

    def _open_application(self, preferred=""):
        dlg = RentRequestDialog(self)
        if preferred:
            try:
                dlg.preferred_room.setText(preferred)
            except Exception:
                pass
        if dlg.exec():
            data = dlg.get_data()
            app_db = database.ApplicationModule()
            ok = app_db.submit_application(
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                gender=data.get('gender', 'Other'),
                occupation_type=data.get('occupation_type', 'Student'),
                institution=data.get('institution_employer') or '',
                contact_number=data.get('contact_number') or '',
                email=data.get('email') or '',
                address=data.get('address') or '',
                emergency_name=data.get('emergency_contact_name') or '',
                emergency_number=data.get('emergency_contact_number') or '',
                preferred_room=data.get('preferred_room') or '',
                message=data.get('message') or '',
            )
            if ok:
                QMessageBox.information(
                    self, "✓ Application Submitted!",
                    f"Thank you, {data['first_name']}! Your rental application has been submitted.\n\n"
                    "The admin will review your application shortly.\n"
                    "Once approved, you will receive your login credentials\n"
                    "to access your tenant dashboard."
                )
            else:
                QMessageBox.warning(
                    self, "Could Not Submit",
                    "There was a problem submitting your application.\n"
                    "Please make sure the system database is running and try again."
                )

    def toggle_amenities(self):
        is_visible = self.feature_container.isVisible()
        self.feature_container.setVisible(not is_visible)
        self.toggle_btn.setText("CLOSE AMENITIES ▲" if not is_visible else "◈ VIEW AMENITIES & INCLUSIONS ▼")

    def resizeEvent(self, event):
        self.bg_label.resize(self.size())
        self.overlay.resize(self.size())
        self._outer_scroll.resize(self.size())
        super().resizeEvent(event)


# ─────────────────────────────────────────────
#  LOGIN PAGE
# ─────────────────────────────────────────────
class LoginPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        self.bg_label = QLabel(self)
        current_dir = os.path.dirname(__file__)
        image_path = os.path.join(current_dir, "images", "dorm_bg.png")
        if os.path.exists(image_path):
            self.bg_label.setPixmap(QPixmap(image_path))
            self.bg_label.setScaledContents(True)

        self.overlay = QFrame(self)
        self.overlay.setStyleSheet("background-color: rgba(0,0,0,165);")

        main_layout = QVBoxLayout(self)
        header = QHBoxLayout()
        back_btn = QPushButton("← BACK")
        back_btn.setStyleSheet("color: #FFD700; background: transparent; font-size: 16px; font-weight: bold; border: none;")
        back_btn.clicked.connect(lambda: self.controller.setCurrentIndex(0))
        header.addWidget(back_btn, alignment=Qt.AlignLeft)
        header.setContentsMargins(20, 20, 20, 0)
        main_layout.addLayout(header)
        main_layout.addStretch()

        self.card = QFrame()
        self.card.setFixedSize(450, 580)
        self.card.setStyleSheet("background-color: #161B22; border-radius: 25px; border: 1px solid #30363D;")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 30, 40, 30)
        card_layout.setSpacing(15)

        brand_container = QWidget()
        brand_layout = QHBoxLayout(brand_container)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        dorm_mini = QLabel("Dorm")
        dorm_mini.setStyleSheet("color: #FFD700; font-family: 'Brush Script MT'; font-size: 28px; border: none;")
        norm_mini = QLabel("Norm")
        norm_mini.setStyleSheet("color: white; font-family: 'Segoe UI'; font-weight: bold; font-size: 28px; border: none;")
        brand_layout.addWidget(dorm_mini)
        brand_layout.addWidget(norm_mini)
        card_layout.addWidget(brand_container, alignment=Qt.AlignCenter)

        title = QLabel("Welcome Back!")
        title.setStyleSheet("color: white; font-size: 30px; font-weight: bold; border: none;")
        card_layout.addWidget(title, alignment=Qt.AlignCenter)

        role_hint = QLabel("Login as Admin, Staff, or Tenant")
        role_hint.setStyleSheet("color: #8B949E; font-size: 12px; border: none;")
        card_layout.addWidget(role_hint, alignment=Qt.AlignCenter)

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #FF6B6B; font-size: 12px; border: none; font-weight: bold;")
        self.info_label.setWordWrap(True)
        self.info_label.setVisible(False)
        card_layout.addWidget(self.info_label)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        self.user_input.setFixedSize(370, 50)
        self.user_input.setStyleSheet(
            "QLineEdit { background-color: #0D1117; color: white; border: 1px solid #30363D; border-radius: 10px; padding-left: 15px; }"
            "QLineEdit:focus { border: 1px solid #FFD700; }"
        )
        card_layout.addWidget(self.user_input)

        pass_container = QWidget()
        pass_container.setFixedSize(370, 50)
        pass_container.setStyleSheet("background-color: #0D1117; border: 1px solid #30363D; border-radius: 10px;")
        pass_layout = QHBoxLayout(pass_container)
        pass_layout.setContentsMargins(0, 0, 0, 0)
        pass_layout.setSpacing(0)
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setFixedSize(320, 50)
        self.pass_input.setStyleSheet(
            "QLineEdit { background: transparent; color: white; border: none; padding-left: 15px; }"
        )
        self.pass_input.returnPressed.connect(self.handle_login)
        self.eye_btn = QPushButton()
        self.eye_btn.setIcon(qta.icon("fa5s.eye", color="#8B949E"))
        self.eye_btn.setIconSize(QSize(18, 18))
        self.eye_btn.setFixedSize(50, 50)
        self.eye_btn.setCheckable(True)
        self.eye_btn.setCursor(Qt.PointingHandCursor)
        self.eye_btn.setStyleSheet("QPushButton { background: transparent; border: none; }")
        self.eye_btn.clicked.connect(self.toggle_password_visibility)
        pass_layout.addWidget(self.pass_input)
        pass_layout.addWidget(self.eye_btn)
        card_layout.addWidget(pass_container)

        login_btn = QPushButton("LOGIN")
        login_btn.setFixedSize(370, 55)
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setStyleSheet("background-color: #FFD700; color: black; border-radius: 12px; font-size: 16px; font-weight: bold; margin-top: 10px;")
        login_btn.clicked.connect(self.handle_login)
        card_layout.addWidget(login_btn)

        footer_note = QLabel("Don't have an account? Contact Admin or Apply to Rent.")
        footer_note.setStyleSheet("color: #8B949E; font-size: 12px; border: none; margin-top: 10px;")
        card_layout.addWidget(footer_note, alignment=Qt.AlignCenter)

        main_layout.addWidget(self.card, alignment=Qt.AlignCenter)
        main_layout.addStretch()

    def toggle_password_visibility(self):
        if self.eye_btn.isChecked():
            self.pass_input.setEchoMode(QLineEdit.Normal)
            self.eye_btn.setIcon(qta.icon("fa5s.eye-slash", color="#8B949E"))
        else:
            self.pass_input.setEchoMode(QLineEdit.Password)
            self.eye_btn.setIcon(qta.icon("fa5s.eye", color="#8B949E"))

    def handle_login(self):
        user = self.user_input.text().strip()
        pw   = self.pass_input.text().strip()
        if not user or not pw:
            self.info_label.setText("Please enter both username and password.")
            self.info_label.setVisible(True)
            return

        # Try admin/staff login first
        db = database.AdminModule()
        user_data = db.validate_login(user, pw)
        if user_data:
            self.info_label.setVisible(False)
            db.log_login(user_data['admin_id'], user_data['full_name'], user_data.get('role', 'Admin'))
            dashboard = self.controller.parent().dashboard
            dashboard.set_current_user(user_data)
            self.controller.parent().fade_to_page(2)
            return

        # Try renter login
        renter_data = self._try_renter_login(user, pw)
        if renter_data:
            self.info_label.setVisible(False)
            dashboard = self.controller.parent().dashboard
            dashboard.set_current_user(renter_data)
            self.controller.parent().fade_to_page(2)
            return

        self.info_label.setText("Invalid username or password.")
        self.info_label.setVisible(True)

    def _try_renter_login(self, username, password):
        try:
            db = database.RenterModule()
            row = db.validate_renter_login(username, password)
            if row:
                return {
                    'admin_id':  None,
                    'renter_id': row['renter_id'],
                    'full_name': f"{row['first_name']} {row['last_name']}",
                    'role':      'Renter',
                    'username':  username,
                }
        except Exception as e:
            print(f"[Renter login] {e}")
        return None

    def resizeEvent(self, event):
        self.bg_label.resize(self.size())
        self.overlay.resize(self.size())
        super().resizeEvent(event)


# ─────────────────────────────────────────────
#  MAIN DASHBOARD PAGE
# ─────────────────────────────────────────────
class DashboardPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.current_user = None
        self._apply_bg()

        self.admin_db       = database.AdminModule()
        self.renter_db      = database.RenterModule()
        self.room_db        = database.RoomModule()
        self.assignment_db  = database.AssignmentModule()
        self.payment_db     = database.PaymentModule()
        self.maintenance_db = database.MaintenanceModule()
        self.utility_db     = database.UtilityModule()
        self.visitor_db     = database.VisitorModule()
        self.app_db         = database.ApplicationModule()
        self.app_db.setup_table()   # ensure table exists on startup

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── SIDEBAR ──────────────────────────────
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(260)
        self._apply_sidebar()
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 40, 20, 20)

        brand_row = QHBoxLayout()
        logo_label = QLabel("DormNorm")
        logo_label.setStyleSheet(f"color: {T('accent')}; font-family: 'Brush Script MT'; font-size: 32px; margin-bottom: 10px;")
        self.theme_toggle = ThemeToggleBtn(self._on_theme_toggle)
        brand_row.addWidget(logo_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        brand_row.addStretch()
        brand_row.addWidget(self.theme_toggle, alignment=Qt.AlignRight | Qt.AlignVCenter)
        sidebar_layout.addLayout(brand_row)
        sidebar_layout.addSpacing(20)

        self.pages_content = QStackedWidget()

        # MENU: index-to-name mapping
        # 0=Dashboard, 1=Renters, 2=Staff, 3=Rooms(All), 4=Vacant, 5=Occupied,
        # 6=Bills&Pay, 7=Reports, 8=Maintenance, 9=Visitors, 10=Activity Logs
        self._all_menu_items = [
            ("  Dashboard",      0,  "fa5s.home",           "#58A6FF"),
            ("  Applications",   1,  "fa5s.file-alt",       "#FFD700"),
            ("  Renters",        2,  "fa5s.users",          "#3FB950"),
            ("  Staff",          3,  "fa5s.user-tie",       "#FFD700"),
            ("  All Rooms",      4,  "fa5s.bed",            "#F0883E"),
            ("  Vacant Rooms",   5,  "fa5s.door-open",      "#3FB950"),
            ("  Occupied Rooms", 6,  "fa5s.door-closed",    "#FF6B6B"),
            ("  Bills & Pay",    7,  "fa5s.credit-card",    "#D2A8FF"),
            ("  Reports",        8,  "fa5s.chart-bar",      "#79C0FF"),
            ("  Maintenance",    9,  "fa5s.tools",          "#FF6B6B"),
            ("  Visitors",       10, "fa5s.eye",            "#A8D8A8"),
            ("  Activity Logs",  11, "fa5s.list-alt",       "#8B949E"),
            ("  My Profile",     12, "fa5s.user-circle",    "#D2A8FF"),
        ]

        self.sidebar_buttons = []
        for text, index, icon_name, icon_color in self._all_menu_items:
            btn = QPushButton(text)
            btn.setIcon(qta.icon(icon_name, color=icon_color))
            btn.setIconSize(QSize(18, 18))
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("page_index", index)   # store index for reliable lookup
            btn.clicked.connect(lambda _, i=index: self.switch_page(i))
            if index == 0:
                btn.setChecked(True)
            btn.setStyleSheet(self._sidebar_btn_style())
            sidebar_layout.addWidget(btn)
            self.sidebar_buttons.append(btn)

        sidebar_layout.addStretch()

        self.user_info_widget = QFrame()
        self.user_info_widget.setStyleSheet(f"background: {T('surface2')}; border-radius: 12px; padding: 8px;")
        ui_layout = QHBoxLayout(self.user_info_widget)
        ui_layout.setContentsMargins(10, 8, 10, 8)
        self.sidebar_avatar = AvatarWidget("?", 36)
        self.sidebar_user_lbl = QLabel("Not logged in")
        self.sidebar_user_lbl.setStyleSheet(f"color: {T('text')}; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        self.sidebar_role_lbl = QLabel("")
        self.sidebar_role_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 11px; background: transparent; border: none;")
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.addWidget(self.sidebar_user_lbl)
        info_col.addWidget(self.sidebar_role_lbl)
        ui_layout.addWidget(self.sidebar_avatar)
        ui_layout.addLayout(info_col)
        ui_layout.addStretch()
        sidebar_layout.addWidget(self.user_info_widget)
        sidebar_layout.addSpacing(8)

        logout_btn = QPushButton("  Logout")
        logout_btn.setIcon(qta.icon("fa5s.sign-out-alt", color=T("red")))
        logout_btn.setIconSize(QSize(16, 16))
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setStyleSheet(f"color: {T('red')}; background: transparent; font-weight: bold; padding: 10px; border: 1px solid {T('red')}; border-radius: 10px;")
        logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(logout_btn)

        # ── BUILD PAGES ───────────────────────────
        self.home_page        = self._build_home_page()
        self.applications_page= self._build_applications_page()
        self.renters_page     = self._build_renters_page()
        self.staff_page       = self._build_staff_page()
        self.rooms_page       = self._build_rooms_page()
        self.vacant_page      = self._build_vacant_rooms_page()
        self.occupied_page    = self._build_occupied_rooms_page()
        self.payments_page    = self._build_payments_page()
        self.reports_page     = self._build_reports_page()
        self.maintenance_page = self._build_maintenance_page()
        self.visitors_page    = self._build_visitors_page()
        self.logs_page        = self._build_logs_page()
        self.profile_page     = self._build_profile_page()

        for p in [self.home_page, self.applications_page, self.renters_page,
                  self.staff_page, self.rooms_page, self.vacant_page,
                  self.occupied_page, self.payments_page, self.reports_page,
                  self.maintenance_page, self.visitors_page, self.logs_page,
                  self.profile_page]:
            self.pages_content.addWidget(p)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.pages_content)

    # ── STYLE HELPERS ──────────────────────────
    def _apply_bg(self):
        self.setStyleSheet(f"background-color: {T('bg')};")

    def _apply_sidebar(self):
        self.sidebar.setStyleSheet(f"background-color: {T('surface')}; border-right: 1px solid {T('border')};")

    def _on_theme_toggle(self):
        self._rebuild_styles()

    def _rebuild_styles(self):
        self._apply_bg()
        self._apply_sidebar()
        for btn in self.sidebar_buttons:
            btn.setStyleSheet(self._sidebar_btn_style())
        self.refresh_home_stats()

    def _sidebar_btn_style(self):
        t = Theme.get()
        return f"""
            QPushButton {{ text-align: left; padding: 10px 15px; font-size: 13px; font-weight: bold;
                border-radius: 8px; color: {t['text_muted']}; border: none; background: transparent; }}
            QPushButton:hover {{ background-color: {t['surface2']}; color: {t['text']}; }}
            QPushButton:checked {{ background-color: {t['accent_dim']}; color: {t['accent']}; border-left: 3px solid {t['accent']}; }}
        """

    def _make_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.verticalHeader().setVisible(False)
        table.setStyleSheet(table_style())
        table.setAlternatingRowColors(True)
        return table

    def _set_table_row(self, table, row, values):
        table.insertRow(row)
        for col, val in enumerate(values):
            item = QTableWidgetItem(str(val) if val is not None else "—")
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            table.setItem(row, col, item)

    def _card_frame(self):
        f = QFrame()
        f.setStyleSheet(f"background-color: {T('surface')}; border-radius: 16px; border: 1px solid {T('border')};")
        return f

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {T('text')}; font-size: 16px; font-weight: bold;")
        return lbl

    # ── USER MANAGEMENT ───────────────────────
    def set_current_user(self, user_data):
        self.current_user = user_data
        role = user_data.get('role', 'Staff')
        name = user_data.get('full_name', 'User')

        self.sidebar_avatar.set_avatar(name)
        self.sidebar_user_lbl.setText(name[:22])
        self.sidebar_role_lbl.setText(role)

        self.welcome_label.setText(
            f'Hello, <span style="color:{T("accent")};">{name}</span>! '
            f'<span style="color:{T("text_muted")}; font-size:14px;">({role})</span>'
        )
        self._apply_role_permissions(role)
        self.refresh_home_stats()

    def _apply_role_permissions(self, role):
        is_admin  = (role == 'Admin')
        is_staff  = (role in ('Admin', 'Staff', 'Maintenance', 'Security'))
        is_renter = (role == 'Renter')

        # 0=Dashboard, 1=Applications, 2=Renters, 3=Staff, 4=AllRooms,
        # 5=Vacant, 6=Occupied, 7=Bills, 8=Reports, 9=Maintenance,
        # 10=Visitors, 11=Logs
        visibility = {
            0:  True,
            1:  is_admin,       # Applications — admin only
            2:  is_staff,
            3:  is_admin,
            4:  is_staff,
            5:  True,           # Vacant — everyone can see
            6:  is_staff,
            7:  is_staff,
            8:  is_staff,
            9:  True,           # Maintenance — renters can submit
            10: is_staff,
            11: is_admin,
            12: True,           # My Profile — everyone
        }
        for btn in self.sidebar_buttons:
            idx = btn.property("page_index")
            btn.setVisible(visibility.get(idx, True))

        if hasattr(self, 'staff_add_btn'):
            self.staff_add_btn.setVisible(is_admin)
            self.staff_edit_btn.setVisible(is_admin)
            self.staff_delete_btn.setVisible(is_admin)
        if hasattr(self, 'renter_delete_btn'):
            self.renter_delete_btn.setVisible(is_admin)
        if hasattr(self, 'room_add_btn'):
            self.room_add_btn.setVisible(is_admin)
            self.room_delete_btn.setVisible(is_admin)
        if hasattr(self, 'payment_delete_btn'):
            self.payment_delete_btn.setVisible(is_admin)
        if hasattr(self, 'maint_delete_btn'):
            self.maint_delete_btn.setVisible(is_admin)
        if hasattr(self, 'visitor_delete_btn'):
            self.visitor_delete_btn.setVisible(is_admin)
        if hasattr(self, 'app_reject_btn'):
            self.app_reject_btn.setVisible(is_admin)
            self.app_approve_btn.setVisible(is_admin)

        # Update applications badge in sidebar
        self._refresh_app_badge()

        if is_renter:
            self._customize_renter_dashboard()

    def _refresh_app_badge(self):
        """Show a red badge on the Applications sidebar button if there are pending applications."""
        try:
            count = self.app_db.get_pending_count()
            for btn in self.sidebar_buttons:
                if btn.property("page_index") == 1:   # 1 = Applications
                    if count > 0:
                        btn.setText(f"  Applications  [{count}]")
                        btn.setStyleSheet(self._sidebar_btn_style().replace(
                            f"color: {T('text_muted')}",
                            f"color: {T('accent')}"
                        ))
                    else:
                        btn.setText("  Applications")
                        btn.setStyleSheet(self._sidebar_btn_style())
                    break
        except Exception:
            pass

    def _customize_renter_dashboard(self):
        """Replace dashboard stat cards with renter-specific info."""
        renter_id = self.current_user.get('renter_id')
        if not renter_id:
            return
        try:
            # Room assignment
            assignment = self.renter_db.get_renter_assignment(renter_id)
            if assignment:
                self.stat_total_rooms.value_label.setText(f"Room {assignment.get('room_number','?')}")
                self.stat_total_rooms.setToolTip(
                    f"Floor: {assignment.get('floor_level','?')}\n"
                    f"Rate: ₱{assignment.get('monthly_rate',0):,.0f}/mo"
                )
            else:
                self.stat_total_rooms.value_label.setText("No Room")

            # Payments
            payments = self.renter_db.get_renter_payments(renter_id)
            pending = sum(1 for p in payments if p.get('status') == 'Pending')
            paid    = sum(float(p['amount']) for p in payments if p.get('status') == 'Paid')
            self.stat_payments.value_label.setText(str(pending))
            self.stat_vacant.value_label.setText(f"₱{paid:,.0f}")

            # Maintenance
            maint = self.renter_db.get_renter_maintenance(renter_id)
            pending_m = sum(1 for m in maint if m.get('status') == 'Pending')
            self.stat_maint.value_label.setText(str(pending_m))

        except Exception as e:
            print(f"[_customize_renter_dashboard] {e}")

    def switch_page(self, index):
        self.pages_content.setCurrentIndex(index)
        refresh_map = {
            0:  self.refresh_home_stats,
            1:  self.load_applications,
            2:  self.load_renters,
            3:  self.load_staff,
            4:  self.load_rooms,
            5:  self.load_vacant_rooms,
            6:  self.load_occupied_rooms,
            7:  self.load_payments,
            8:  self.load_reports,
            9:  self.load_maintenance,
            10: self.load_visitors,
            11: self.load_logs,
            12: self.load_profile,
        }
        if index in refresh_map:
            refresh_map[index]()

    def handle_logout(self):
        if self.current_user and self.current_user.get('admin_id'):
            self.admin_db.add_log(
                self.current_user['admin_id'], 'LOGOUT',
                f"{self.current_user['full_name']} logged out."
            )
        self.current_user = None
        self.controller.parent().fade_to_page(1)

    # ══════════════════════════════════════════
    #  HOME / DASHBOARD PAGE
    # ══════════════════════════════════════════
    def _build_home_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # Header
        header = QHBoxLayout()
        self.welcome_label = QLabel(f'Hello, <span style="color:{T("accent")};">Admin</span>!')
        self.welcome_label.setStyleSheet(f"color: {T('text')}; font-size: 28px; font-weight: bold;")
        self.welcome_label.setTextFormat(Qt.RichText)
        date_lbl = QLabel(QDate.currentDate().toString("dddd, MMMM d, yyyy"))
        date_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 14px;")
        header.addWidget(self.welcome_label)
        header.addStretch()
        header.addWidget(date_lbl)
        layout.addLayout(header)

        # ── ROW 1: STAT CARDS ─────────────────
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(14)

        self.stat_total_rooms = StatCard(
            "Total Rooms", "—", T("blue"), "fa5s.building",
            on_click=lambda: self.switch_page(4)
        )
        self.stat_vacant = StatCard(
            "Vacant Rooms", "—", T("green"), "fa5s.door-open",
            subtitle="Available now",
            on_click=lambda: self.switch_page(5)
        )
        self.stat_occupied = StatCard(
            "Occupied", "—", T("red"), "fa5s.door-closed",
            subtitle="Currently rented",
            on_click=lambda: self.switch_page(6)
        )
        self.stat_boarders = StatCard(
            "Active Renters", "—", T("accent"), "fa5s.users",
            on_click=lambda: self.switch_page(2)
        )
        self.stat_maint = StatCard(
            "Pending Maint.", "—", T("orange"), "fa5s.tools",
            on_click=lambda: self.switch_page(9)
        )
        self.stat_payments = StatCard(
            "Pending Payments", "—", T("purple"), "fa5s.exclamation-circle",
            on_click=lambda: self.switch_page(7)
        )

        for card in [self.stat_total_rooms, self.stat_vacant, self.stat_occupied,
                     self.stat_boarders, self.stat_maint, self.stat_payments]:
            stats_layout.addWidget(card)
        layout.addLayout(stats_layout)

        # ── ROW 2: ROOM OVERVIEW + PAYMENT DONUT ─
        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        # Room availability breakdown (bar: available vs occupied vs maintenance)
        room_bar_card = self._card_frame()
        room_bar_card.setMinimumHeight(260)
        rbc_layout = QVBoxLayout(room_bar_card)
        rbc_layout.setContentsMargins(16, 16, 16, 16)
        lbl = QLabel("Room Status Breakdown")
        lbl.setStyleSheet(f"color: {T('text')}; font-size: 14px; font-weight: bold; border: none; background: transparent;")
        rbc_layout.addWidget(lbl)
        self.room_status_chart = BarChartWidget("")
        rbc_layout.addWidget(self.room_status_chart)
        charts_row.addWidget(room_bar_card, 2)

        pay_card = self._card_frame()
        pay_card.setMinimumHeight(260)
        pay_layout = QVBoxLayout(pay_card)
        pay_layout.setContentsMargins(16, 16, 16, 16)
        self.payment_donut = DonutChartWidget("Payments")
        pay_layout.addWidget(self.payment_donut)
        charts_row.addWidget(pay_card, 1)

        renter_card = self._card_frame()
        renter_card.setMinimumHeight(260)
        rc_layout = QVBoxLayout(renter_card)
        rc_layout.setContentsMargins(16, 16, 16, 16)
        self.renter_chart = BarChartWidget("Renters by Type")
        rc_layout.addWidget(self.renter_chart)
        charts_row.addWidget(renter_card, 2)

        layout.addLayout(charts_row)

        # ── ROW 3: ROOM CARDS PREVIEW ─────────
        room_preview_hdr = QHBoxLayout()
        room_preview_hdr.addWidget(self._section_label("Rooms at a Glance"))
        see_all = QPushButton("See All Rooms →")
        see_all.setStyleSheet(f"color: {T('blue')}; background: transparent; border: none; font-size: 13px; font-weight: bold;")
        see_all.setCursor(Qt.PointingHandCursor)
        see_all.clicked.connect(lambda: self.switch_page(4))
        room_preview_hdr.addStretch()
        room_preview_hdr.addWidget(see_all)
        layout.addLayout(room_preview_hdr)

        self.room_cards_scroll = QScrollArea()
        self.room_cards_scroll.setFixedHeight(180)
        self.room_cards_scroll.setWidgetResizable(True)
        self.room_cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.room_cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.room_cards_scroll.setStyleSheet("border: none; background: transparent;")
        self.room_cards_inner = QWidget()
        self.room_cards_inner.setStyleSheet("background: transparent;")
        self.room_cards_row = QHBoxLayout(self.room_cards_inner)
        self.room_cards_row.setContentsMargins(0, 4, 0, 4)
        self.room_cards_row.setSpacing(12)
        self.room_cards_row.addStretch()
        self.room_cards_scroll.setWidget(self.room_cards_inner)
        layout.addWidget(self.room_cards_scroll)

        # ── ROW 4: MAINTENANCE PANEL ──────────
        maint_hdr = QHBoxLayout()
        maint_hdr.addWidget(self._section_label("🔧 Pending Maintenance"))
        see_maint = QPushButton("See All →")
        see_maint.setStyleSheet(f"color: {T('blue')}; background: transparent; border: none; font-size: 13px; font-weight: bold;")
        see_maint.setCursor(Qt.PointingHandCursor)
        see_maint.clicked.connect(lambda: self.switch_page(9))
        maint_hdr.addStretch()
        maint_hdr.addWidget(see_maint)
        layout.addLayout(maint_hdr)

        self.maint_cards_widget = QWidget()
        self.maint_cards_widget.setStyleSheet("background: transparent;")
        self.maint_cards_layout = QVBoxLayout(self.maint_cards_widget)
        self.maint_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.maint_cards_layout.setSpacing(8)
        layout.addWidget(self.maint_cards_widget)

        # ── ROW 5: ACTIVE RENTERS ─────────────
        faces_hdr = QHBoxLayout()
        faces_hdr.addWidget(self._section_label("Active Renters"))
        see_renters = QPushButton("See All →")
        see_renters.setStyleSheet(f"color: {T('blue')}; background: transparent; border: none; font-size: 13px; font-weight: bold;")
        see_renters.setCursor(Qt.PointingHandCursor)
        see_renters.clicked.connect(lambda: self.switch_page(2))
        faces_hdr.addStretch()
        faces_hdr.addWidget(see_renters)
        layout.addLayout(faces_hdr)

        self.renter_faces_area = QScrollArea()
        self.renter_faces_area.setFixedHeight(88)
        self.renter_faces_area.setWidgetResizable(True)
        self.renter_faces_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.renter_faces_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.renter_faces_area.setStyleSheet("border: none; background: transparent;")
        self.renter_faces_inner = QWidget()
        self.renter_faces_inner.setStyleSheet("background: transparent;")
        self.renter_faces_row = QHBoxLayout(self.renter_faces_inner)
        self.renter_faces_row.setContentsMargins(0, 4, 0, 4)
        self.renter_faces_row.setSpacing(10)
        self.renter_faces_row.addStretch()
        self.renter_faces_area.setWidget(self.renter_faces_inner)
        layout.addWidget(self.renter_faces_area)

        # ── ROW 6: RECENT ACTIVITY ────────────
        layout.addWidget(self._section_label("Recent Activity"))
        self.recent_logs_table = self._make_table(["Admin", "Action", "Details", "Timestamp"])
        self.recent_logs_table.setMaximumHeight(200)
        layout.addWidget(self.recent_logs_table)
        layout.addStretch()

        scroll.setWidget(page)
        return scroll

    def refresh_home_stats(self):
        t = Theme.get()

        # ── Room stats ───────────────────────
        total_rooms = 0
        vacant_count = 0
        occupied_count = 0
        maint_count_rooms = 0
        try:
            rooms = self.room_db.get_all_rooms()
            total_rooms = len(rooms)
            vacant_count   = sum(1 for r in rooms if r.get('status') == 'Available')
            occupied_count = sum(1 for r in rooms if r.get('status') == 'Full')
            maint_count_rooms = sum(1 for r in rooms if r.get('status') == 'Under Maintenance')

            self.stat_total_rooms.set_value(total_rooms)
            self.stat_vacant.set_value(vacant_count)
            self.stat_occupied.set_value(occupied_count)

            # Room status bar chart — Available vs Occupied vs Maintenance
            bar_data = []
            if vacant_count:    bar_data.append(("Available", vacant_count, t['green']))
            if occupied_count:  bar_data.append(("Full", occupied_count, t['red']))
            if maint_count_rooms: bar_data.append(("Maint.", maint_count_rooms, t['orange']))
            reserved = sum(1 for r in rooms if r.get('status') == 'Reserved')
            if reserved:        bar_data.append(("Reserved", reserved, t['blue']))
            if not bar_data:    bar_data = [("No Rooms", 1, t['border'])]
            self.room_status_chart.set_data(bar_data)

            # Room cards preview (first 10)
            self._refresh_room_cards(rooms[:10])
        except Exception:
            pass

        # ── Renter stats ─────────────────────
        renters_count = 0
        try:
            stats = self.renter_db.get_stats()
            if stats:
                renters_count = stats.get("renters", 0)
                self.stat_boarders.set_value(renters_count)
        except Exception:
            pass

        # ── Renter chart ─────────────────────
        try:
            conn = self.renter_db.connect()
            if conn:
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT occupation_type, COUNT(*) AS c FROM renters WHERE renter_status='Active' GROUP BY occupation_type")
                rows = cur.fetchall()
                colors = [t['accent'], t['blue'], t['green'], t['orange'], t['red']]
                occ_data = [(r['occupation_type'], r['c'], colors[i % len(colors)]) for i, r in enumerate(rows)]
                conn.close()
                if not occ_data:
                    occ_data = [("Student", renters_count, t['accent'])]
                self.renter_chart.set_data(occ_data)
        except Exception:
            pass

        # ── Maintenance & Payment stats ───────
        maint_pending = 0
        pay_count = 0
        paid_count = 0
        overdue_count = 0
        try:
            conn = self.maintenance_db.connect()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT COUNT(*) AS c FROM maintenance_requests WHERE status='Pending'")
                maint_pending = cursor.fetchone()['c']
                self.stat_maint.set_value(maint_pending)

                cursor.execute("SELECT COUNT(*) AS c FROM payments WHERE status='Pending'")
                pay_count = cursor.fetchone()['c']
                cursor.execute("SELECT COUNT(*) AS c FROM payments WHERE status='Paid'")
                paid_count = cursor.fetchone()['c']
                cursor.execute("SELECT COUNT(*) AS c FROM payments WHERE status='Overdue'")
                overdue_count = cursor.fetchone()['c']
                self.stat_payments.set_value(pay_count)
                conn.close()
        except Exception:
            pass

        # Payment donut
        pay_donut_data = []
        if paid_count:    pay_donut_data.append(("Paid", paid_count, t['green']))
        if pay_count:     pay_donut_data.append(("Pending", pay_count, t['accent']))
        if overdue_count: pay_donut_data.append(("Overdue", overdue_count, t['red']))
        if not pay_donut_data: pay_donut_data = [("No Data", 1, t['border'])]
        self.payment_donut.set_data(pay_donut_data)

        # ── Pending maintenance cards ─────────
        self._refresh_maintenance_cards()

        # ── Recent activity ───────────────────
        try:
            logs = self.admin_db.get_activity_logs() or []
        except Exception:
            logs = []
        self.recent_logs_table.setRowCount(0)
        if not logs:
            self._set_table_row(self.recent_logs_table, 0, ["No recent activity yet", "", "", ""])
        else:
            for i, log in enumerate(logs[:8]):
                self._set_table_row(self.recent_logs_table, i, [
                    log['admin_name'], log['action_type'],
                    log['action_text'], str(log['log_timestamp'])
                ])

        self._refresh_renter_faces()

        # Refresh applications badge in sidebar
        self._refresh_app_badge()

    def _refresh_room_cards(self, rooms):
        while self.room_cards_row.count() > 1:
            item = self.room_cards_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for room in rooms:
            card = RoomCardWidget(room, on_click=lambda r=room: self._show_room_detail(r))
            self.room_cards_row.insertWidget(self.room_cards_row.count() - 1, card)

    def _show_room_detail(self, room):
        """Show full room info + amenities in a clean dialog."""
        t = Theme.get()
        cap  = int(room.get('capacity', 1) or 1)
        occ  = int(room.get('occupied', 0) or 0)
        avail = cap - occ

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Room {room.get('room_number','?')} — Full Details")
        dlg.setFixedWidth(500)
        dlg.setStyleSheet(dialog_style())
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # Photo
        photo_path = room.get('photo_path') or ''
        if photo_path and os.path.exists(photo_path):
            photo_lbl = QLabel()
            pix = QPixmap(photo_path).scaled(440, 200, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            photo_lbl.setPixmap(pix)
            photo_lbl.setStyleSheet("border-radius: 10px; background: #0D1117;")
            photo_lbl.setFixedHeight(200)
            photo_lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(photo_lbl)

        # Title row
        title_row = QHBoxLayout()
        room_num_lbl = QLabel(f"Room {room.get('room_number','?')}")
        room_num_lbl.setStyleSheet(f"color: {t['text']}; font-size: 22px; font-weight: bold; border: none; background: transparent;")
        status = room.get('status', '?')
        status_colors = {'Available': t['green'], 'Full': t['red'], 'Under Maintenance': t['orange']}
        st_color = status_colors.get(status, t['text_muted'])
        status_lbl = QLabel(f"● {status}")
        status_lbl.setStyleSheet(f"color: {st_color}; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        title_row.addWidget(room_num_lbl)
        title_row.addStretch()
        title_row.addWidget(status_lbl)
        layout.addLayout(title_row)

        # Key info grid
        info_widget = QWidget()
        info_widget.setStyleSheet(f"background: {t['surface2']}; border-radius: 10px;")
        info_grid = QGridLayout(info_widget)
        info_grid.setContentsMargins(16, 12, 16, 12)
        info_grid.setSpacing(8)

        def inf(label, value, col_offset=0):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {t['text_muted']}; font-size: 12px; background: transparent; border: none;")
            val = QLabel(str(value))
            val.setStyleSheet(f"color: {t['text']}; font-size: 13px; font-weight: bold; background: transparent; border: none;")
            return lbl, val

        fields = [
            ("Floor:", room.get('floor_level','?')),
            ("Capacity:", f"{cap} beds"),
            ("Occupied:", f"{occ} beds"),
            ("Available:", f"{avail} bed{'s' if avail != 1 else ''}"),
            ("Monthly Rate:", f"₱{float(room.get('monthly_rate',0)):,.2f}"),
            ("Notes:", room.get('description','—') or '—'),
        ]
        for i, (lbl_txt, val_txt) in enumerate(fields):
            row_i = i // 2
            col_base = (i % 2) * 2
            lbl, val = inf(lbl_txt, val_txt)
            info_grid.addWidget(lbl, row_i, col_base)
            info_grid.addWidget(val, row_i, col_base + 1)
        layout.addWidget(info_widget)

        # Amenities
        try:
            ams = self.room_db.get_amenities(room.get('room_id'))
        except Exception:
            ams = []

        if ams:
            am_hdr = QLabel("Amenities & Inclusions")
            am_hdr.setStyleSheet(f"color: {t['text']}; font-size: 14px; font-weight: bold; border: none; background: transparent;")
            layout.addWidget(am_hdr)

            am_grid = QGridLayout()
            am_grid.setSpacing(8)
            for idx, am in enumerate(ams):
                cond_colors = {'Good': t['green'], 'Fair': t['orange'], 'Poor': t['red']}
                cond = am.get('item_condition', 'Good')
                pill = QLabel(f"  {am.get('amenity_name','')}  ×{am.get('quantity',1)}  [{cond}]")
                pill.setStyleSheet(
                    f"background: {t['surface2']}; color: {cond_colors.get(cond, t['text'])}; "
                    f"border: 1px solid {t['border']}; padding: 5px 10px; border-radius: 8px; font-size: 11px;"
                )
                am_grid.addWidget(pill, idx // 2, idx % 2)
            layout.addLayout(am_grid)
        else:
            no_am = QLabel("No amenities listed for this room.")
            no_am.setStyleSheet(f"color: {t['text_muted']}; font-size: 12px; border: none; background: transparent;")
            layout.addWidget(no_am)

        # Buttons
        btn_row = QHBoxLayout()
        close_btn = make_btn("Close", T("surface2"), T("text"))
        close_btn.clicked.connect(dlg.reject)
        apply_btn = make_btn("  Apply for this Room", T("accent"), "black", icon="fa5s.paper-plane", icon_color="black")
        apply_btn.clicked.connect(lambda: (dlg.accept(), self._open_apply_for(room)))
        apply_btn.setVisible(avail > 0)
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)

        dlg.exec()

    def _open_apply_for(self, room):
        """Quick-apply for a specific room from the dashboard view."""
        QMessageBox.information(
            self, "Apply to Rent",
            f"To apply for Room {room.get('room_number','?')}, please go to the Welcome page "
            f"and click 'Apply to Rent', then specify your preferred room. "
            f"Or contact the admin directly."
        )


    def _refresh_maintenance_cards(self):
        # Clear existing cards
        while self.maint_cards_layout.count():
            item = self.maint_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            requests = self.maintenance_db.get_all_requests()
            pending = [r for r in requests if r.get('status') == 'Pending'][:4]
            if not pending:
                empty_lbl = QLabel("✓ No pending maintenance requests.")
                empty_lbl.setStyleSheet(f"color: {T('green')}; font-size: 13px; padding: 10px;")
                self.maint_cards_layout.addWidget(empty_lbl)
                return
            for req in pending:
                req_copy = dict(req)
                def make_resolve(r=req_copy):
                    def fn():
                        ok = self.maintenance_db.update_status(
                            r['request_id'], "Completed",
                            "Resolved from dashboard.",
                            QDate.currentDate().toString("yyyy-MM-dd")
                        )
                        if ok:
                            if self.current_user and self.current_user.get('admin_id'):
                                self.admin_db.add_log(
                                    self.current_user['admin_id'],
                                    'RESOLVE_MAINTENANCE',
                                    f"Resolved request ID {r['request_id']} from dashboard"
                                )
                            self._refresh_maintenance_cards()
                            self.stat_maint.set_value(
                                int(self.stat_maint.value_label.text() or 0) - 1
                            )
                    return fn

                def make_view(r=req_copy):
                    def fn():
                        dlg = MaintenanceDetailDialog(self, r)
                        dlg.exec()
                    return fn

                card = MaintenanceCardWidget(req_copy, make_resolve(), make_view())
                self.maint_cards_layout.addWidget(card)
        except Exception as e:
            print(f"[Maintenance cards] {e}")

    def _refresh_renter_faces(self):
        while self.renter_faces_row.count() > 1:
            item = self.renter_faces_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        try:
            renters = self.renter_db.get_all_renters()
            active = [r for r in renters if r.get('renter_status') == 'Active']
            for r in active[:30]:
                name = f"{r.get('first_name','')} {r.get('last_name','')}".strip()
                profile_path = r.get('profile_path') or r.get('profile_pic_path')
                av = AvatarWidget(name, 48, profile_path)
                av.setCursor(Qt.PointingHandCursor)
                av.setToolTip(name)
                renter_copy = dict(r)
                av.mousePressEvent = lambda ev, rd=renter_copy: self._show_renter_detail(rd)
                short_name = name.split()[0] if name else "?"
                nm_lbl = QLabel(short_name)
                nm_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 9px;")
                nm_lbl.setAlignment(Qt.AlignCenter)
                wrapper = QWidget()
                wrapper.setStyleSheet("background: transparent;")
                wl = QVBoxLayout(wrapper)
                wl.setContentsMargins(0, 0, 0, 0)
                wl.setSpacing(2)
                wl.addWidget(av, alignment=Qt.AlignCenter)
                wl.addWidget(nm_lbl, alignment=Qt.AlignCenter)
                self.renter_faces_row.insertWidget(self.renter_faces_row.count() - 1, wrapper)
        except Exception:
            pass

    def _show_renter_detail(self, renter_data):
        dlg = PersonDetailDialog(self, renter_data, "renter")
        dlg.exec()

    def _show_staff_detail(self, staff_data):
        dlg = PersonDetailDialog(self, staff_data, "staff")
        dlg.exec()

    # ══════════════════════════════════════════
    #  RENTERS PAGE
    # ══════════════════════════════════════════
    def _build_renters_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addWidget(page_header("Renter Management", "  Register Renter", self.open_add_renter_dialog, btn_icon="fa5s.user-plus"))
        layout.addSpacing(10)

        # Pending applications banner
        self.pending_banner = QFrame()
        self.pending_banner.setStyleSheet(f"background: {T('accent_dim')}; border-radius: 10px; border: 1px solid {T('accent')};")
        pb_layout = QHBoxLayout(self.pending_banner)
        pb_layout.setContentsMargins(16, 10, 16, 10)
        self.pending_label = QLabel("⚠  There are pending rental applications awaiting approval.")
        self.pending_label.setStyleSheet(f"color: {T('accent')}; font-size: 13px; font-weight: bold;")
        approve_btn = make_btn("Review & Approve", T("accent"), "black", height=34)
        approve_btn.clicked.connect(self._show_pending_applications)
        pb_layout.addWidget(self.pending_label)
        pb_layout.addStretch()
        pb_layout.addWidget(approve_btn)
        self.pending_banner.setVisible(False)
        layout.addWidget(self.pending_banner)

        search_row = QHBoxLayout()
        self.renter_search = QLineEdit()
        self.renter_search.setPlaceholderText("⌕  Search by name, contact, or email…")
        self.renter_search.setStyleSheet(input_style() + "min-height:38px;")
        self.renter_search.textChanged.connect(self.search_renters)
        search_row.addWidget(self.renter_search)

        # Filter by status
        self.renter_filter = QComboBox()
        self.renter_filter.addItems(["All", "Active", "Inactive", "Pending", "Blacklisted"])
        self.renter_filter.setStyleSheet(input_style() + "min-width: 120px;")
        self.renter_filter.currentTextChanged.connect(self._filter_renters)
        search_row.addWidget(self.renter_filter)
        layout.addLayout(search_row)
        layout.addSpacing(10)

        self.renters_table = self._make_table(
            ["ID", "Avatar", "Full Name", "Gender", "Occupation", "Contact", "Email", "Status"]
        )
        self.renters_table.setColumnWidth(1, 56)
        self.renters_table.setRowHeight(0, 52)
        self.renters_table.clicked.connect(self._on_renter_row_clicked)
        layout.addWidget(self.renters_table)

        btn_row = QHBoxLayout()
        view_btn   = make_btn("  View",    T("blue"),   "white", icon="fa5s.eye",       icon_color="white")
        edit_btn   = make_btn("  Edit",    T("blue"),   "white", icon="fa5s.edit",      icon_color="white")
        self.renter_delete_btn = make_btn("  Delete",  T("red"),    "white", icon="fa5s.trash-alt", icon_color="white")
        pic_btn    = make_btn("  Set Pic", T("orange"), "white", icon="fa5s.camera",    icon_color="white")
        view_btn.clicked.connect(self._view_renter)
        edit_btn.clicked.connect(self.open_edit_renter_dialog)
        self.renter_delete_btn.clicked.connect(self.delete_renter)
        pic_btn.clicked.connect(self._renter_set_pic)
        btn_row.addStretch()
        btn_row.addWidget(view_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(self.renter_delete_btn)
        btn_row.addWidget(pic_btn)
        layout.addLayout(btn_row)
        return page

    def _show_pending_applications(self):
        """Called from the renters page banner — navigate to Applications page."""
        self.switch_page(1)
        for btn in self.sidebar_buttons:
            if btn.property("page_index") == 1:
                btn.setChecked(True)
                break

    # ══════════════════════════════════════════
    #  APPLICATIONS PAGE  (NEW)
    # ══════════════════════════════════════════
    def _build_applications_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel("Rental Applications")
        title.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        hdr.addWidget(title)
        hdr.addStretch()
        layout.addLayout(hdr)

        sub = QLabel(
            "These are applications submitted through the public 'Apply to Rent' form.\n"
            "Approve an applicant to automatically create their renter record and login credentials."
        )
        sub.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        # Mini stat cards
        stat_row = QHBoxLayout()
        stat_row.setSpacing(12)
        self.app_stat_pending  = StatCard("Pending",  "0", T("accent"), "fa5s.clock")
        self.app_stat_approved = StatCard("Approved", "0", T("green"),  "fa5s.check-circle")
        self.app_stat_rejected = StatCard("Rejected", "0", T("red"),    "fa5s.times-circle")
        self.app_stat_total    = StatCard("Total",    "0", T("blue"),   "fa5s.file-alt")
        for c in [self.app_stat_pending, self.app_stat_approved, self.app_stat_rejected, self.app_stat_total]:
            c.setFixedHeight(100)
            stat_row.addWidget(c)
        layout.addLayout(stat_row)

        # Filter row
        filter_row = QHBoxLayout()
        self.app_search = QLineEdit()
        self.app_search.setPlaceholderText("⌕  Search by name, email, or contact…")
        self.app_search.setStyleSheet(input_style() + "min-height: 36px;")
        self.app_search.textChanged.connect(self._filter_applications)
        self.app_status_filter = QComboBox()
        self.app_status_filter.addItems(["All", "Pending", "Approved", "Rejected"])
        self.app_status_filter.setStyleSheet(input_style() + "min-width: 130px;")
        self.app_status_filter.currentTextChanged.connect(self._filter_applications)
        filter_row.addWidget(self.app_search)
        filter_row.addWidget(self.app_status_filter)
        layout.addLayout(filter_row)

        self.applications_table = self._make_table([
            "ID", "Full Name", "Gender", "Occupation", "Contact", "Email",
            "Preferred Room", "Submitted", "Status"
        ])
        layout.addWidget(self.applications_table)

        btn_row = QHBoxLayout()
        view_btn = make_btn("  View Details", T("blue"),  "white", icon="fa5s.eye",         icon_color="white")
        self.app_approve_btn = make_btn("  Approve",     T("green"), "white", icon="fa5s.user-check",  icon_color="white")
        self.app_reject_btn  = make_btn("  Reject",      T("red"),   "white", icon="fa5s.user-times",  icon_color="white")
        delete_btn = make_btn("  Delete",                T("surface2"), T("text_muted"), icon="fa5s.trash-alt", icon_color=T("text_muted"))
        view_btn.clicked.connect(self._view_application)
        self.app_approve_btn.clicked.connect(self._approve_application)
        self.app_reject_btn.clicked.connect(self._reject_application)
        delete_btn.clicked.connect(self._delete_application)
        btn_row.addStretch()
        btn_row.addWidget(view_btn)
        btn_row.addWidget(self.app_approve_btn)
        btn_row.addWidget(self.app_reject_btn)
        btn_row.addWidget(delete_btn)
        layout.addLayout(btn_row)
        return page

    def load_applications(self):
        apps = self.app_db.get_all_applications()
        self._display_applications(apps)
        pending  = sum(1 for a in apps if a.get('status') == 'Pending')
        approved = sum(1 for a in apps if a.get('status') == 'Approved')
        rejected = sum(1 for a in apps if a.get('status') == 'Rejected')
        if hasattr(self, 'app_stat_pending'):
            self.app_stat_pending.set_value(pending)
            self.app_stat_approved.set_value(approved)
            self.app_stat_rejected.set_value(rejected)
            self.app_stat_total.set_value(len(apps))
        self._refresh_app_badge()

    def _display_applications(self, apps):
        self.applications_table.setRowCount(0)
        t = Theme.get()
        sc = {'Pending': t['accent'], 'Approved': t['green'], 'Rejected': t['red']}
        for i, a in enumerate(apps):
            name = f"{a.get('first_name','')} {a.get('last_name','')}".strip()
            submitted = str(a.get('submitted_at', '—'))[:16]
            self._set_table_row(self.applications_table, i, [
                a['application_id'], name,
                a.get('gender', '—'), a.get('occupation_type', '—'),
                a.get('contact_number', '—'), a.get('email', '—'),
                a.get('preferred_room', '—') or '—',
                submitted, a.get('status', '—')
            ])
            status_color = sc.get(a.get('status', ''), t['text'])
            self.applications_table.item(i, 8).setForeground(QColor(status_color))

    def _filter_applications(self):
        apps = self.app_db.get_all_applications()
        kw = self.app_search.text().strip().lower() if hasattr(self, 'app_search') else ""
        sf = self.app_status_filter.currentText() if hasattr(self, 'app_status_filter') else "All"
        if kw:
            apps = [a for a in apps if
                    kw in f"{a.get('first_name','')} {a.get('last_name','')}".lower() or
                    kw in str(a.get('email', '')).lower() or
                    kw in str(a.get('contact_number', '')).lower()]
        if sf != "All":
            apps = [a for a in apps if a.get('status') == sf]
        self._display_applications(apps)

    def _get_selected_application(self):
        row = self.applications_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an application first.")
            return None
        app_id = int(self.applications_table.item(row, 0).text())
        apps = self.app_db.get_all_applications()
        return next((a for a in apps if a['application_id'] == app_id), None)

    def _view_application(self):
        app = self._get_selected_application()
        if not app:
            return
        t = Theme.get()
        dlg = QDialog(self)
        dlg.setWindowTitle("Application Details")
        dlg.setFixedWidth(500)
        dlg.setStyleSheet(dialog_style())
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(10)

        name = f"{app.get('first_name','')} {app.get('last_name','')}".strip()
        av = AvatarWidget(name, 72)
        layout.addWidget(av, alignment=Qt.AlignCenter)

        title = QLabel(name)
        title.setStyleSheet(f"color: {T('text')}; font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        status = app.get('status', '—')
        sc = {'Pending': T('accent'), 'Approved': T('green'), 'Rejected': T('red')}
        st_lbl = QLabel(f"● {status}")
        st_lbl.setStyleSheet(f"color: {sc.get(status, T('text'))}; font-size: 13px; font-weight: bold;")
        st_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(st_lbl)

        line = QFrame(); line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background: {T('border')}; max-height: 1px;")
        layout.addWidget(line)

        fields = [
            ("Gender",          app.get('gender')),
            ("Occupation",      app.get('occupation_type')),
            ("Institution",     app.get('institution')),
            ("Contact",         app.get('contact_number')),
            ("Email",           app.get('email')),
            ("Address",         app.get('address')),
            ("Emergency Name",  app.get('emergency_name')),
            ("Emergency No.",   app.get('emergency_number')),
            ("Preferred Room",  app.get('preferred_room')),
            ("Message",         app.get('message')),
            ("Submitted",       str(app.get('submitted_at', '—'))[:16]),
        ]
        for lbl, val in fields:
            if not val:
                continue
            row_w = QHBoxLayout()
            l = QLabel(f"{lbl}:")
            l.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px; font-weight: bold; min-width: 110px;")
            v = QLabel(str(val))
            v.setStyleSheet(f"color: {T('text')}; font-size: 13px;")
            v.setWordWrap(True)
            row_w.addWidget(l)
            row_w.addWidget(v, stretch=1)
            layout.addLayout(row_w)

        close_btn = make_btn("Close", T("surface2"), T("text"))
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        dlg.exec()

    def _approve_application(self):
        app = self._get_selected_application()
        if not app:
            return
        if app.get('status') != 'Pending':
            QMessageBox.information(self, "Already Processed",
                                    f"This application is already '{app.get('status')}'.")
            return
        name = f"{app.get('first_name','')} {app.get('last_name','')}".strip()
        reply = QMessageBox.question(
            self, "Approve Application",
            f"Approve '{name}'?\n\n"
            f"This will create their renter record and generate login credentials.\n"
            f"Default password will be: dorm123\n\n"
            f"You can share the credentials with the applicant.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        admin_id = self.current_user.get('admin_id') if self.current_user else None
        ok, username, pw = self.app_db.approve_application(app['application_id'], admin_id)
        if ok:
            if admin_id:
                self.admin_db.add_log(admin_id, 'APPROVE_APPLICATION',
                                      f"Approved application from {name}. Login: {username}")
            QMessageBox.information(
                self, "✓ Application Approved!",
                f"'{name}' has been approved and registered as a renter.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  Username:  {username}\n"
                f"  Password:  {pw}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Please share these credentials with the renter.\n"
                f"They can change their password after first login."
            )
            self.load_applications()
            self._refresh_app_badge()
        else:
            QMessageBox.critical(self, "Error", f"Approval failed: {username}")

    def _reject_application(self):
        app = self._get_selected_application()
        if not app:
            return
        if app.get('status') != 'Pending':
            QMessageBox.information(self, "Already Processed",
                                    f"This application is already '{app.get('status')}'.")
            return
        name = f"{app.get('first_name','')} {app.get('last_name','')}".strip()
        reason_dlg = QDialog(self)
        reason_dlg.setWindowTitle("Reject Application")
        reason_dlg.setFixedWidth(400)
        reason_dlg.setStyleSheet(dialog_style())
        rl = QVBoxLayout(reason_dlg)
        rl.setContentsMargins(24, 24, 24, 24)
        rl.setSpacing(12)
        rl.addWidget(QLabel(f"Rejecting application from: {name}"))
        reason_input = QTextEdit()
        reason_input.setPlaceholderText("Reason for rejection (optional)…")
        reason_input.setFixedHeight(80)
        reason_input.setStyleSheet(input_style())
        rl.addWidget(reason_input)
        btn_row = QHBoxLayout()
        cancel = make_btn("Cancel", T("surface2"), T("text"))
        confirm = make_btn("  Reject", T("red"), "white", icon="fa5s.times", icon_color="white")
        cancel.clicked.connect(reason_dlg.reject)
        confirm.clicked.connect(reason_dlg.accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(confirm)
        rl.addLayout(btn_row)
        if reason_dlg.exec():
            reason = reason_input.toPlainText().strip()
            admin_id = self.current_user.get('admin_id') if self.current_user else None
            ok = self.app_db.reject_application(app['application_id'], admin_id, reason)
            if ok:
                if admin_id:
                    self.admin_db.add_log(admin_id, 'REJECT_APPLICATION',
                                          f"Rejected application from {name}.")
                QMessageBox.information(self, "Rejected", f"Application from '{name}' has been rejected.")
                self.load_applications()
                self._refresh_app_badge()
            else:
                QMessageBox.critical(self, "Error", "Failed to reject application.")

    def _delete_application(self):
        app = self._get_selected_application()
        if not app:
            return
        name = f"{app.get('first_name','')} {app.get('last_name','')}".strip()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Permanently delete application from '{name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            ok = self.app_db.delete_application(app['application_id'])
            if ok:
                self.load_applications()
                self._refresh_app_badge()

    def load_renters(self, rows=None):
        # Check for pending applications via ApplicationModule
        try:
            pending_count = self.app_db.get_pending_count()
            if pending_count > 0:
                self.pending_label.setText(
                    f"⚠  {pending_count} rental application(s) pending review in Applications page."
                )
                self.pending_banner.setVisible(True)
            else:
                self.pending_banner.setVisible(False)
        except Exception:
            self.pending_banner.setVisible(False)

        if rows is None:
            rows = self.renter_db.get_all_renters()
        self.renters_table.setRowCount(0)
        t = Theme.get()
        status_colors = {"Active": t['green'], "Inactive": t['text_muted'],
                         "Pending": t['accent'], "Blacklisted": t['red']}
        for i, r in enumerate(rows):
            self.renters_table.insertRow(i)
            self.renters_table.setRowHeight(i, 52)
            name = f"{r['first_name']} {r.get('middle_name','')} {r['last_name']}".strip()
            profile_path = r.get('profile_path') or r.get('profile_pic_path')
            av = AvatarWidget(name, 40, profile_path)
            self.renters_table.setCellWidget(i, 1, av)
            vals = [r['renter_id'], None, name, r['gender'], r['occupation_type'],
                    r['contact_number'], r['email'], r['renter_status']]
            for col, val in enumerate(vals):
                if col == 1:
                    continue
                item = QTableWidgetItem(str(val) if val is not None else "—")
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if col == 7:
                    item.setForeground(QColor(status_colors.get(str(val), t['text'])))
                self.renters_table.setItem(i, col, item)

    def _on_renter_row_clicked(self, index):
        pass

    def search_renters(self):
        kw = self.renter_search.text().strip()
        if kw:
            rows = self.renter_db.search_renters(kw)
        else:
            rows = self.renter_db.get_all_renters()
        status_filter = self.renter_filter.currentText() if hasattr(self, 'renter_filter') else "All"
        if status_filter != "All":
            rows = [r for r in rows if r.get('renter_status') == status_filter]
        self.load_renters(rows)

    def _filter_renters(self):
        self.search_renters()

    def _view_renter(self):
        row = self.renters_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a renter.")
            return
        renter_id = int(self.renters_table.item(row, 0).text())
        renter = self.renter_db.get_renter_by_id(renter_id)
        if renter:
            self._show_renter_detail(renter)

    def _renter_set_pic(self):
        row = self.renters_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a renter.")
            return
        renter_id = int(self.renters_table.item(row, 0).text())
        renter = self.renter_db.get_renter_by_id(renter_id)
        if not renter:
            return
        name = f"{renter.get('first_name','')} {renter.get('last_name','')}".strip()
        dlg = RenterSelfProfileDialog(self, name, renter_id, "renter")
        if dlg.exec() and dlg.chosen_path:
            try:
                conn = self.renter_db.connect()
                cur = conn.cursor()
                cur.execute("UPDATE renters SET profile_pic_path=%s WHERE renter_id=%s", (dlg.chosen_path, renter_id))
                conn.commit()
                conn.close()
            except Exception:
                pass
            QMessageBox.information(self, "Updated", f"{name}'s profile picture has been set!")
            self.load_renters()

    def open_add_renter_dialog(self):
        dlg = RenterDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            status = data.pop('renter_status', 'Active')
            renter_id = self.renter_db.add_renter(**data)
            if renter_id:
                if status != 'Active':
                    try:
                        conn = self.renter_db.connect()
                        cur = conn.cursor()
                        cur.execute("UPDATE renters SET renter_status=%s WHERE renter_id=%s", (status, renter_id))
                        conn.commit()
                        conn.close()
                    except Exception:
                        pass
                if self.current_user and self.current_user.get('admin_id'):
                    self.admin_db.add_log(self.current_user['admin_id'], 'ADD_RENTER',
                                          f"Registered renter: {data['first_name']} {data['last_name']}")
                QMessageBox.information(self, "Success", "Renter registered!")
                self.load_renters()
            else:
                QMessageBox.critical(self, "Error", "Failed to register renter.")

    def open_edit_renter_dialog(self):
        row = self.renters_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a renter.")
            return
        renter_id = int(self.renters_table.item(row, 0).text())
        renter = self.renter_db.get_renter_by_id(renter_id)
        if not renter:
            return
        dlg = RenterDialog(self, renter)
        if dlg.exec():
            data = dlg.get_data()
            status = data.pop('renter_status', 'Active')
            data['renter_status'] = status
            ok = self.renter_db.update_renter(renter_id, **data)
            if ok:
                if self.current_user and self.current_user.get('admin_id'):
                    self.admin_db.add_log(self.current_user['admin_id'], 'EDIT_RENTER',
                                          f"Edited renter ID {renter_id}")
                QMessageBox.information(self, "Success", "Renter updated!")
                self.load_renters()
            else:
                QMessageBox.critical(self, "Error", "Update failed.")

    def delete_renter(self):
        row = self.renters_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a renter.")
            return
        renter_id = int(self.renters_table.item(row, 0).text())
        name = self.renters_table.item(row, 2).text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Delete renter '{name}'?\nThis cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            ok = self.renter_db.delete_renter(renter_id)
            if ok:
                if self.current_user and self.current_user.get('admin_id'):
                    self.admin_db.add_log(self.current_user['admin_id'], 'DELETE_RENTER',
                                          f"Deleted renter: {name}")
                self.load_renters()
            else:
                QMessageBox.critical(self, "Error", "Delete failed.")

    # ══════════════════════════════════════════
    #  STAFF PAGE
    # ══════════════════════════════════════════
    def _build_staff_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        self.staff_page_header = page_header("Staff Management")
        layout.addWidget(self.staff_page_header)
        layout.addSpacing(10)
        self.staff_table = self._make_table(["ID", "Avatar", "Full Name", "Username", "Role", "Joined"])
        self.staff_table.setColumnWidth(1, 56)
        layout.addWidget(self.staff_table)
        btn_row = QHBoxLayout()
        view_btn = make_btn("  View", T("blue"), "white", icon="fa5s.eye", icon_color="white")
        self.staff_edit_btn   = make_btn("  Edit",   T("blue"),  "white", icon="fa5s.edit",      icon_color="white")
        self.staff_delete_btn = make_btn("  Delete", T("red"),   "white", icon="fa5s.trash-alt", icon_color="white")
        self.staff_add_btn    = make_btn("  Add Staff", T("green"), "white", icon="fa5s.user-plus", icon_color="white")
        view_btn.clicked.connect(self._view_staff)
        self.staff_edit_btn.clicked.connect(self.open_edit_staff_dialog)
        self.staff_delete_btn.clicked.connect(self.delete_staff)
        self.staff_add_btn.clicked.connect(self.open_add_staff_dialog)
        btn_row.addStretch()
        btn_row.addWidget(view_btn)
        btn_row.addWidget(self.staff_edit_btn)
        btn_row.addWidget(self.staff_delete_btn)
        btn_row.addWidget(self.staff_add_btn)
        layout.addLayout(btn_row)
        return page

    def load_staff(self):
        try:
            admins = self.admin_db.get_all_admins()
        except Exception:
            admins = []
        self.staff_table.setRowCount(0)
        for i, a in enumerate(admins):
            self.staff_table.insertRow(i)
            self.staff_table.setRowHeight(i, 52)
            name = a.get('full_name', '—')
            av = AvatarWidget(name, 40)
            self.staff_table.setCellWidget(i, 1, av)
            joined = str(a.get('created_at', '—'))[:10] if a.get('created_at') else '—'
            vals = [a.get('admin_id', i), None, name, a.get('username', '—'), a.get('role', '—'), joined]
            for col, val in enumerate(vals):
                if col == 1:
                    continue
                item = QTableWidgetItem(str(val) if val is not None else "—")
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.staff_table.setItem(i, col, item)

    def _view_staff(self):
        row = self.staff_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a staff member.")
            return
        try:
            staff_id = int(self.staff_table.item(row, 0).text())
            admins = self.admin_db.get_all_admins()
            staff = next((a for a in admins if a.get('admin_id') == staff_id), None)
            if staff:
                self._show_staff_detail(staff)
        except Exception:
            pass

    def open_add_staff_dialog(self):
        dlg = StaffDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            try:
                conn = self.admin_db.connect()
                cur = conn.cursor()
                pw = data.pop('password', 'changeme123')
                hashed = hashlib.sha256(pw.encode()).hexdigest()
                cur.execute("INSERT INTO admins (full_name, username, password, role) VALUES (%s,%s,%s,%s)",
                            (data['full_name'], data['username'], hashed, data.get('role', 'Staff')))
                conn.commit()
                conn.close()
                if self.current_user and self.current_user.get('admin_id'):
                    self.admin_db.add_log(self.current_user['admin_id'], 'ADD_STAFF',
                                          f"Added staff: {data['full_name']}")
                QMessageBox.information(self, "Success", "Staff added!")
                self.load_staff()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed: {e}")

    def open_edit_staff_dialog(self):
        row = self.staff_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a staff member.")
            return
        try:
            staff_id = int(self.staff_table.item(row, 0).text())
            admins = self.admin_db.get_all_admins()
            staff = next((a for a in admins if a.get('admin_id') == staff_id), None)
            if not staff:
                return
            dlg = StaffDialog(self, staff)
            if dlg.exec():
                data = dlg.get_data()
                try:
                    conn = self.admin_db.connect()
                    cur = conn.cursor()
                    if 'password' in data:
                        hashed = hashlib.sha256(data.pop('password').encode()).hexdigest()
                        cur.execute("UPDATE admins SET password=%s WHERE admin_id=%s", (hashed, staff_id))
                    cur.execute("UPDATE admins SET full_name=%s, username=%s, role=%s WHERE admin_id=%s",
                                (data['full_name'], data['username'], data.get('role', 'Staff'), staff_id))
                    conn.commit()
                    conn.close()
                    QMessageBox.information(self, "Success", "Staff updated!")
                    self.load_staff()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Update failed: {e}")
        except Exception:
            pass

    def delete_staff(self):
        row = self.staff_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a staff member.")
            return
        staff_id = int(self.staff_table.item(row, 0).text())
        name = self.staff_table.item(row, 2).text()
        if self.current_user and self.current_user.get('admin_id') == staff_id:
            QMessageBox.warning(self, "Cannot Delete", "You cannot delete your own account.")
            return
        reply = QMessageBox.question(self, "Confirm", f"Delete staff '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                conn = self.admin_db.connect()
                cur = conn.cursor()
                cur.execute("DELETE FROM admins WHERE admin_id=%s", (staff_id,))
                conn.commit()
                conn.close()
                self.load_staff()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete failed: {e}")

    # ══════════════════════════════════════════
    #  ALL ROOMS PAGE
    # ══════════════════════════════════════════
    def _build_rooms_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        header_row = QHBoxLayout()
        title = QLabel("Room Management")
        title.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        self.room_add_btn = make_btn("  Add Room", T("green"), "white", icon="fa5s.plus", icon_color="white")
        self.room_add_btn.clicked.connect(self.open_add_room_dialog)
        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(self.room_add_btn)
        layout.addLayout(header_row)
        layout.addSpacing(10)

        # Mini stats row
        mini_stats = QHBoxLayout()
        mini_stats.setSpacing(12)
        self.rm_stat_total = StatCard("Total Rooms", "—", T("blue"), "fa5s.building")
        self.rm_stat_avail = StatCard("Available", "—", T("green"), "fa5s.door-open")
        self.rm_stat_full  = StatCard("Full", "—", T("red"), "fa5s.door-closed")
        self.rm_stat_maint = StatCard("Under Maint.", "—", T("orange"), "fa5s.tools")
        for c in [self.rm_stat_total, self.rm_stat_avail, self.rm_stat_full, self.rm_stat_maint]:
            c.setFixedHeight(100)
            mini_stats.addWidget(c)
        layout.addLayout(mini_stats)
        layout.addSpacing(10)

        self.rooms_table = self._make_table(
            ["ID", "Room No.", "Floor", "Rate (₱)", "Capacity", "Occupied", "Available", "Status", "Notes"]
        )
        self.rooms_table.doubleClicked.connect(self.open_edit_room_dialog)
        layout.addWidget(self.rooms_table)

        btn_row = QHBoxLayout()
        edit_btn = make_btn("  Edit", T("blue"), "white", icon="fa5s.edit", icon_color="white")
        self.room_delete_btn = make_btn("  Delete", T("red"), "white", icon="fa5s.trash-alt", icon_color="white")
        edit_btn.clicked.connect(self.open_edit_room_dialog)
        self.room_delete_btn.clicked.connect(self.delete_room)
        btn_row.addStretch()
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(self.room_delete_btn)
        layout.addLayout(btn_row)
        return page

    def load_rooms(self):
        rooms = self.room_db.get_all_rooms()
        self.rooms_table.setRowCount(0)
        t = Theme.get()
        status_colors = {'Available': t['green'], 'Full': t['red'],
                         'Under Maintenance': t['orange'], 'Reserved': t['blue']}

        total = len(rooms)
        avail = sum(1 for r in rooms if r.get('status') == 'Available')
        full  = sum(1 for r in rooms if r.get('status') == 'Full')
        maint = sum(1 for r in rooms if r.get('status') == 'Under Maintenance')

        if hasattr(self, 'rm_stat_total'):
            self.rm_stat_total.set_value(total)
            self.rm_stat_avail.set_value(avail)
            self.rm_stat_full.set_value(full)
            self.rm_stat_maint.set_value(maint)

        for i, r in enumerate(rooms):
            cap = r.get('capacity', 0) or 0
            occ = r.get('occupied', 0) or 0
            avail_slots = cap - occ
            self._set_table_row(self.rooms_table, i, [
                r['room_id'], r['room_number'], r['floor_level'],
                f"₱{r['monthly_rate']:,.2f}", cap, occ, avail_slots,
                r['status'], r.get('description', '') or '—'
            ])
            status = r.get('status', '')
            color = status_colors.get(status, t['text'])
            self.rooms_table.item(i, 7).setForeground(QColor(color))

    def open_add_room_dialog(self):
        dlg = RoomDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            ok = self.room_db.add_room(**data)
            if ok:
                if self.current_user and self.current_user.get('admin_id'):
                    self.admin_db.add_log(self.current_user['admin_id'], 'ADD_ROOM',
                                          f"Added room {data['room_number']}")
                QMessageBox.information(self, "Success", "Room added!")
                self.load_rooms()
            else:
                QMessageBox.critical(self, "Error", "Failed to add room.")

    def open_edit_room_dialog(self):
        row = self.rooms_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a room.")
            return
        room_id = int(self.rooms_table.item(row, 0).text())
        room = self.room_db.get_room_by_id(room_id)
        if not room:
            return
        dlg = RoomDialog(self, room)
        if dlg.exec():
            data = dlg.get_data()
            ok = self.room_db.update_room(room_id, **data)
            if ok:
                if self.current_user and self.current_user.get('admin_id'):
                    self.admin_db.add_log(self.current_user['admin_id'], 'EDIT_ROOM', f"Edited room ID {room_id}")
                QMessageBox.information(self, "Success", "Room updated!")
                self.load_rooms()
            else:
                QMessageBox.critical(self, "Error", "Update failed.")

    def delete_room(self):
        row = self.rooms_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a room.")
            return
        room_id = int(self.rooms_table.item(row, 0).text())
        reply = QMessageBox.question(self, "Confirm", f"Delete room ID {room_id}?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            ok = self.room_db.delete_room(room_id)
            if ok:
                self.load_rooms()
            else:
                QMessageBox.critical(self, "Error", "Delete failed.")

    # ══════════════════════════════════════════
    #  VACANT ROOMS PAGE
    # ══════════════════════════════════════════
    def _build_vacant_rooms_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Vacant Rooms")
        title.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        self.vacant_count_lbl = QLabel("0 rooms available")
        self.vacant_count_lbl.setStyleSheet(f"color: {T('green')}; font-size: 14px; font-weight: bold; background: {T('surface2')}; padding: 6px 14px; border-radius: 16px;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.vacant_count_lbl)
        layout.addLayout(header)

        sub = QLabel("These rooms are currently available for new renters. Click any room card to view its details.")
        sub.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px;")
        layout.addWidget(sub)

        self.vacant_grid_widget = QWidget()
        self.vacant_grid_widget.setStyleSheet("background: transparent;")
        self.vacant_grid_layout = QGridLayout(self.vacant_grid_widget)
        self.vacant_grid_layout.setSpacing(16)
        self.vacant_grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.vacant_grid_widget)
        layout.addStretch()

        scroll.setWidget(page)
        return scroll

    def load_vacant_rooms(self):
        rooms = self.room_db.get_all_rooms()
        vacant = [r for r in rooms if r.get('status') == 'Available']

        total_beds = sum(max(0, int(r.get('capacity',0) or 0) - int(r.get('occupied',0) or 0)) for r in vacant)
        self.vacant_count_lbl.setText(f"{len(vacant)} rooms · {total_beds} beds available")

        # Clear grid
        while self.vacant_grid_layout.count():
            item = self.vacant_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not vacant:
            empty = QLabel("No vacant rooms at this time.")
            empty.setStyleSheet(f"color: {T('text_muted')}; font-size: 15px; padding: 30px;")
            self.vacant_grid_layout.addWidget(empty, 0, 0)
            return

        for i, room in enumerate(vacant):
            card = RoomCardWidget(room, on_click=lambda r=room: self._show_room_detail(r))
            self.vacant_grid_layout.addWidget(card, i // 4, i % 4)


    # ══════════════════════════════════════════
    #  OCCUPIED ROOMS PAGE
    # ══════════════════════════════════════════
    def _build_occupied_rooms_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Occupied Rooms")
        title.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        self.occupied_count_lbl = QLabel("0 rooms full")
        self.occupied_count_lbl.setStyleSheet(f"color: {T('red')}; font-size: 14px; font-weight: bold; background: {T('surface2')}; padding: 6px 14px; border-radius: 16px;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.occupied_count_lbl)
        layout.addLayout(header)

        sub = QLabel("Rooms currently at full capacity. Click any card to view details.")
        sub.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px;")
        layout.addWidget(sub)

        # Occupancy table
        self.occupied_table = self._make_table([
            "Room No.", "Floor", "Rate (₱)", "Capacity", "Occupied", "Renters"
        ])
        layout.addWidget(self.occupied_table)
        layout.addStretch()

        scroll.setWidget(page)
        return scroll

    def load_occupied_rooms(self):
        rooms = self.room_db.get_all_rooms()
        occupied = [r for r in rooms if r.get('status') == 'Full']
        self.occupied_count_lbl.setText(f"{len(occupied)} rooms full")

        self.occupied_table.setRowCount(0)
        for i, r in enumerate(occupied):
            # Try to get renter names
            renter_names = "—"
            try:
                conn = self.renter_db.connect()
                if conn:
                    cur = conn.cursor(dictionary=True)
                    cur.execute("""
                        SELECT CONCAT(r.first_name,' ',r.last_name) AS name
                        FROM assignments a JOIN renters r ON a.renter_id=r.renter_id
                        WHERE a.room_id=%s AND a.status='Active'
                    """, (r['room_id'],))
                    names = [row['name'] for row in cur.fetchall()]
                    conn.close()
                    if names:
                        renter_names = ", ".join(names)
            except Exception:
                pass

            cap = r.get('capacity', 0) or 0
            occ = r.get('occupied', 0) or 0
            self._set_table_row(self.occupied_table, i, [
                r['room_number'], r['floor_level'],
                f"₱{r['monthly_rate']:,.2f}", cap, occ, renter_names
            ])

    # ══════════════════════════════════════════
    #  BILLS & PAYMENTS PAGE
    # ══════════════════════════════════════════
    def _build_payments_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        layout.addWidget(page_header("Bills & Payments", "  Add Payment", self.open_add_payment_dialog, btn_icon="fa5s.plus"))

        # Summary cards
        pay_stats_row = QHBoxLayout()
        pay_stats_row.setSpacing(12)
        self.pay_stat_total  = StatCard("Total Collected", "₱0", T("green"),  "fa5s.check-circle")
        self.pay_stat_pend   = StatCard("Pending",         "0",  T("accent"), "fa5s.clock")
        self.pay_stat_over   = StatCard("Overdue",         "0",  T("red"),    "fa5s.exclamation-triangle")
        self.pay_stat_partial= StatCard("Partial",         "0",  T("orange"), "fa5s.adjust")
        for c in [self.pay_stat_total, self.pay_stat_pend, self.pay_stat_over, self.pay_stat_partial]:
            c.setFixedHeight(100)
            pay_stats_row.addWidget(c)
        layout.addLayout(pay_stats_row)

        # Filter row
        filter_row = QHBoxLayout()
        self.pay_search = QLineEdit()
        self.pay_search.setPlaceholderText("⌕  Search by invoice, renter, or billing month…")
        self.pay_search.setStyleSheet(input_style() + "min-height: 38px;")
        self.pay_search.textChanged.connect(self._filter_payments)
        self.pay_status_filter = QComboBox()
        self.pay_status_filter.addItems(["All", "Paid", "Pending", "Overdue", "Partial", "Advanced"])
        self.pay_status_filter.setStyleSheet(input_style() + "min-width: 120px;")
        self.pay_status_filter.currentTextChanged.connect(self._filter_payments)
        filter_row.addWidget(self.pay_search)
        filter_row.addWidget(self.pay_status_filter)
        layout.addLayout(filter_row)

        self.payments_table = self._make_table(
            ["ID", "Invoice", "Renter", "Amount (₱)", "Balance (₱)", "Method", "Billing Month", "Date", "Status"]
        )
        layout.addWidget(self.payments_table)

        btn_row = QHBoxLayout()
        status_btn = make_btn("  Mark Paid", T("green"), "white", icon="fa5s.check-circle", icon_color="white")
        self.payment_delete_btn = make_btn("  Delete", T("red"), "white", icon="fa5s.trash-alt", icon_color="white")
        status_btn.clicked.connect(self.mark_payment_paid)
        self.payment_delete_btn.clicked.connect(self.delete_payment)
        btn_row.addStretch()
        btn_row.addWidget(status_btn)
        btn_row.addWidget(self.payment_delete_btn)
        layout.addLayout(btn_row)
        return page

    def load_payments(self):
        payments = self.payment_db.get_all_payments()
        self._display_payments(payments)
        self._update_payment_stats(payments)

    def _display_payments(self, payments):
        self.payments_table.setRowCount(0)
        t = Theme.get()
        status_colors = {"Paid": t['green'], "Pending": t['accent'],
                         "Overdue": t['red'], "Partial": t['orange'], "Advanced": t['blue']}
        for i, p in enumerate(payments):
            self._set_table_row(self.payments_table, i, [
                p['payment_id'], p['invoice_number'], p['renter_name'],
                f"₱{p['amount']:,.2f}", f"₱{p['balance_amount']:,.2f}",
                p['payment_method'], p['billing_month'],
                str(p['payment_date']), p['status']
            ])
            color = status_colors.get(p['status'], t['text'])
            self.payments_table.item(i, 8).setForeground(QColor(color))

    def _update_payment_stats(self, payments):
        total_paid = sum(p['amount'] for p in payments if p['status'] == 'Paid')
        pending    = sum(1 for p in payments if p['status'] == 'Pending')
        overdue    = sum(1 for p in payments if p['status'] == 'Overdue')
        partial    = sum(1 for p in payments if p['status'] == 'Partial')
        if hasattr(self, 'pay_stat_total'):
            self.pay_stat_total.set_value(f"₱{total_paid:,.0f}")
            self.pay_stat_pend.set_value(pending)
            self.pay_stat_over.set_value(overdue)
            self.pay_stat_partial.set_value(partial)

    def _filter_payments(self):
        try:
            payments = self.payment_db.get_all_payments()
            kw = self.pay_search.text().strip().lower() if hasattr(self, 'pay_search') else ""
            sf = self.pay_status_filter.currentText() if hasattr(self, 'pay_status_filter') else "All"
            if kw:
                payments = [p for p in payments if
                            kw in str(p.get('invoice_number', '')).lower() or
                            kw in str(p.get('renter_name', '')).lower() or
                            kw in str(p.get('billing_month', '')).lower()]
            if sf != "All":
                payments = [p for p in payments if p.get('status') == sf]
            self._display_payments(payments)
            self._update_payment_stats(payments)
        except Exception:
            pass

    def open_add_payment_dialog(self):
        renters = self.renter_db.get_all_renters()
        dlg = PaymentDialog(self, renters)
        if dlg.exec():
            data = dlg.get_data()
            if self.current_user and self.current_user.get('admin_id'):
                data['processed_by'] = self.current_user['admin_id']
            ok = self.payment_db.add_payment(**data)
            if ok:
                if self.current_user and self.current_user.get('admin_id'):
                    self.admin_db.add_log(self.current_user['admin_id'], 'ADD_PAYMENT',
                                          f"Added payment {data['invoice_number']}")
                QMessageBox.information(self, "Success", "Payment recorded!")
                self.load_payments()
            else:
                QMessageBox.critical(self, "Error", "Failed to add payment.")

    def mark_payment_paid(self):
        row = self.payments_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a payment.")
            return
        payment_id = int(self.payments_table.item(row, 0).text())
        ok = self.payment_db.update_payment_status(payment_id, "Paid")
        if ok:
            self.load_payments()

    def delete_payment(self):
        row = self.payments_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a payment.")
            return
        payment_id = int(self.payments_table.item(row, 0).text())
        reply = QMessageBox.question(self, "Confirm", "Delete this payment record?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            ok = self.payment_db.delete_payment(payment_id)
            if ok:
                self.load_payments()

    # ══════════════════════════════════════════
    #  REPORTS PAGE  (rich payment analytics)
    # ══════════════════════════════════════════
    def _build_reports_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # ── Header ────────────────────────────
        hdr_row = QHBoxLayout()
        title_lbl = QLabel("Reports & Analytics")
        title_lbl.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        refresh_btn = make_btn("  Refresh", T("surface2"), T("text"), icon="fa5s.sync-alt", icon_color=T("text"), height=36)
        refresh_btn.clicked.connect(self.load_reports)
        hdr_row.addWidget(title_lbl)
        hdr_row.addStretch()
        hdr_row.addWidget(refresh_btn)
        layout.addLayout(hdr_row)

        sub_lbl = QLabel("Payment performance, revenue trends, and collection analytics for your dormitory.")
        sub_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px;")
        layout.addWidget(sub_lbl)

        # ── KPI Cards Row ─────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)
        self.rpt_total_revenue   = StatCard("Total Revenue",      "₱0",  T("green"),  "fa5s.money-bill-wave")
        self.rpt_total_pending   = StatCard("Total Pending",       "₱0",  T("accent"), "fa5s.clock")
        self.rpt_total_overdue   = StatCard("Total Overdue",       "₱0",  T("red"),    "fa5s.exclamation-triangle")
        self.rpt_collection_rate = StatCard("Collection Rate",     "0%",  T("blue"),   "fa5s.percentage")
        self.rpt_txn_count       = StatCard("Total Transactions",  "0",   T("purple"), "fa5s.list-alt")
        self.rpt_avg_payment     = StatCard("Avg. Payment",        "₱0",  T("teal"),   "fa5s.calculator")
        for c in [self.rpt_total_revenue, self.rpt_total_pending, self.rpt_total_overdue,
                  self.rpt_collection_rate, self.rpt_txn_count, self.rpt_avg_payment]:
            c.setFixedHeight(115)
            kpi_row.addWidget(c)
        layout.addLayout(kpi_row)

        # ── Revenue Trend Line Chart ───────────
        sep1 = QLabel("Monthly Revenue Trend")
        sep1.setStyleSheet(f"color: {T('text')}; font-size: 15px; font-weight: bold; margin-top: 6px;")
        layout.addWidget(sep1)

        revenue_card = self._card_frame()
        revenue_card.setMinimumHeight(280)
        rev_layout = QVBoxLayout(revenue_card)
        rev_layout.setContentsMargins(16, 16, 16, 16)

        # Filter row inside chart card
        rev_filter = QHBoxLayout()
        self.rpt_period_filter = QComboBox()
        self.rpt_period_filter.addItems(["Last 6 Months", "Last 12 Months", "All Time"])
        self.rpt_period_filter.setStyleSheet(input_style() + "max-width: 160px;")
        self.rpt_period_filter.currentTextChanged.connect(self.load_reports)
        rev_filter.addStretch()
        rev_filter.addWidget(QLabel("Period:"))
        rev_filter.addWidget(self.rpt_period_filter)
        rev_layout.addLayout(rev_filter)

        self.revenue_line_chart = LineChartWidget("Revenue (₱) — Collected vs Expected")
        self.revenue_line_chart.setMinimumHeight(230)
        rev_layout.addWidget(self.revenue_line_chart)
        layout.addWidget(revenue_card)

        # ── Two charts side by side ───────────
        sep2 = QLabel("Payment Breakdown")
        sep2.setStyleSheet(f"color: {T('text')}; font-size: 15px; font-weight: bold; margin-top: 4px;")
        layout.addWidget(sep2)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        # Monthly bar chart (collected by month)
        bar_card = self._card_frame()
        bar_card.setMinimumHeight(250)
        bc_layout = QVBoxLayout(bar_card)
        bc_layout.setContentsMargins(16, 16, 16, 16)
        self.monthly_bar_chart = BarChartWidget("Monthly Collections (₱)")
        bc_layout.addWidget(self.monthly_bar_chart)
        charts_row.addWidget(bar_card, 3)

        # Payment method donut
        method_card = self._card_frame()
        method_card.setMinimumHeight(250)
        mth_layout = QVBoxLayout(method_card)
        mth_layout.setContentsMargins(16, 16, 16, 16)
        mth_title = QLabel("By Payment Method")
        mth_title.setStyleSheet(f"color: {T('text')}; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        mth_layout.addWidget(mth_title)
        self.method_donut = DonutChartWidget("Method")
        mth_layout.addWidget(self.method_donut)
        charts_row.addWidget(method_card, 2)

        # Status donut
        status_card = self._card_frame()
        status_card.setMinimumHeight(250)
        st_layout = QVBoxLayout(status_card)
        st_layout.setContentsMargins(16, 16, 16, 16)
        st_title = QLabel("By Status")
        st_title.setStyleSheet(f"color: {T('text')}; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        st_layout.addWidget(st_title)
        self.status_donut_rpt = DonutChartWidget("Status")
        st_layout.addWidget(self.status_donut_rpt)
        charts_row.addWidget(status_card, 2)

        layout.addLayout(charts_row)

        # ── Per-Renter Table ──────────────────
        sep3 = QLabel("Per-Renter Payment Summary")
        sep3.setStyleSheet(f"color: {T('text')}; font-size: 15px; font-weight: bold; margin-top: 4px;")
        layout.addWidget(sep3)

        renter_filter_row = QHBoxLayout()
        self.rpt_renter_search = QLineEdit()
        self.rpt_renter_search.setPlaceholderText("⌕  Search renter…")
        self.rpt_renter_search.setStyleSheet(input_style() + "min-height: 36px; max-width: 280px;")
        self.rpt_renter_search.textChanged.connect(self._filter_rpt_renter_table)
        renter_filter_row.addWidget(self.rpt_renter_search)
        renter_filter_row.addStretch()
        layout.addLayout(renter_filter_row)

        self.rpt_renter_table = self._make_table([
            "Renter Name", "Paid (₱)", "Pending (₱)", "Overdue (₱)", "Partial (₱)", "Txns", "Last Payment", "Status"
        ])
        layout.addWidget(self.rpt_renter_table)

        # ── Overdue Alerts ────────────────────
        sep4 = QLabel("⚠  Overdue Payment Alerts")
        sep4.setStyleSheet(f"color: {T('red')}; font-size: 15px; font-weight: bold; margin-top: 4px;")
        layout.addWidget(sep4)

        self.rpt_overdue_table = self._make_table([
            "Invoice", "Renter", "Amount (₱)", "Balance (₱)", "Billing Month", "Due Date", "Days Overdue"
        ])
        layout.addWidget(self.rpt_overdue_table)

        # ── Recent Payments ───────────────────
        sep5 = QLabel("Recent Payments")
        sep5.setStyleSheet(f"color: {T('text')}; font-size: 15px; font-weight: bold; margin-top: 4px;")
        layout.addWidget(sep5)

        self.rpt_recent_table = self._make_table([
            "Invoice", "Renter", "Amount (₱)", "Method", "Billing Month", "Date", "Status"
        ])
        self.rpt_recent_table.setMaximumHeight(220)
        layout.addWidget(self.rpt_recent_table)
        layout.addStretch()

        scroll.setWidget(page)
        return scroll

    def _filter_rpt_renter_table(self):
        """Live-filter the per-renter table by name."""
        kw = self.rpt_renter_search.text().strip().lower() if hasattr(self, 'rpt_renter_search') else ""
        for row in range(self.rpt_renter_table.rowCount()):
            item = self.rpt_renter_table.item(row, 0)
            match = (kw in item.text().lower()) if item else True
            self.rpt_renter_table.setRowHidden(row, not match)

    def load_reports(self):
        try:
            payments = self.payment_db.get_all_payments()
        except Exception:
            payments = []

        t = Theme.get()

        # ── KPI calculations ─────────────────
        total_revenue   = sum(float(p['amount']) for p in payments if p['status'] == 'Paid')
        total_pending_v = sum(float(p['amount']) for p in payments if p['status'] == 'Pending')
        total_overdue_v = sum(float(p['amount']) for p in payments if p['status'] == 'Overdue')
        paid_count      = sum(1 for p in payments if p['status'] == 'Paid')
        total_count     = len(payments)
        collection_rate = int((paid_count / total_count * 100)) if total_count else 0
        avg_payment     = (total_revenue / paid_count) if paid_count else 0

        self.rpt_total_revenue.set_value(f"₱{total_revenue:,.0f}")
        self.rpt_total_pending.set_value(f"₱{total_pending_v:,.0f}")
        self.rpt_total_overdue.set_value(f"₱{total_overdue_v:,.0f}")
        self.rpt_collection_rate.set_value(f"{collection_rate}%")
        self.rpt_txn_count.set_value(total_count)
        self.rpt_avg_payment.set_value(f"₱{avg_payment:,.0f}")

        # ── Determine period for trend charts ─
        period = self.rpt_period_filter.currentText() if hasattr(self, 'rpt_period_filter') else "Last 6 Months"
        n_months = {"Last 6 Months": 6, "Last 12 Months": 12, "All Time": 99}.get(period, 6)

        # Build monthly buckets
        monthly_collected = {}
        monthly_expected  = {}
        for p in payments:
            bm = str(p.get('billing_month', '') or '')
            key = bm[:7] if len(bm) >= 7 else bm
            if not key:
                continue
            amt = float(p['amount'])
            if p['status'] == 'Paid':
                monthly_collected[key] = monthly_collected.get(key, 0) + amt
            # Expected = all payments regardless of status
            monthly_expected[key] = monthly_expected.get(key, 0) + amt

        all_months = sorted(set(list(monthly_collected.keys()) + list(monthly_expected.keys())))
        if n_months < 99:
            all_months = all_months[-n_months:]

        # ── Revenue Line Chart (Collected vs Expected) ─
        if len(all_months) >= 2:
            collected_pts = [(m, monthly_collected.get(m, 0)) for m in all_months]
            expected_pts  = [(m, monthly_expected.get(m, 0))  for m in all_months]
            self.revenue_line_chart.set_data([
                ("Collected", collected_pts, t['green']),
                ("Expected",  expected_pts,  t['teal']),
            ])
        else:
            self.revenue_line_chart.set_data([
                ("Collected", [("No data", 0), ("—", 0)], t['border'])
            ])

        # ── Monthly Bar Chart (collected only) ─
        bar_data = []
        bar_colors = [t['green'], t['blue'], t['accent'], t['orange'], t['purple'], t['teal'],
                      t['red'], t['green'], t['blue'], t['accent'], t['orange'], t['purple']]
        for i, m in enumerate(all_months[-8:]):
            bar_data.append((m, int(monthly_collected.get(m, 0)), bar_colors[i % len(bar_colors)]))
        if bar_data:
            self.monthly_bar_chart.set_data(bar_data)
        else:
            self.monthly_bar_chart.set_data([("No data", 0, t['border'])])

        # ── Payment Method Donut ─────────────
        method_counts = {}
        for p in payments:
            if p['status'] == 'Paid':
                m = p.get('payment_method', 'Other') or 'Other'
                method_counts[m] = method_counts.get(m, 0) + float(p['amount'])
        method_colors = [t['green'], t['blue'], t['accent'], t['orange'], t['purple']]
        method_data = [(m, int(v), method_colors[i % len(method_colors)])
                       for i, (m, v) in enumerate(sorted(method_counts.items(), key=lambda x: -x[1]))]
        self.method_donut.set_data(method_data if method_data else [("No data", 1, t['border'])])

        # ── Status Donut ─────────────────────
        status_counts = {}
        for p in payments:
            s = p.get('status', 'Unknown')
            status_counts[s] = status_counts.get(s, 0) + 1
        status_c = {'Paid': t['green'], 'Pending': t['accent'], 'Overdue': t['red'],
                    'Partial': t['orange'], 'Advanced': t['blue']}
        status_data = [(s, c, status_c.get(s, t['text_muted']))
                       for s, c in sorted(status_counts.items(), key=lambda x: -x[1])]
        self.status_donut_rpt.set_data(status_data if status_data else [("No data", 1, t['border'])])

        # ── Per-Renter Table ─────────────────
        renter_data = {}
        for p in payments:
            name = p.get('renter_name', '?') or '?'
            if name not in renter_data:
                renter_data[name] = {'paid': 0.0, 'pending': 0.0, 'overdue': 0.0,
                                     'partial': 0.0, 'txns': 0, 'last': None}
            renter_data[name]['txns'] += 1
            amt = float(p['amount'])
            s = p.get('status', '')
            if s == 'Paid':
                renter_data[name]['paid'] += amt
                pd_val = p.get('payment_date')
                if pd_val and (not renter_data[name]['last'] or pd_val > renter_data[name]['last']):
                    renter_data[name]['last'] = pd_val
            elif s == 'Pending':
                renter_data[name]['pending'] += amt
            elif s == 'Overdue':
                renter_data[name]['overdue'] += amt
            elif s == 'Partial':
                renter_data[name]['partial'] += amt

        self.rpt_renter_table.setRowCount(0)
        for i, (name, d) in enumerate(sorted(renter_data.items())):
            total_due = d['paid'] + d['pending'] + d['overdue'] + d['partial']
            rate = int(d['paid'] / total_due * 100) if total_due > 0 else 0
            health = "✓ Good" if rate >= 80 else ("⚠ At Risk" if rate >= 50 else "✗ Poor")
            self._set_table_row(self.rpt_renter_table, i, [
                name,
                f"₱{d['paid']:,.2f}",
                f"₱{d['pending']:,.2f}",
                f"₱{d['overdue']:,.2f}",
                f"₱{d['partial']:,.2f}",
                d['txns'],
                str(d['last'])[:10] if d['last'] else "—",
                f"{rate}% — {health}",
            ])
            # Color the overdue column
            if d['overdue'] > 0:
                self.rpt_renter_table.item(i, 3).setForeground(QColor(t['red']))
            # Color the status column
            health_colors = {"✓ Good": t['green'], "⚠ At Risk": t['accent'], "✗ Poor": t['red']}
            h_color = next((v for k, v in health_colors.items() if k in health), t['text'])
            self.rpt_renter_table.item(i, 7).setForeground(QColor(h_color))

        # ── Overdue Alerts ────────────────────
        overdue_payments = [p for p in payments if p['status'] == 'Overdue']
        self.rpt_overdue_table.setRowCount(0)
        today = QDate.currentDate()
        for i, p in enumerate(overdue_payments):
            pay_date = p.get('payment_date')
            days = "—"
            if pay_date:
                try:
                    pd_q = QDate.fromString(str(pay_date)[:10], "yyyy-MM-dd")
                    days = str(pd_q.daysTo(today))
                except Exception:
                    pass
            self._set_table_row(self.rpt_overdue_table, i, [
                p.get('invoice_number', '—'),
                p.get('renter_name', '—'),
                f"₱{float(p['amount']):,.2f}",
                f"₱{float(p.get('balance_amount', 0)):,.2f}",
                p.get('billing_month', '—'),
                str(pay_date)[:10] if pay_date else '—',
                days
            ])
            self.rpt_overdue_table.item(i, 2).setForeground(QColor(t['red']))
            if days != "—":
                try:
                    d_int = int(days)
                    urgency = t['red'] if d_int > 30 else t['orange']
                    self.rpt_overdue_table.item(i, 6).setForeground(QColor(urgency))
                except Exception:
                    pass

        # ── Recent Payments (last 15) ─────────
        sorted_payments = sorted(payments, key=lambda p: str(p.get('payment_date', '')), reverse=True)
        self.rpt_recent_table.setRowCount(0)
        status_colors = {'Paid': t['green'], 'Pending': t['accent'], 'Overdue': t['red'],
                         'Partial': t['orange'], 'Advanced': t['blue']}
        for i, p in enumerate(sorted_payments[:15]):
            self._set_table_row(self.rpt_recent_table, i, [
                p.get('invoice_number', '—'),
                p.get('renter_name', '—'),
                f"₱{float(p['amount']):,.2f}",
                p.get('payment_method', '—'),
                p.get('billing_month', '—'),
                str(p.get('payment_date', '—'))[:10],
                p.get('status', '—'),
            ])
            sc = status_colors.get(p.get('status', ''), t['text'])
            self.rpt_recent_table.item(i, 6).setForeground(QColor(sc))

    # ══════════════════════════════════════════
    #  MAINTENANCE PAGE
    # ══════════════════════════════════════════
    def _build_maintenance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        hdr_row = QHBoxLayout()
        title = QLabel("Maintenance Requests")
        title.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        add_btn = make_btn("  Add Request", T("green"), "white", icon="fa5s.plus", icon_color="white")
        add_btn.clicked.connect(self.open_add_maintenance_dialog)
        hdr_row.addWidget(title)
        hdr_row.addStretch()
        hdr_row.addWidget(add_btn)
        layout.addLayout(hdr_row)

        # Mini stats
        maint_stats = QHBoxLayout()
        maint_stats.setSpacing(12)
        self.mst_pending   = StatCard("Pending",   "—", T("accent"), "fa5s.clock")
        self.mst_progress  = StatCard("In Progress","—", T("blue"),   "fa5s.spinner")
        self.mst_completed = StatCard("Completed", "—", T("green"),  "fa5s.check-circle")
        self.mst_high      = StatCard("High Prio", "—", T("red"),    "fa5s.fire")
        for c in [self.mst_pending, self.mst_progress, self.mst_completed, self.mst_high]:
            c.setFixedHeight(100)
            maint_stats.addWidget(c)
        layout.addLayout(maint_stats)

        # Filter
        filter_row = QHBoxLayout()
        self.maint_search = QLineEdit()
        self.maint_search.setPlaceholderText("⌕  Search by room or issue…")
        self.maint_search.setStyleSheet(input_style() + "min-height: 36px;")
        self.maint_search.textChanged.connect(self._filter_maintenance)
        self.maint_status_filter = QComboBox()
        self.maint_status_filter.addItems(["All", "Pending", "In Progress", "Completed"])
        self.maint_status_filter.setStyleSheet(input_style() + "min-width: 120px;")
        self.maint_status_filter.currentTextChanged.connect(self._filter_maintenance)
        self.maint_priority_filter = QComboBox()
        self.maint_priority_filter.addItems(["All Priorities", "High", "Medium", "Low"])
        self.maint_priority_filter.setStyleSheet(input_style() + "min-width: 120px;")
        self.maint_priority_filter.currentTextChanged.connect(self._filter_maintenance)
        filter_row.addWidget(self.maint_search)
        filter_row.addWidget(self.maint_status_filter)
        filter_row.addWidget(self.maint_priority_filter)
        layout.addLayout(filter_row)

        self.maintenance_table = self._make_table(
            ["ID", "Room", "Renter", "Issue", "Priority", "Status", "Date Requested"]
        )
        layout.addWidget(self.maintenance_table)

        btn_row = QHBoxLayout()
        view_btn    = make_btn("  View Detail",  T("blue"),  "white", icon="fa5s.eye",          icon_color="white")
        resolve_btn = make_btn("  Mark Resolved",T("green"), "white", icon="fa5s.check-circle",  icon_color="white")
        progress_btn= make_btn("  In Progress",  T("blue"),  "white", icon="fa5s.spinner",       icon_color="white")
        self.maint_delete_btn = make_btn("  Delete", T("red"), "white", icon="fa5s.trash-alt", icon_color="white")
        view_btn.clicked.connect(self._view_maintenance)
        resolve_btn.clicked.connect(self.resolve_maintenance)
        progress_btn.clicked.connect(self._mark_maintenance_in_progress)
        self.maint_delete_btn.clicked.connect(self.delete_maintenance)
        btn_row.addStretch()
        btn_row.addWidget(view_btn)
        btn_row.addWidget(progress_btn)
        btn_row.addWidget(resolve_btn)
        btn_row.addWidget(self.maint_delete_btn)
        layout.addLayout(btn_row)
        return page

    def _get_all_maintenance(self):
        try:
            return self.maintenance_db.get_all_requests()
        except Exception:
            return []

    def load_maintenance(self):
        requests = self._get_all_maintenance()
        self._display_maintenance(requests)
        self._update_maintenance_stats(requests)

    def _update_maintenance_stats(self, requests):
        pending   = sum(1 for r in requests if r.get('status') == 'Pending')
        progress  = sum(1 for r in requests if r.get('status') == 'In Progress')
        completed = sum(1 for r in requests if r.get('status') == 'Completed')
        high      = sum(1 for r in requests if r.get('priority') == 'High')
        if hasattr(self, 'mst_pending'):
            self.mst_pending.set_value(pending)
            self.mst_progress.set_value(progress)
            self.mst_completed.set_value(completed)
            self.mst_high.set_value(high)

    def _display_maintenance(self, requests):
        self.maintenance_table.setRowCount(0)
        t = Theme.get()
        priority_colors = {"High": t['red'], "Medium": t['accent'], "Low": t['green']}
        status_colors   = {"Pending": t['accent'], "In Progress": t['blue'], "Completed": t['green']}
        for i, r in enumerate(requests):
            self._set_table_row(self.maintenance_table, i, [
                r['request_id'], r['room_number'], r['renter_name'],
                r['description'], r['priority'], r['status'], str(r['request_date'])
            ])
            self.maintenance_table.item(i, 4).setForeground(QColor(priority_colors.get(r['priority'], t['text'])))
            self.maintenance_table.item(i, 5).setForeground(QColor(status_colors.get(r['status'], t['text'])))

    def _filter_maintenance(self):
        requests = self._get_all_maintenance()
        kw = self.maint_search.text().strip().lower() if hasattr(self, 'maint_search') else ""
        sf = self.maint_status_filter.currentText() if hasattr(self, 'maint_status_filter') else "All"
        pf = self.maint_priority_filter.currentText() if hasattr(self, 'maint_priority_filter') else "All Priorities"
        if kw:
            requests = [r for r in requests if
                        kw in str(r.get('room_number', '')).lower() or
                        kw in str(r.get('description', '')).lower() or
                        kw in str(r.get('renter_name', '')).lower()]
        if sf != "All":
            requests = [r for r in requests if r.get('status') == sf]
        if pf != "All Priorities":
            requests = [r for r in requests if r.get('priority') == pf]
        self._display_maintenance(requests)
        self._update_maintenance_stats(requests)

    def _view_maintenance(self):
        row = self.maintenance_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a request.")
            return
        request_id = int(self.maintenance_table.item(row, 0).text())
        requests = self._get_all_maintenance()
        req = next((r for r in requests if r['request_id'] == request_id), None)
        if req:
            dlg = MaintenanceDetailDialog(self, req)
            dlg.exec()

    def _mark_maintenance_in_progress(self):
        row = self.maintenance_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a request.")
            return
        request_id = int(self.maintenance_table.item(row, 0).text())
        try:
            ok = self.maintenance_db.update_status(request_id, "In Progress", "", None)
            if ok:
                self.load_maintenance()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def open_add_maintenance_dialog(self):
        rooms   = self.room_db.get_all_rooms()
        renters = self.renter_db.get_all_renters()
        dlg = MaintenanceDialog(self, rooms, renters)
        if dlg.exec():
            data = dlg.get_data()
            ok = self.maintenance_db.add_request(**data)
            if ok:
                if self.current_user and self.current_user.get('admin_id'):
                    self.admin_db.add_log(self.current_user['admin_id'], 'ADD_MAINTENANCE',
                                          f"Maintenance request added for room {data['room_id']}")
                QMessageBox.information(self, "Success", "Request added!")
                self.load_maintenance()
            else:
                QMessageBox.critical(self, "Error", "Failed to add request.")

    def resolve_maintenance(self):
        row = self.maintenance_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a request.")
            return
        request_id = int(self.maintenance_table.item(row, 0).text())
        ok = self.maintenance_db.update_status(request_id, "Completed",
                                               "Resolved by admin.",
                                               QDate.currentDate().toString("yyyy-MM-dd"))
        if ok:
            if self.current_user and self.current_user.get('admin_id'):
                self.admin_db.add_log(self.current_user['admin_id'], 'RESOLVE_MAINTENANCE',
                                      f"Resolved request ID {request_id}")
            self.load_maintenance()

    def delete_maintenance(self):
        row = self.maintenance_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a request.")
            return
        request_id = int(self.maintenance_table.item(row, 0).text())
        reply = QMessageBox.question(self, "Confirm", "Delete this request?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            ok = self.maintenance_db.delete_request(request_id)
            if ok:
                self.load_maintenance()

    # ══════════════════════════════════════════
    #  VISITORS PAGE
    # ══════════════════════════════════════════
    def _build_visitors_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addWidget(page_header("Visitor Logs", "  Log Visitor In", self.open_add_visitor_dialog, btn_icon="fa5s.sign-in-alt"))
        layout.addSpacing(10)
        self.visitors_table = self._make_table(
            ["ID", "Visitor Name", "Relationship", "Visiting Renter", "Time In", "Time Out"]
        )
        layout.addWidget(self.visitors_table)
        btn_row = QHBoxLayout()
        out_btn = make_btn("  Log Out",  T("blue"), "white", icon="fa5s.sign-out-alt", icon_color="white")
        self.visitor_delete_btn = make_btn("  Delete", T("red"), "white", icon="fa5s.trash-alt", icon_color="white")
        out_btn.clicked.connect(self.log_visitor_out)
        self.visitor_delete_btn.clicked.connect(self.delete_visitor)
        btn_row.addStretch()
        btn_row.addWidget(out_btn)
        btn_row.addWidget(self.visitor_delete_btn)
        layout.addLayout(btn_row)
        return page

    def load_visitors(self):
        visitors = self.visitor_db.get_all_visitors()
        self.visitors_table.setRowCount(0)
        for i, v in enumerate(visitors):
            self._set_table_row(self.visitors_table, i, [
                v['visitor_id'], v['visitor_name'], v['relationship'],
                v['renter_name'], str(v['time_in']),
                str(v['time_out']) if v['time_out'] else "Still In"
            ])
            t = Theme.get()
            if not v.get('time_out'):
                self.visitors_table.item(i, 5).setForeground(QColor(t['green']))

    def open_add_visitor_dialog(self):
        renters = self.renter_db.get_all_renters()
        dlg = VisitorDialog(self, renters)
        if dlg.exec():
            data = dlg.get_data()
            ok = self.visitor_db.log_visitor_in(**data)
            if ok:
                self.load_visitors()

    def log_visitor_out(self):
        row = self.visitors_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a visitor.")
            return
        visitor_id = int(self.visitors_table.item(row, 0).text())
        from datetime import datetime
        ok = self.visitor_db.log_visitor_out(visitor_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if ok:
            self.load_visitors()

    def delete_visitor(self):
        row = self.visitors_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a visitor.")
            return
        visitor_id = int(self.visitors_table.item(row, 0).text())
        reply = QMessageBox.question(self, "Confirm", "Delete this visitor log?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            ok = self.visitor_db.delete_visitor_log(visitor_id)
            if ok:
                self.load_visitors()

    # ══════════════════════════════════════════
    #  ACTIVITY LOGS PAGE
    # ══════════════════════════════════════════
    # ══════════════════════════════════════════
    #  MY PROFILE PAGE  (all roles)
    # ══════════════════════════════════════════
    def _build_profile_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        layout.addWidget(page_header("My Profile"))

        # ── Profile card ──────────────────────
        top_card = self._card_frame()
        top_card.setFixedHeight(160)
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(24, 24, 24, 24)
        top_layout.setSpacing(20)

        self.profile_avatar = AvatarWidget("?", 100)
        top_layout.addWidget(self.profile_avatar)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        self.profile_name_lbl = QLabel("—")
        self.profile_name_lbl.setStyleSheet(f"color: {T('text')}; font-size: 22px; font-weight: bold; background: transparent; border: none;")
        self.profile_role_lbl = QLabel("—")
        self.profile_role_lbl.setStyleSheet(f"color: {T('accent')}; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        self.profile_user_lbl = QLabel("—")
        self.profile_user_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px; background: transparent; border: none;")
        info_col.addWidget(self.profile_name_lbl)
        info_col.addWidget(self.profile_role_lbl)
        info_col.addWidget(self.profile_user_lbl)
        info_col.addStretch()

        top_layout.addLayout(info_col)
        top_layout.addStretch()

        change_pic_btn = make_btn("  Change Photo", T("blue"), "white", icon="fa5s.camera", icon_color="white")
        change_pic_btn.clicked.connect(self._profile_change_photo)
        top_layout.addWidget(change_pic_btn, alignment=Qt.AlignBottom)
        layout.addWidget(top_card)

        # ── Edit info form ──────────────────
        edit_card = self._card_frame()
        edit_layout = QVBoxLayout(edit_card)
        edit_layout.setContentsMargins(24, 24, 24, 24)
        edit_layout.setSpacing(14)

        edit_hdr = QLabel("Edit Profile Information")
        edit_hdr.setStyleSheet(f"color: {T('text')}; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        edit_layout.addWidget(edit_hdr)

        form_grid = QGridLayout()
        form_grid.setSpacing(10)

        def mk_lbl(txt):
            l = QLabel(txt)
            l.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px; background: transparent; border: none;")
            return l

        def mk_inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        self.prof_fullname   = mk_inp("Full Name")
        self.prof_email      = mk_inp("Email")
        self.prof_contact    = mk_inp("Contact Number")

        form_grid.addWidget(mk_lbl("Full Name"),       0, 0)
        form_grid.addWidget(self.prof_fullname,         0, 1)
        form_grid.addWidget(mk_lbl("Email"),           1, 0)
        form_grid.addWidget(self.prof_email,            1, 1)
        form_grid.addWidget(mk_lbl("Contact No."),     2, 0)
        form_grid.addWidget(self.prof_contact,          2, 1)
        edit_layout.addLayout(form_grid)

        save_info_btn = make_btn("  Save Changes", T("green"), "white", icon="fa5s.save", icon_color="white", width=160)
        save_info_btn.clicked.connect(self._profile_save_info)
        edit_layout.addWidget(save_info_btn, alignment=Qt.AlignRight)
        layout.addWidget(edit_card)

        # ── Change password ──────────────────
        pw_card = self._card_frame()
        pw_layout = QVBoxLayout(pw_card)
        pw_layout.setContentsMargins(24, 24, 24, 24)
        pw_layout.setSpacing(14)

        pw_hdr = QLabel("Change Password")
        pw_hdr.setStyleSheet(f"color: {T('text')}; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        pw_layout.addWidget(pw_hdr)

        pw_grid = QGridLayout()
        pw_grid.setSpacing(10)
        self.prof_old_pw  = mk_inp("Current Password")
        self.prof_old_pw.setEchoMode(QLineEdit.Password)
        self.prof_new_pw  = mk_inp("New Password")
        self.prof_new_pw.setEchoMode(QLineEdit.Password)
        self.prof_new_pw2 = mk_inp("Confirm New Password")
        self.prof_new_pw2.setEchoMode(QLineEdit.Password)

        pw_grid.addWidget(mk_lbl("Current Password"),  0, 0)
        pw_grid.addWidget(self.prof_old_pw,             0, 1)
        pw_grid.addWidget(mk_lbl("New Password"),       1, 0)
        pw_grid.addWidget(self.prof_new_pw,             1, 1)
        pw_grid.addWidget(mk_lbl("Confirm Password"),   2, 0)
        pw_grid.addWidget(self.prof_new_pw2,            2, 1)
        pw_layout.addLayout(pw_grid)

        save_pw_btn = make_btn("  Update Password", T("orange"), "white", icon="fa5s.lock", icon_color="white", width=180)
        save_pw_btn.clicked.connect(self._profile_save_password)
        pw_layout.addWidget(save_pw_btn, alignment=Qt.AlignRight)
        layout.addWidget(pw_card)

        # ── Payroll section (staff/admin only) ──
        self.payroll_card = self._card_frame()
        payroll_layout = QVBoxLayout(self.payroll_card)
        payroll_layout.setContentsMargins(24, 24, 24, 24)
        payroll_layout.setSpacing(14)

        pay_hdr = QLabel("My Monthly Salary Records")
        pay_hdr.setStyleSheet(f"color: {T('text')}; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        payroll_layout.addWidget(pay_hdr)

        self.payroll_table = self._make_table([
            "Period", "Basic Salary", "Allowances", "Deductions", "Net Pay", "Pay Date", "Method"
        ])
        self.payroll_table.setMaximumHeight(220)
        payroll_layout.addWidget(self.payroll_table)

        # Summary row
        self.payroll_summary_lbl = QLabel("")
        self.payroll_summary_lbl.setStyleSheet(f"color: {T('green')}; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        payroll_layout.addWidget(self.payroll_summary_lbl)
        layout.addWidget(self.payroll_card)

        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    def load_profile(self):
        if not self.current_user:
            return
        role = self.current_user.get('role', '')
        name = self.current_user.get('full_name', '?')
        username = self.current_user.get('username', '—')

        self.profile_avatar.set_avatar(name)
        self.profile_name_lbl.setText(name)
        self.profile_role_lbl.setText(role)
        self.profile_user_lbl.setText(f"@{username}")

        # Show/hide payroll card
        is_staff_role = role in ('Admin', 'Staff', 'Maintenance', 'Security')
        self.payroll_card.setVisible(is_staff_role)

        if role == 'Renter':
            renter_id = self.current_user.get('renter_id')
            if renter_id:
                try:
                    prof_mod = database.ProfileModule()
                    data = prof_mod.get_renter_profile(renter_id)
                    if data:
                        self.prof_fullname.setText(f"{data.get('first_name','')} {data.get('last_name','')}".strip())
                        self.prof_email.setText(data.get('email') or '')
                        self.prof_contact.setText(data.get('contact_number') or '')
                        pic = data.get('profile_pic_path') or ''
                        if pic and os.path.exists(pic):
                            self.profile_avatar.set_avatar(name, pic)
                except Exception as e:
                    print(f"[load_profile renter] {e}")
        else:
            admin_id = self.current_user.get('admin_id')
            if admin_id:
                try:
                    prof_mod = database.ProfileModule()
                    data = prof_mod.get_admin_profile(admin_id)
                    if data:
                        self.prof_fullname.setText(data.get('full_name') or '')
                        self.prof_email.setText(data.get('email') or '')
                        self.prof_contact.setText(data.get('contact_number') or '')
                        pic = data.get('profile_pic_path') or ''
                        if pic and os.path.exists(pic):
                            self.profile_avatar.set_avatar(name, pic)
                except Exception as e:
                    print(f"[load_profile admin] {e}")

            # Load payroll
            if is_staff_role and admin_id:
                try:
                    pay_mod = database.PayrollModule()
                    pay_mod.setup_table()
                    records = pay_mod.get_payroll_for_admin(admin_id)
                    self.payroll_table.setRowCount(0)
                    total_net = 0.0
                    for i, rec in enumerate(records):
                        net = float(rec.get('net_pay') or 0)
                        total_net += net
                        self._set_table_row(self.payroll_table, i, [
                            rec.get('period_month', '—'),
                            f"₱{float(rec.get('basic_salary',0)):,.2f}",
                            f"₱{float(rec.get('allowances',0)):,.2f}",
                            f"₱{float(rec.get('deductions',0)):,.2f}",
                            f"₱{net:,.2f}",
                            str(rec.get('payment_date') or '—')[:10],
                            rec.get('payment_method', '—'),
                        ])
                    self.payroll_summary_lbl.setText(f"Total net pay received: ₱{total_net:,.2f}")
                except Exception as e:
                    print(f"[load_profile payroll] {e}")

    def _profile_change_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose Profile Photo", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if not path:
            return
        role = self.current_user.get('role', '') if self.current_user else ''
        name = self.current_user.get('full_name', '?') if self.current_user else '?'
        try:
            prof_mod = database.ProfileModule()
            if role == 'Renter':
                renter_id = self.current_user.get('renter_id')
                prof_mod.update_renter_profile(renter_id, profile_pic_path=path)
            else:
                admin_id = self.current_user.get('admin_id')
                prof_mod.update_admin_profile(admin_id, full_name=name, profile_pic_path=path)
            self.profile_avatar.set_avatar(name, path)
            self.sidebar_avatar.set_avatar(name, path)
            QMessageBox.information(self, "Updated", "Profile photo updated!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update photo: {e}")

    def _profile_save_info(self):
        if not self.current_user:
            return
        full_name = self.prof_fullname.text().strip()
        email     = self.prof_email.text().strip()
        contact   = self.prof_contact.text().strip()
        if not full_name:
            QMessageBox.warning(self, "Required", "Full name cannot be empty.")
            return
        role = self.current_user.get('role', '')
        try:
            prof_mod = database.ProfileModule()
            if role == 'Renter':
                renter_id = self.current_user.get('renter_id')
                prof_mod.update_renter_profile(renter_id, email=email, contact_number=contact)
            else:
                admin_id = self.current_user.get('admin_id')
                prof_mod.update_admin_profile(admin_id, full_name=full_name, email=email, contact_number=contact)
                self.current_user['full_name'] = full_name
                self.sidebar_user_lbl.setText(full_name[:22])
                self.sidebar_avatar.set_avatar(full_name)
                self.welcome_label.setText(
                    f'Hello, <span style="color:{T("accent")};">{full_name}</span>! '
                    f'<span style="color:{T("text_muted")}; font-size:14px;">({role})</span>'
                )
                self.profile_name_lbl.setText(full_name)
            QMessageBox.information(self, "Saved", "Profile information updated!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save: {e}")

    def _profile_save_password(self):
        if not self.current_user:
            return
        old_pw  = self.prof_old_pw.text()
        new_pw  = self.prof_new_pw.text()
        new_pw2 = self.prof_new_pw2.text()
        if not old_pw or not new_pw:
            QMessageBox.warning(self, "Required", "Please fill in all password fields.")
            return
        if new_pw != new_pw2:
            QMessageBox.warning(self, "Mismatch", "New passwords do not match.")
            return
        if len(new_pw) < 6:
            QMessageBox.warning(self, "Too Short", "New password must be at least 6 characters.")
            return
        role = self.current_user.get('role', '')
        try:
            prof_mod = database.ProfileModule()
            if role == 'Renter':
                result = prof_mod.change_renter_password(self.current_user.get('renter_id'), old_pw, new_pw)
            else:
                result = prof_mod.change_admin_password(self.current_user.get('admin_id'), old_pw, new_pw)
            if result == 'wrong_password':
                QMessageBox.warning(self, "Wrong Password", "Current password is incorrect.")
            elif result:
                self.prof_old_pw.clear()
                self.prof_new_pw.clear()
                self.prof_new_pw2.clear()
                QMessageBox.information(self, "Updated", "Password changed successfully!")
            else:
                QMessageBox.critical(self, "Error", "Could not update password.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {e}")

    def _build_logs_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addWidget(page_header("Activity Logs"))
        layout.addSpacing(10)
        self.logs_table = self._make_table(["Log ID", "Admin", "Action", "Details", "Timestamp"])
        layout.addWidget(self.logs_table)
        return page

    def load_logs(self):
        logs = self.admin_db.get_activity_logs()
        self.logs_table.setRowCount(0)
        for i, log in enumerate(logs):
            self._set_table_row(self.logs_table, i, [
                log['log_id'], log['admin_name'],
                log['action_type'], log['action_text'],
                str(log['log_timestamp'])
            ])


# ─────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────
class DormNormApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DormNorm")
        self.setMinimumSize(1200, 750)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.welcome   = WelcomePage(self.stack)
        self.login     = LoginPage(self.stack)
        self.dashboard = DashboardPage(self.stack)

        self.stack.addWidget(self.welcome)
        self.stack.addWidget(self.login)
        self.stack.addWidget(self.dashboard)
        self.stack.setCurrentIndex(0)

    def fade_to_page(self, index):
        self.anim = QPropertyAnimation(self.stack, b"windowOpacity")
        self.anim.setDuration(350)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)

        def change_page():
            self.stack.setCurrentIndex(index)
            self.anim2 = QPropertyAnimation(self.stack, b"windowOpacity")
            self.anim2.setDuration(350)
            self.anim2.setStartValue(0.0)
            self.anim2.setEndValue(1.0)
            self.anim2.start()

        self.anim.finished.connect(change_page)
        self.anim.start()


if __name__ == "__main__":
    # ── Auto-migrate plaintext passwords on first run ──
    try:
        _am = database.AdminModule()
        _am.hash_existing_admin_passwords()
        _rm = database.RenterModule()
        _rm.hash_existing_renter_passwords()
        # Ensure extra admin columns exist (email, contact_number, profile_pic_path)
        _conn = _am.connect()
        if _conn:
            _cur = _conn.cursor()
            for _col, _typ in [
                ("email",           "VARCHAR(150)"),
                ("contact_number",  "VARCHAR(30)"),
                ("profile_pic_path","VARCHAR(255)"),
            ]:
                try:
                    _cur.execute(f"ALTER TABLE admins ADD COLUMN IF NOT EXISTS `{_col}` {_typ} DEFAULT NULL")
                except Exception:
                    pass
            _conn.commit()
            _conn.close()
    except Exception as _e:
        print(f"[Startup migration] {_e}")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = DormNormApp()
    window.showMaximized()
    sys.exit(app.exec())