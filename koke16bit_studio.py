"""
Koke16-Bit Studio
=================
A professional-grade 16-bit DAW with the revolutionary "Hum to Music" workflow.
Single-file, fully responsive PyQt6 application.
"""

import sys
import math
import random
import wave
import numpy as np
try:
    import pygame
    import pygame.mixer
except ImportError:
    pygame = None  # type: ignore
try:
    import sounddevice as sd
except ImportError:
    sd = None  # type: ignore
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QSlider,
    QHBoxLayout, QVBoxLayout, QGridLayout, QFrame, QScrollArea,
    QSizePolicy, QSpacerItem, QGraphicsDropShadowEffect,
    QDialog, QProgressBar, QStackedWidget, QButtonGroup,
    QRadioButton, QComboBox, QLineEdit, QFileDialog
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal,
    QRect, QPoint, QSize, QThread, pyqtProperty
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QFontDatabase,
    QLinearGradient, QPainterPath, QPolygon, QRadialGradient
)

# ─────────────────────────────────────────────────────────────────────────────
#  QSS  ─  Global Stylesheet
# ─────────────────────────────────────────────────────────────────────────────
GLOBAL_QSS = """
/* ── Base ── */
QMainWindow, QWidget {
    background-color: #0e0e0e;
    color: #e0e0e0;
    font-family: 'Segoe UI', 'Arial', sans-serif;
}

/* ── Scrollbars ── */
QScrollBar:vertical {
    background: #1a1a1a;
    width: 8px;
    margin: 0;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #00ffc8;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #1a1a1a;
    height: 8px;
    margin: 0;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #00ffc8;
    min-width: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Header ── */
#headerBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                from: #0a0a0a, stop: 0.5 #111111, to: #0a0a0a);
    border-bottom: 2px solid #00ffc8;
}

/* ── App Title ── */
#appTitle {
    color: #00ffc8;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 3px;
}
#appSubtitle {
    color: #555555;
    font-size: 10px;
    letter-spacing: 5px;
    font-weight: 400;
}

/* ── Transport Buttons ── */
QPushButton#transportBtn {
    background-color: #1e1e1e;
    color: #cccccc;
    border: 1px solid #333333;
    border-radius: 8px;
    font-size: 18px;
    padding: 6px 14px;
    min-width: 48px;
    min-height: 48px;
}
QPushButton#transportBtn:hover {
    background-color: #2a2a2a;
    border-color: #00ffc8;
    color: #00ffc8;
}
QPushButton#transportBtn:pressed {
    background-color: #003322;
    border-color: #00ffc8;
}
QPushButton#transportBtn[active="true"] {
    background-color: #003322;
    border-color: #00ffc8;
    color: #00ffc8;
}
QPushButton#recordBtn {
    background-color: #2a0000;
    color: #ff4444;
    border: 1px solid #551111;
    border-radius: 8px;
    font-size: 18px;
    padding: 6px 14px;
    min-width: 48px;
    min-height: 48px;
}
QPushButton#recordBtn:hover {
    background-color: #3a0000;
    border-color: #ff4444;
}
QPushButton#recordBtn[recording="true"] {
    background-color: #ff2222;
    color: #ffffff;
    border-color: #ff8888;
}

/* ── BPM Display ── */
#bpmFrame {
    background-color: #0a0a0a;
    border: 1px solid #00ffc8;
    border-radius: 6px;
    padding: 4px 10px;
}
#bpmValue {
    color: #00ffc8;
    font-size: 28px;
    font-weight: 700;
    font-family: 'Courier New', monospace;
    letter-spacing: 4px;
}
#bpmLabel {
    color: #666666;
    font-size: 9px;
    letter-spacing: 4px;
    font-weight: 600;
}

/* ── Sidebar ── */
#resourceSidebar {
    background-color: #111111;
    border-right: 1px solid #222222;
    min-width: 180px;
    max-width: 240px;
}
#sidebarTitle {
    color: #888888;
    font-size: 9px;
    letter-spacing: 3px;
    font-weight: 700;
    padding: 8px 12px 4px 12px;
    border-bottom: 1px solid #1e1e1e;
}

/* ── Sample Bank Items ── */
QPushButton#sampleItem {
    background-color: #181818;
    color: #cccccc;
    border: 1px solid #2a2a2a;
    border-left: 3px solid #00ffc8;
    border-radius: 4px;
    text-align: left;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 500;
    margin: 2px 6px;
}
QPushButton#sampleItem:hover {
    background-color: #202020;
    border-left-color: #00ffff;
    color: #00ffc8;
}
QPushButton#sampleItem:checked {
    background-color: #0a1f1a;
    border-left-color: #00ffc8;
    color: #00ffc8;
}
QPushButton#sampleItem[category="bass"] { border-left-color: #8844ff; }
QPushButton#sampleItem[category="perc"] { border-left-color: #ff6644; }
QPushButton#sampleItem[category="pad"]  { border-left-color: #4488ff; }
QPushButton#sampleItem[category="lead"] { border-left-color: #00ffc8; }
QPushButton#sampleItem[category="fx"]   { border-left-color: #ffcc00; }

/* ── Track Header ── */
#trackHeader {
    background-color: #161616;
    border-right: 1px solid #282828;
    border-bottom: 1px solid #1e1e1e;
    min-width: 180px;
    max-width: 180px;
    padding: 0 6px;
}
#trackLabel {
    color: #d0d0d0;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#muteBtn {
    background-color: #222222;
    color: #888888;
    border: 1px solid #333333;
    border-radius: 3px;
    font-size: 9px;
    font-weight: 700;
    padding: 2px 5px;
    max-width: 28px;
    max-height: 20px;
}
QPushButton#muteBtn:checked {
    background-color: #ffaa00;
    color: #000000;
    border-color: #ffcc44;
}
QPushButton#soloBtn {
    background-color: #222222;
    color: #888888;
    border: 1px solid #333333;
    border-radius: 3px;
    font-size: 9px;
    font-weight: 700;
    padding: 2px 5px;
    max-width: 28px;
    max-height: 20px;
}
QPushButton#soloBtn:checked {
    background-color: #00ffc8;
    color: #000000;
    border-color: #00ffff;
}

/* ── Volume Slider ── */
QSlider#volSlider::groove:horizontal {
    background: #2a2a2a;
    height: 4px;
    border-radius: 2px;
}
QSlider#volSlider::handle:horizontal {
    background: #00ffc8;
    width: 10px;
    height: 10px;
    border-radius: 5px;
    margin: -3px 0;
}
QSlider#volSlider::sub-page:horizontal {
    background: #00ffc8;
    border-radius: 2px;
}

/* ── Timeline Canvas ── */
#timelineCanvas {
    background-color: #0e0e0e;
}
#arrangementArea {
    background-color: #0e0e0e;
    border-bottom: 1px solid #1e1e1e;
}

/* ── Hum Footer ── */
#humFooter {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                from: #0a0a0a, to: #060f0c);
    border-top: 2px solid #00ffc8;
    min-height: 130px;
    max-height: 160px;
}
#humTitle {
    color: #00ffc8;
    font-size: 10px;
    letter-spacing: 5px;
    font-weight: 700;
}
QPushButton#humBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                from: #00443a, to: #001a14);
    color: #00ffc8;
    border: 2px solid #00ffc8;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 10px 24px;
    min-width: 180px;
    min-height: 52px;
}
QPushButton#humBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                from: #00665a, to: #002a1e);
    border-color: #00ffee;
    color: #ffffff;
}
QPushButton#humBtn[active="true"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                from: #660000, to: #330000);
    border-color: #ff2222;
    color: #ff4444;
}

/* ── Status Bar ── */
#statusBar {
    background-color: #0a0a0a;
    border-top: 1px solid #1a1a1a;
    padding: 0 12px;
}
#statusText {
    color: #555555;
    font-size: 10px;
    letter-spacing: 1px;
}
#statusIndicator {
    color: #00ffc8;
    font-size: 10px;
}
"""

# ─────────────────────────────────────────────────────────────────────────────
#  Waveform Visualizer Widget
# ─────────────────────────────────────────────────────────────────────────────
class WaveformVisualizer(QWidget):
    """Real-time waveform display with animated idle / active states."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._phase = 0.0
        self._amplitude = 0.05        # 0.0 – 1.0
        self._active = False
        self._bars: list[float] = [0.0] * 64

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)         # ~30 fps

    # ── public API ──────────────────────────────────────────────────────────
    def set_active(self, active: bool) -> None:
        self._active = active
        self._amplitude = 0.05 if not active else 0.0

    def push_amplitude(self, amp: float) -> None:
        self._amplitude = max(0.0, min(1.0, amp))

    # ── internals ───────────────────────────────────────────────────────────
    def _tick(self) -> None:
        self._phase += 0.08
        if self._active:
            self._amplitude = min(1.0, self._amplitude + random.uniform(-0.04, 0.08))
            self._amplitude = max(0.15, self._amplitude)
        else:
            self._amplitude = max(0.05, self._amplitude * 0.97)

        for i in range(len(self._bars)):
            target = (
                math.sin(self._phase + i * 0.35) * 0.4 +
                math.sin(self._phase * 1.7 + i * 0.22) * 0.3 +
                (random.uniform(-1, 1) * 0.3 if self._active else 0.0)
            ) * self._amplitude
            self._bars[i] += (target - self._bars[i]) * 0.25

        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        mid = h / 2

        # background
        painter.fillRect(0, 0, w, h, QColor("#060f0c"))

        # grid line
        painter.setPen(QPen(QColor("#0a2018"), 1))
        painter.drawLine(0, int(mid), w, int(mid))

        if len(self._bars) == 0:
            return

        bar_w = w / len(self._bars)
        base_color = QColor("#ff2222") if self._active else QColor("#00ffc8")

        for i, val in enumerate(self._bars):
            bar_h = abs(val) * (mid * 0.9)
            x = i * bar_w
            y = mid - bar_h if val >= 0 else mid

            # colour gradient per amplitude
            alpha = int(120 + abs(val) * 135)
            c = QColor(base_color)
            c.setAlpha(alpha)

            gradient = QLinearGradient(x, y, x, y + bar_h * 2)
            c2 = QColor(c)
            c2.setAlpha(30)
            gradient.setColorAt(0.0, c)
            gradient.setColorAt(1.0, c2)

            painter.fillRect(
                int(x), int(mid - bar_h),
                max(1, int(bar_w - 1)), int(bar_h * 2),
                gradient
            )

        # top scan line
        painter.setPen(QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), 60), 1))
        painter.drawLine(0, 0, w, 0)
        painter.drawLine(0, h - 1, w, h - 1)

        painter.end()


# ─────────────────────────────────────────────────────────────────────────────
#  BPM Display
# ─────────────────────────────────────────────────────────────────────────────
class BPMDisplay(QFrame):
    bpm_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bpmFrame")
        self._bpm = 120
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(0)

        self._value_lbl = QLabel(f"{self._bpm:03d}")
        self._value_lbl.setObjectName("bpmValue")
        self._value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel("BPM")
        lbl.setObjectName("bpmLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        for delta, sym in [(-1, "−"), (+1, "+")]:
            b = QPushButton(sym)
            b.setObjectName("transportBtn")
            b.setFixedSize(24, 24)
            b.setStyleSheet("font-size:14px; min-width:24px; min-height:24px;")
            b.clicked.connect(lambda _, d=delta: self._change(d))
            btn_row.addWidget(b)

        layout.addWidget(self._value_lbl)
        layout.addWidget(lbl)
        layout.addLayout(btn_row)

    def _change(self, delta: int):
        self._bpm = max(40, min(300, self._bpm + delta))
        self._value_lbl.setText(f"{self._bpm:03d}")
        self.bpm_changed.emit(self._bpm)

    @property
    def bpm(self):
        return self._bpm


# ─────────────────────────────────────────────────────────────────────────────
#  Transport Controls
# ─────────────────────────────────────────────────────────────────────────────
class TransportControls(QWidget):
    play_toggled = pyqtSignal(bool)
    stop_clicked = pyqtSignal()
    record_toggled = pyqtSignal(bool)
    loop_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playing = False
        self._recording = False
        self._looping = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._play_btn = self._mk_btn("▶", "transportBtn", self._toggle_play)
        self._stop_btn = self._mk_btn("■", "transportBtn", self._stop)
        self._rec_btn  = self._mk_btn("⏺", "recordBtn",    self._toggle_rec)
        self._loop_btn = self._mk_btn("⟳", "transportBtn", self._toggle_loop)
        self._rew_btn  = self._mk_btn("⏮", "transportBtn", lambda: None)
        self._ffw_btn  = self._mk_btn("⏭", "transportBtn", lambda: None)

        for w in [self._rew_btn, self._play_btn, self._stop_btn,
                  self._rec_btn, self._loop_btn, self._ffw_btn]:
            layout.addWidget(w)

    @staticmethod
    def _mk_btn(text, obj_name, slot):
        b = QPushButton(text)
        b.setObjectName(obj_name)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(slot)
        return b

    def _toggle_play(self):
        self._playing = not self._playing
        self._play_btn.setText("⏸" if self._playing else "▶")
        self._play_btn.setProperty("active", self._playing)
        self._play_btn.style().unpolish(self._play_btn)
        self._play_btn.style().polish(self._play_btn)
        self.play_toggled.emit(self._playing)

    def _stop(self):
        if self._playing:
            self._toggle_play()
        self.stop_clicked.emit()

    def _toggle_rec(self):
        self._recording = not self._recording
        self._rec_btn.setProperty("recording", self._recording)
        self._rec_btn.style().unpolish(self._rec_btn)
        self._rec_btn.style().polish(self._rec_btn)
        self.record_toggled.emit(self._recording)

    def _toggle_loop(self):
        self._looping = not self._looping
        self._loop_btn.setProperty("active", self._looping)
        self._loop_btn.style().unpolish(self._loop_btn)
        self._loop_btn.style().polish(self._loop_btn)
        self.loop_toggled.emit(self._looping)


# ─────────────────────────────────────────────────────────────────────────────
#  MIDI Block  ─  draggable block on a track lane
# ─────────────────────────────────────────────────────────────────────────────
class MidiBlock(QWidget):
    COLORS = {
        "Lead":       ("#00ffc8", "#003322"),
        "Bass":       ("#8844ff", "#1a0040"),
        "Percussion": ("#ff6644", "#330e00"),
        "Pads":       ("#4488ff", "#001033"),
        "FX":         ("#ffcc00", "#332200"),
        "Hum":        ("#ff2222", "#330000"),
    }

    def __init__(self, track_name: str, label: str = "MIDI", width: int = 160,
                 hum_generated: bool = False, parent=None):
        super().__init__(parent)
        self._track = track_name
        self._label = label
        self._hum = hum_generated
        fg, bg = self.COLORS.get(track_name, ("#00ffc8", "#003322"))
        self._fg = QColor(fg)
        self._bg = QColor(bg)
        self.setFixedSize(width, 54)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self._drag_origin: QPoint | None = None
        self._orig_x = 0

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # body
        path = QPainterPath()
        path.addRoundedRect(1, 1, w - 2, h - 2, 5, 5)

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, self._bg.lighter(140))
        grad.setColorAt(1, self._bg)
        p.fillPath(path, grad)

        # border
        p.setPen(QPen(self._fg, 1.5))
        p.drawPath(path)

        # top accent bar
        accent = QPainterPath()
        accent.addRoundedRect(1, 1, w - 2, 4, 2, 2)
        p.fillPath(accent, QBrush(self._fg))

        # label
        p.setPen(self._fg)
        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QRect(6, 6, w - 12, h - 12), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, self._label)

        # waveform squiggle
        p.setPen(QPen(self._fg.lighter(120), 1, Qt.PenStyle.SolidLine))
        prev_x, prev_y = 0, h // 2
        for x in range(0, w, 3):
            y = int(h / 2 + math.sin(x * 0.22 + (hash(self._label) % 10)) * (h * 0.22))
            if x > 0:
                p.drawLine(prev_x, prev_y, x, y)
            prev_x, prev_y = x, y

        if self._hum:
            p.setFont(QFont("Segoe UI", 7))
            p.setPen(QColor("#ffffff88"))
            p.drawText(QRect(6, h - 18, w - 12, 16),
                       Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, "♪ HUM")

        p.end()

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint()
            self._orig_x = self.x()

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._drag_origin is not None:
            delta = event.globalPosition().toPoint().x() - self._drag_origin.x()
            new_x = max(0, self._orig_x + delta)
            self.move(new_x, self.y())

    def mouseReleaseEvent(self, event):  # noqa: N802
        self._drag_origin = None


class StepLaneCanvas(QWidget):
    STEPS = 16
    PITCH_ROWS = 4

    def __init__(self, lane, parent=None):
        super().__init__(parent)
        self._lane = lane
        self.setObjectName("arrangementArea")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _note_for_row(self, row: int) -> int:
        row = max(0, min(self.PITCH_ROWS - 1, row))
        if self._lane.category == "perc":
            drum_notes = [46, 42, 38, 36]
            return drum_notes[row]
        return self._lane._base_note + (self.PITCH_ROWS - 1 - row) * 2

    def _row_for_note(self, note: int) -> int:
        if self._lane.category == "perc":
            drum_notes = [46, 42, 38, 36]
            return drum_notes.index(note) if note in drum_notes else self.PITCH_ROWS - 1
        row = self.PITCH_ROWS - 1 - int((note - self._lane._base_note) / 2)
        return max(0, min(self.PITCH_ROWS - 1, row))

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        w, h = max(1, self.width()), max(1, self.height())
        col = int((event.position().x() / w) * self.STEPS)
        row = int((event.position().y() / h) * self.PITCH_ROWS)
        col = max(0, min(self.STEPS - 1, col))
        target_note = self._note_for_row(row)
        self._lane._step_notes[col] = 0 if self._lane._step_notes[col] > 0 else target_note
        self.update()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        p.fillRect(0, 0, w, h, QColor("#0e0e0e"))

        step_w = w / self.STEPS
        row_h = h / self.PITCH_ROWS

        for r in range(self.PITCH_ROWS + 1):
            y = int(r * row_h)
            p.setPen(QPen(QColor("#202020"), 1))
            p.drawLine(0, y, w, y)

        for i in range(self.STEPS + 1):
            x = int(i * step_w)
            strong = (i % 4 == 0)
            p.setPen(QPen(QColor("#383838" if strong else "#222222"), 1))
            p.drawLine(x, 0, x, h)

        if self._lane._active_step >= 0:
            x = int(self._lane._active_step * step_w)
            p.fillRect(x, 0, int(step_w), h, QColor("#00ffc81f"))

        accent = QColor(self._lane._accent)
        for i, note in enumerate(self._lane._step_notes):
            if note <= 0:
                continue
            row = self._row_for_note(note)
            x = int(i * step_w) + 2
            y = int(row * row_h) + 2
            rw = max(6, int(step_w) - 4)
            rh = max(6, int(row_h) - 4)

            p.setPen(QPen(accent, 1))
            p.setBrush(QBrush(QColor(accent.red(), accent.green(), accent.blue(), 140)))
            p.drawRoundedRect(x, y, rw, rh, 3, 3)

        if not any(n > 0 for n in self._lane._step_notes):
            p.setPen(QColor("#444444"))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(
                QRect(0, 0, w, h),
                Qt.AlignmentFlag.AlignCenter,
                "Click to plot notes"
            )

        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  Track Lane  (header + canvas)
# ─────────────────────────────────────────────────────────────────────────────
class TrackLane(QWidget):
    TRACK_HEIGHT = 66

    def __init__(self, name: str, color_key: str, index: int, parent=None):
        super().__init__(parent)
        self._name = name
        self._category = color_key
        self._index = index
        self._instrument_name = ""
        self._base_note = {
            "lead": 60,
            "bass": 36,
            "perc": 36,
            "pad": 48,
            "fx": 72,
            "hum": 64,
        }.get(color_key, 60)
        self._accent = {
            "lead": "#00ffc8",
            "bass": "#8844ff",
            "perc": "#ff6644",
            "pad": "#4488ff",
            "fx": "#ffcc00",
            "hum": "#ff2222",
        }.get(color_key, "#00ffc8")
        self._step_notes = [0] * 16
        self._active_step = -1
        self.setFixedHeight(self.TRACK_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._setup_ui()

    def _setup_ui(self):
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        # ── Track Header ──────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setObjectName("trackHeader")
        hdr.setFixedWidth(180)
        hdr_lay = QVBoxLayout(hdr)
        hdr_lay.setContentsMargins(6, 4, 6, 4)
        hdr_lay.setSpacing(3)

        # row 1: name + mute/solo
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        lbl = QLabel(self._name)
        lbl.setObjectName("trackLabel")
        row1.addWidget(lbl, 1)

        self._mute_btn = QPushButton("M")
        self._mute_btn.setObjectName("muteBtn")
        self._mute_btn.setCheckable(True)
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1.addWidget(self._mute_btn)

        self._solo_btn = QPushButton("S")
        self._solo_btn.setObjectName("soloBtn")
        self._solo_btn.setCheckable(True)
        self._solo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1.addWidget(self._solo_btn)

        hdr_lay.addLayout(row1)

        # row 2: volume slider
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setObjectName("volSlider")
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(80)
        self._vol_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        hdr_lay.addWidget(self._vol_slider)

        row.addWidget(hdr)

        self._canvas = StepLaneCanvas(self)
        row.addWidget(self._canvas, 1)

    @property
    def canvas(self):
        return self._canvas

    @property
    def step_notes(self) -> list[int]:
        return self._step_notes

    def set_notes(self, notes: list[int]) -> None:
        for i in range(16):
            self._step_notes[i] = notes[i] if i < len(notes) else 0
        self._canvas.update()

    def set_active_step(self, step: int) -> None:
        self._active_step = step
        self._canvas.update()

    @property
    def is_muted(self) -> bool:
        return self._mute_btn.isChecked()

    @property
    def volume(self) -> float:
        return self._vol_slider.value() / 100.0

    @property
    def category(self) -> str:
        return self._category

    @property
    def instrument_name(self) -> str:
        return self._instrument_name

    def set_instrument_name(self, instrument_name: str) -> None:
        self._instrument_name = instrument_name


# ─────────────────────────────────────────────────────────────────────────────
#  Ruler (timeline bar)
# ─────────────────────────────────────────────────────────────────────────────
class TimelineRuler(QWidget):
    BAR_COUNT = 64

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._playhead = 0.0          # 0.0 – 1.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._playing = False

    def set_playing(self, playing: bool):
        self._playing = playing
        if playing:
            self._timer.start(50)
        else:
            self._timer.stop()

    def reset(self):
        self._playhead = 0.0
        self.update()

    def _advance(self):
        self._playhead = (self._playhead + 0.003) % 1.0
        self.update()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.fillRect(0, 0, w, h, QColor("#0a0a0a"))

        bar_w = w / self.BAR_COUNT
        for i in range(self.BAR_COUNT + 1):
            x = int(i * bar_w)
            is_beat4 = i % 4 == 0
            color = QColor("#444444") if is_beat4 else QColor("#282828")
            p.setPen(QPen(color, 1))
            p.drawLine(x, 0, x, h)

            if is_beat4:
                p.setPen(QColor("#666666"))
                p.setFont(QFont("Courier New", 7))
                p.drawText(x + 2, h - 4, str(i + 1))

        # playhead
        ph_x = int(self._playhead * w)
        p.setPen(QPen(QColor("#00ffc8"), 2))
        p.drawLine(ph_x, 0, ph_x, h)

        p.setPen(QPen(QColor("#0a0a0a"), 1))
        p.setBrush(QBrush(QColor("#00ffc8")))
        triangle = QPolygon([
            QPoint(ph_x - 5, 0),
            QPoint(ph_x + 5, 0),
            QPoint(ph_x, 9)
        ])
        p.drawPolygon(triangle)
        p.end()

    @property
    def playhead(self):
        return self._playhead


# ─────────────────────────────────────────────────────────────────────────────
#  Arrangement Canvas (ruler + lanes)
# ─────────────────────────────────────────────────────────────────────────────
TRACKS = [
    ("Lead Synth",   "lead", "lead"),
    ("Bass Line",    "bass", "bass"),
    ("Percussion",   "perc", "perc"),
    ("Pad Layer",    "pad",  "pad"),
    ("Arp / FX",     "fx",   "fx"),
    ("Hum Channel",  "hum",  "lead"),
]

class ArrangementCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("timelineCanvas")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._lanes: list[TrackLane] = []
        self._stretch_item = None
        self._setup_ui()

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── ruler row ─────────────────────────────────────────────────────
        ruler_row = QHBoxLayout()
        ruler_row.setContentsMargins(0, 0, 0, 0)
        ruler_row.setSpacing(0)

        corner = QFrame()
        corner.setFixedSize(180, 26)
        corner.setStyleSheet("background:#0a0a0a; border-right:1px solid #222; border-bottom:1px solid #222;")
        ruler_row.addWidget(corner)

        self._ruler = TimelineRuler()
        ruler_row.addWidget(self._ruler, 1)
        main.addLayout(ruler_row)

        # ── scrollable track area ─────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setObjectName("timelineCanvas")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        track_container = QWidget()
        track_container.setObjectName("timelineCanvas")
        self._track_layout = QVBoxLayout(track_container)
        self._track_layout.setContentsMargins(0, 0, 0, 0)
        self._track_layout.setSpacing(1)

        for name, cat, color_key in TRACKS:
            self._add_lane(name, color_key)

        self._track_layout.addStretch(1)
        self._stretch_item = self._track_layout.itemAt(self._track_layout.count() - 1)
        scroll.setWidget(track_container)
        main.addWidget(scroll, 1)

    def _add_lane(self, name: str, category: str) -> TrackLane:
        lane = TrackLane(name, category, len(self._lanes))
        self._lanes.append(lane)
        if self._stretch_item is None:
            self._track_layout.addWidget(lane)
        else:
            self._track_layout.insertWidget(self._track_layout.count() - 1, lane)
        return lane

    def get_track_names(self) -> list[str]:
        return [lane._name for lane in self._lanes]

    def get_lane(self, track_name: str) -> TrackLane | None:
        for lane in self._lanes:
            if lane._name == track_name:
                return lane
        return None

    def apply_hum_result(
        self,
        notes: list[int],
        instrument_name: str,
        category: str,
        create_new_track: bool,
        target_track_name: str,
    ) -> str:
        if create_new_track:
            base_name = f"Hum {instrument_name}"
            track_name = base_name
            suffix = 2
            existing = set(self.get_track_names())
            while track_name in existing:
                track_name = f"{base_name} {suffix}"
                suffix += 1
            lane = self._add_lane(track_name, category)
        else:
            lane = self.get_lane(target_track_name) or self._lanes[-1]
            track_name = lane._name

        lane.set_notes(notes)
        lane.set_instrument_name(instrument_name)
        lane._category = category
        return track_name

    def set_active_step(self, step: int):
        for lane in self._lanes:
            lane.set_active_step(step)

    def clear_active_step(self):
        self.set_active_step(-1)

    @property
    def ruler(self):
        return self._ruler

    @property
    def lanes(self):
        return self._lanes


# ─────────────────────────────────────────────────────────────────────────────
#  Resource Sidebar
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_BANKS = [
    ("lead",  "⬆ Lead Synth",    ["NES Lead",  "Chiptune High", "Buzz Lead",   "FM Sine"]),
    ("bass",  "⬇ Bass",          ["Sub Bass",  "8-Bit Bass",    "Pulse Bass",  "Saw Bass"]),
    ("perc",  "◉ Percussion",    ["Kick 909",  "Snare Clap",    "Hi-Hat 16b",  "Cymbal Px"]),
    ("pad",   "◈ Pads",          ["Warm Pad",  "Space Choir",   "String 16b",  "Analog Pad"]),
    ("fx",    "✦ FX / Arp",      ["Arp Rise",  "Glitch Hit",    "Noise Sweep", "Stab FX"]),
]

class ResourceSidebar(QWidget):
    sample_selected = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("resourceSidebar")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("16-BIT SAMPLE BANKS")
        title.setObjectName("sidebarTitle")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent; border:none;")

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(0, 6, 0, 6)
        inner_lay.setSpacing(8)

        for cat, header, items in SAMPLE_BANKS:
            cat_lbl = QLabel(header)
            cat_lbl.setStyleSheet(
                f"color:#888; font-size:9px; letter-spacing:2px; font-weight:700; "
                f"padding:4px 12px 2px; background:transparent;"
            )
            inner_lay.addWidget(cat_lbl)
            for item_name in items:
                btn = QPushButton(item_name)
                btn.setObjectName("sampleItem")
                btn.setProperty("category", cat)
                btn.setCheckable(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _, c=cat, n=item_name: self.sample_selected.emit(c, n))
                inner_lay.addWidget(btn)

        inner_lay.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)


# colour accent per instrument category (matches MidiBlock.COLORS keys)
INSTRUMENT_ACCENT = {
    "lead": "#00ffc8",
    "bass": "#8844ff",
    "perc": "#ff6644",
    "pad":  "#4488ff",
    "fx":   "#ffcc00",
}
CAT_TO_COLOR_KEY = {
    "lead": "Lead", "bass": "Bass", "perc": "Percussion",
    "pad": "Pads",  "fx":   "FX",   "hum":  "Hum",
}


# ─────────────────────────────────────────────────────────────────────────────
#  Hum Decision Dialog  (Process vs Restart)
# ─────────────────────────────────────────────────────────────────────────────
class HumDecisionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hum Recorded")
        self.setFixedSize(440, 280)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #111111;
                border: 2px solid #00ffc8;
                border-radius: 14px;
            }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(14)

        title = QLabel("Hum Captured!")
        title.setStyleSheet(
            "color:#00ffc8; font-size:22px; font-weight:700; "
            "letter-spacing:2px; background:transparent; border:none;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        sub = QLabel("What do you want to do with this recording?")
        sub.setStyleSheet("color:#666; font-size:12px; background:transparent; border:none;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)

        lay.addSpacing(10)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        process_btn = QPushButton("🎵  Process Hum")
        process_btn.setStyleSheet("""
            QPushButton {
                background: #003322; color: #00ffc8;
                border: 2px solid #00ffc8; border-radius: 9px;
                font-size: 14px; font-weight: 700;
                padding: 14px 22px;
            }
            QPushButton:hover { background: #00503a; color: #ffffff; }
        """)
        process_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        process_btn.clicked.connect(self.accept)
        btn_row.addWidget(process_btn)

        restart_btn = QPushButton("🔄  Restart")
        restart_btn.setStyleSheet("""
            QPushButton {
                background: #1a1a1a; color: #888888;
                border: 2px solid #333333; border-radius: 9px;
                font-size: 14px; font-weight: 700;
                padding: 14px 22px;
            }
            QPushButton:hover { background: #2a2a2a; color: #cccccc; border-color: #555; }
        """)
        restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restart_btn.clicked.connect(self.reject)
        btn_row.addWidget(restart_btn)

        lay.addLayout(btn_row)
        outer.addWidget(card)


# ─────────────────────────────────────────────────────────────────────────────
#  Instrument Picker Dialog
# ─────────────────────────────────────────────────────────────────────────────
class InstrumentPickerDialog(QDialog):
    def __init__(self, existing_tracks: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Instrument")
        self.setMinimumSize(640, 540)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._existing_tracks = existing_tracks
        self._selected_inst: str | None = None
        self._selected_cat: str | None = None
        self._create_new_track = False
        self._inst_buttons: list[QPushButton] = []
        self._step_index = 0
        self._proc_steps = [
            ("🎤  Analyzing vocal frequencies…",     20),
            ("🎼  Detecting pitch contour…",          42),
            ("🔧  Quantizing to 16-bit grid…",        65),
            ("🎹  Mapping to instrument patches…",    85),
            ("✅  Done! Writing notes to timeline…", 100),
        ]
        self._setup_ui()

    # ── layout ───────────────────────────────────────────────────────────────
    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #111111;
                border: 2px solid #00ffc8;
                border-radius: 14px;
            }
        """)
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_picker_page())
        self._stack.addWidget(self._build_processing_page())

        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.addWidget(self._stack)

        outer.addWidget(card)

    def _build_picker_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 22, 28, 22)
        lay.setSpacing(12)

        # header row
        hdr = QHBoxLayout()
        title = QLabel("Choose Your Instrument")
        title.setStyleSheet(
            "color:#00ffc8; font-size:18px; font-weight:700; "
            "letter-spacing:2px; background:transparent; border:none;"
        )
        hdr.addWidget(title, 1)
        close_btn = QPushButton("✕")
        close_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#555;border:none;font-size:16px;}"
            "QPushButton:hover{color:#fff;}"
        )
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(self.reject)
        hdr.addWidget(close_btn)
        lay.addLayout(hdr)

        sub = QLabel(
            "Pick a 16-bit instrument — your hum will be converted and played back through it"
        )
        sub.setStyleSheet("color:#555; font-size:11px; background:transparent; border:none;")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        # scrollable instrument grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:transparent; border:none;")

        grid_w = QWidget()
        grid_w.setStyleSheet("background:transparent;")
        grid_lay = QVBoxLayout(grid_w)
        grid_lay.setSpacing(8)
        grid_lay.setContentsMargins(0, 0, 0, 0)

        for cat, cat_label, instruments in SAMPLE_BANKS:
            accent = INSTRUMENT_ACCENT.get(cat, "#00ffc8")
            cat_hdr = QLabel(cat_label)
            cat_hdr.setStyleSheet(
                f"color:{accent}; font-size:9px; letter-spacing:3px; "
                f"font-weight:700; background:transparent; border:none; padding:4px 0 2px;"
            )
            grid_lay.addWidget(cat_hdr)

            row_lay = QHBoxLayout()
            row_lay.setSpacing(6)
            for inst in instruments:
                btn = QPushButton(inst)
                btn.setCheckable(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setProperty("inst_cat", cat)
                btn.setProperty("inst_name", inst)
                btn.setProperty("accent", accent)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #181818; color: #aaaaaa;
                        border: 1px solid #2a2a2a;
                        border-left: 3px solid {accent};
                        border-radius: 5px; font-size: 11px; font-weight: 500;
                        padding: 8px 10px; text-align: left;
                    }}
                    QPushButton:hover {{ background:#202020; color:{accent}; border-color:{accent}; }}
                    QPushButton:checked {{
                        background: #0a1510; color: {accent};
                        border: 2px solid {accent}; font-weight: 700;
                    }}
                """)
                btn.clicked.connect(lambda _, b=btn: self._select_instrument(b))
                self._inst_buttons.append(btn)
                row_lay.addWidget(btn)
            row_lay.addStretch()
            grid_lay.addLayout(row_lay)

        grid_lay.addStretch()
        scroll.setWidget(grid_w)
        lay.addWidget(scroll, 1)

        # selection label
        self._sel_label = QLabel("No instrument selected — pick one above")
        self._sel_label.setStyleSheet(
            "color:#555; font-size:11px; background:transparent; border:none;"
        )
        self._sel_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._sel_label)

        route_frame = QFrame()
        route_frame.setStyleSheet("QFrame{background:#141414; border:1px solid #262626; border-radius:8px;}")
        route_lay = QVBoxLayout(route_frame)
        route_lay.setContentsMargins(10, 8, 10, 8)
        route_lay.setSpacing(6)

        route_title = QLabel("Track Routing")
        route_title.setStyleSheet("color:#888; font-size:10px; font-weight:700; letter-spacing:1px;")
        route_lay.addWidget(route_title)

        self._overwrite_radio = QRadioButton("Overwrite existing track")
        self._new_track_radio = QRadioButton("Create new track")
        self._overwrite_radio.setChecked(True)
        for radio in (self._overwrite_radio, self._new_track_radio):
            radio.setStyleSheet("color:#bbb; font-size:11px;")
            route_lay.addWidget(radio)

        self._target_combo = QComboBox()
        self._target_combo.addItems(self._existing_tracks)
        self._target_combo.setStyleSheet(
            "QComboBox{background:#1a1a1a;color:#ddd;border:1px solid #333;border-radius:5px;padding:5px;}"
        )
        route_lay.addWidget(self._target_combo)

        self._new_track_name = QLineEdit("Hum Layer")
        self._new_track_name.setStyleSheet(
            "QLineEdit{background:#1a1a1a;color:#ddd;border:1px solid #333;border-radius:5px;padding:6px;}"
        )
        self._new_track_name.setEnabled(False)
        route_lay.addWidget(self._new_track_name)

        self._overwrite_radio.toggled.connect(self._update_route_inputs)
        self._new_track_radio.toggled.connect(self._update_route_inputs)
        lay.addWidget(route_frame)

        # big process button
        self._process_btn = QPushButton("🎹  Process Hum  →  Add to Timeline")
        self._process_btn.setEnabled(False)
        self._process_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._process_btn.setStyleSheet("""
            QPushButton {
                background: #111; color: #333;
                border: 2px solid #222; border-radius: 9px;
                font-size: 13px; font-weight: 700;
                padding: 13px 24px; letter-spacing: 1px;
            }
            QPushButton:enabled {
                background: #003322; color: #00ffc8; border-color: #00ffc8;
            }
            QPushButton:enabled:hover { background: #00503a; color: #ffffff; }
        """)
        self._process_btn.clicked.connect(self._start_processing)
        lay.addWidget(self._process_btn)

        return page

    def _build_processing_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(46, 46, 46, 46)
        lay.setSpacing(18)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._proc_icon = QLabel("🎵")
        self._proc_icon.setStyleSheet("font-size:52px; background:transparent; border:none;")
        self._proc_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._proc_icon)

        self._proc_title = QLabel("Converting Hum to MIDI…")
        self._proc_title.setStyleSheet(
            "color:#00ffc8; font-size:18px; font-weight:700; "
            "letter-spacing:2px; background:transparent; border:none;"
        )
        self._proc_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._proc_title)

        self._proc_sub = QLabel("Initializing…")
        self._proc_sub.setStyleSheet("color:#555; font-size:11px; background:transparent; border:none;")
        self._proc_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._proc_sub.setWordWrap(True)
        lay.addWidget(self._proc_sub)

        self._prog_bar = QProgressBar()
        self._prog_bar.setRange(0, 100)
        self._prog_bar.setValue(0)
        self._prog_bar.setTextVisible(False)
        self._prog_bar.setFixedHeight(8)
        self._prog_bar.setStyleSheet("""
            QProgressBar { background:#1a1a1a; border:none; border-radius:4px; }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            from:#00ffc8, to:#00aaff);
                border-radius:4px;
            }
        """)
        lay.addWidget(self._prog_bar)

        return page

    # ── interaction ──────────────────────────────────────────────────────────
    def _select_instrument(self, clicked: QPushButton):
        for b in self._inst_buttons:
            if b is not clicked:
                b.setChecked(False)
        clicked.setChecked(True)
        self._selected_inst = clicked.property("inst_name")
        self._selected_cat  = clicked.property("inst_cat")
        accent = clicked.property("accent")
        self._sel_label.setText(
            f"Selected: {self._selected_inst}  [{self._selected_cat.upper()}]"
        )
        self._sel_label.setStyleSheet(
            f"color:{accent}; font-size:11px; font-weight:600; "
            f"background:transparent; border:none;"
        )
        self._process_btn.setEnabled(True)

    def _start_processing(self):
        if not self._selected_inst:
            return
        self._create_new_track = self._new_track_radio.isChecked()
        self._stack.setCurrentIndex(1)
        self._prog_bar.setValue(0)
        self._step_index = 0
        self._proc_timer = QTimer(self)
        self._proc_timer.timeout.connect(self._proc_tick)
        self._proc_timer.start(440)

    def _update_route_inputs(self):
        make_new = self._new_track_radio.isChecked()
        self._target_combo.setEnabled(not make_new)
        self._new_track_name.setEnabled(make_new)

    def _proc_tick(self):
        if self._step_index >= len(self._proc_steps):
            self._proc_timer.stop()
            QTimer.singleShot(380, self.accept)
            return
        text, val = self._proc_steps[self._step_index]
        self._proc_sub.setText(text)
        self._prog_bar.setValue(val)
        self._step_index += 1

    @property
    def selected_instrument(self) -> str:
        return self._selected_inst or "Hum"

    @property
    def selected_category(self) -> str:
        return self._selected_cat or "hum"

    @property
    def create_new_track(self) -> bool:
        return self._create_new_track

    @property
    def target_track(self) -> str:
        return self._target_combo.currentText() if self._target_combo.count() else "Hum Channel"

    @property
    def new_track_name(self) -> str:
        return self._new_track_name.text().strip() or "Hum Layer"


# ─────────────────────────────────────────────────────────────────────────────
#  Hum Footer
# ─────────────────────────────────────────────────────────────────────────────
class HumFooter(QWidget):
    hum_done = pyqtSignal(str, str, list, bool, str)   # instrument, category, notes, create_new, target_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("humFooter")
        self._recording = False
        self._elapsed = 0
        self._sample_rate = 22050
        self._recorded_chunks: list[np.ndarray] = []
        self._input_stream = None
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._elapsed_tick)
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_on = True
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(20)

        left = QVBoxLayout()
        left.setSpacing(4)
        title = QLabel("HUM TO MUSIC")
        title.setObjectName("humTitle")
        left.addWidget(title)

        self._hum_btn = QPushButton("🎙  ACTIVATE HUM INPUT")
        self._hum_btn.setObjectName("humBtn")
        self._hum_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hum_btn.clicked.connect(self._on_hum_clicked)
        self._apply_glow(self._hum_btn)
        left.addWidget(self._hum_btn)

        self._import_btn = QPushButton("📁  IMPORT AUDIO FILE")
        self._import_btn.setObjectName("transportBtn")
        self._import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._import_btn.setMinimumHeight(36)
        self._import_btn.clicked.connect(self._on_import_audio_clicked)
        left.addWidget(self._import_btn)

        self._status_lbl = QLabel("Ready — press to start humming or import WAV")
        self._status_lbl.setStyleSheet("color:#444; font-size:10px;")
        left.addWidget(self._status_lbl)

        layout.addLayout(left)

        self._waveform = WaveformVisualizer()
        layout.addWidget(self._waveform, 1)

    @staticmethod
    def _apply_glow(widget, color: str = "#00ffc8", radius: int = 22):
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(radius)
        glow.setColor(QColor(color))
        glow.setOffset(0, 0)
        widget.setGraphicsEffect(glow)

    def _on_hum_clicked(self):
        if not self._recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _on_import_audio_clicked(self):
        if self._recording:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Audio",
            "",
            "WAV Audio (*.wav)",
        )
        if not file_path:
            return

        try:
            audio, sr = self._load_wav_audio(file_path)
        except Exception:
            self._status_lbl.setText("Import failed — use PCM WAV files")
            self._status_lbl.setStyleSheet("color:#ff6666; font-size:10px; font-weight:600;")
            return

        if audio.size < sr // 4:
            self._status_lbl.setText("Imported file too short")
            self._status_lbl.setStyleSheet("color:#ff6666; font-size:10px; font-weight:600;")
            return

        self._sample_rate = sr
        self._recorded_chunks = [audio.astype(np.float32)]
        self._status_lbl.setText("Audio imported — choose process or restart")
        self._status_lbl.setStyleSheet("color:#00ffc8; font-size:10px; font-weight:600;")
        QTimer.singleShot(100, self._show_decision_dialog)

    def _load_wav_audio(self, file_path: str) -> tuple[np.ndarray, int]:
        with wave.open(file_path, "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            src_rate = wf.getframerate()
            frame_count = wf.getnframes()
            raw = wf.readframes(frame_count)

        if sample_width == 1:
            data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        elif sample_width == 2:
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sample_width == 3:
            packed = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
            vals = (
                packed[:, 0].astype(np.int32)
                | (packed[:, 1].astype(np.int32) << 8)
                | (packed[:, 2].astype(np.int32) << 16)
            )
            neg = vals & 0x800000
            vals = vals - (neg << 1)
            data = vals.astype(np.float32) / 8388608.0
        elif sample_width == 4:
            data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            raise ValueError("Unsupported sample width")

        if channels > 1:
            data = data.reshape(-1, channels).mean(axis=1)

        target_sr = 22050
        if src_rate != target_sr and data.size > 8:
            src_x = np.linspace(0.0, 1.0, num=data.size, endpoint=False)
            tgt_len = int(data.size * (target_sr / src_rate))
            tgt_x = np.linspace(0.0, 1.0, num=max(1, tgt_len), endpoint=False)
            data = np.interp(tgt_x, src_x, data).astype(np.float32)
            src_rate = target_sr

        peak = float(np.max(np.abs(data))) if data.size else 0.0
        if peak > 0:
            data = data / peak

        return data.astype(np.float32), src_rate

    def _start_recording(self):
        self._recording = True
        self._elapsed = 0
        self._recorded_chunks = []
        self._hum_btn.setProperty("active", True)
        self._hum_btn.style().unpolish(self._hum_btn)
        self._hum_btn.style().polish(self._hum_btn)
        self._hum_btn.setText("⏹  STOP RECORDING")
        self._apply_glow(self._hum_btn, "#ff0000", 30)
        self._waveform.set_active(True)
        self._elapsed_timer.start(1000)
        self._pulse_timer.start(500)
        self._status_lbl.setText("🔴 Recording mic… click STOP RECORDING when done")
        self._status_lbl.setStyleSheet("color:#ff4444; font-size:10px; font-weight:600;")

        if sd is not None:
            try:
                def _audio_cb(indata, frames, time_info, status):
                    if self._recording:
                        self._recorded_chunks.append(indata[:, 0].copy())

                self._input_stream = sd.InputStream(
                    samplerate=self._sample_rate,
                    channels=1,
                    dtype="float32",
                    callback=_audio_cb,
                )
                self._input_stream.start()
            except Exception:
                self._input_stream = None
                self._status_lbl.setText("🔴 Recording timer active (mic unavailable)")

    def _stop_recording(self):
        self._recording = False
        self._elapsed_timer.stop()
        self._pulse_timer.stop()
        if self._input_stream is not None:
            try:
                self._input_stream.stop()
                self._input_stream.close()
            except Exception:
                pass
            self._input_stream = None
        self._waveform.set_active(False)
        self._hum_btn.setProperty("active", False)
        self._hum_btn.style().unpolish(self._hum_btn)
        self._hum_btn.style().polish(self._hum_btn)
        self._hum_btn.setText("🎙  ACTIVATE HUM INPUT")
        self._apply_glow(self._hum_btn, "#00ffc8", 22)
        self._status_lbl.setText("Hum captured — deciding…")
        self._status_lbl.setStyleSheet("color:#888; font-size:10px;")
        # slight delay so UI updates before dialog opens
        QTimer.singleShot(120, self._show_decision_dialog)

    def _show_decision_dialog(self):
        dlg = HumDecisionDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._status_lbl.setText("Opening instrument picker…")
            QTimer.singleShot(80, self._show_instrument_picker)
        else:
            self._status_lbl.setText("Restarted — press to hum again")
            self._status_lbl.setStyleSheet("color:#444; font-size:10px;")

    def _show_instrument_picker(self):
        parent = self.window()
        existing_tracks = parent._arrangement.get_track_names() if hasattr(parent, "_arrangement") else ["Hum Channel"]
        dlg = InstrumentPickerDialog(existing_tracks, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            inst = dlg.selected_instrument
            cat  = dlg.selected_category
            notes = self._build_hum_notes(cat)
            create_new = dlg.create_new_track
            target_name = dlg.new_track_name if create_new else dlg.target_track
            self._status_lbl.setText(f"✔  [{cat.upper()}] {inst} added to timeline!")
            self._status_lbl.setStyleSheet(
                "color:#00ffc8; font-size:10px; font-weight:600;"
            )
            self.hum_done.emit(inst, cat, notes, create_new, target_name)
            QTimer.singleShot(5000, self._reset_status)
        else:
            self._status_lbl.setText("Cancelled — ready for another hum")
            self._status_lbl.setStyleSheet("color:#444; font-size:10px;")

    def _build_hum_notes(self, cat: str) -> list[int]:
        if not self._recorded_chunks:
            return [0] * 16

        audio = np.concatenate(self._recorded_chunks).astype(np.float32)
        if audio.size < self._sample_rate // 2:
            return [0] * 16

        audio = audio - float(np.mean(audio))
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak < 0.01:
            return [0] * 16
        audio = audio / max(peak, 1e-6)

        scales = {
            "lead": [60, 62, 64, 67, 69, 71, 72],
            "bass": [36, 38, 40, 43, 45, 47, 48],
            "perc": [36, 0, 38, 0, 42, 0, 46],
            "pad":  [48, 50, 52, 55, 57, 59, 60],
            "fx":   [72, 74, 76, 79, 81, 83, 84],
        }
        scale = scales.get(cat, scales["lead"])

        seg_len = max(1, len(audio) // 16)
        notes = [0] * 16
        for i in range(16):
            seg = audio[i * seg_len:(i + 1) * seg_len]
            if seg.size < 256:
                notes[i] = 0
                continue
            rms = float(np.sqrt(np.mean(seg * seg)))
            if rms < 0.04:
                notes[i] = 0
                continue
            if cat == "perc":
                notes[i] = 36 if rms > 0.12 else 38
                continue

            midi = self._detect_midi(seg, self._sample_rate)
            if midi <= 0:
                notes[i] = 0
                continue
            notes[i] = min(scale, key=lambda n: abs(n - midi))

        for i in range(1, 16):
            if notes[i] == 0 and notes[i - 1] > 0 and random.random() < 0.25:
                notes[i] = notes[i - 1]
        return notes

    @staticmethod
    def _detect_midi(segment: np.ndarray, sr: int) -> int:
        seg = segment.astype(np.float32)
        seg = seg - float(np.mean(seg))
        if seg.size < 256:
            return 0

        window = np.hanning(seg.size).astype(np.float32)
        sig = seg * window
        corr = np.correlate(sig, sig, mode="full")[sig.size - 1:]
        min_freq, max_freq = 80.0, 1000.0
        min_lag = int(sr / max_freq)
        max_lag = int(sr / min_freq)
        if max_lag >= corr.size:
            max_lag = corr.size - 1
        if min_lag >= max_lag:
            return 0
        corr[:min_lag] = 0
        lag = int(np.argmax(corr[min_lag:max_lag]) + min_lag)
        if lag <= 0:
            return 0
        freq = sr / lag
        if freq < 50 or freq > 1500:
            return 0
        midi = int(round(69 + 12 * math.log2(freq / 440.0)))
        return max(24, min(96, midi))

    def _reset_status(self):
        self._status_lbl.setText("Ready — press to start humming or import WAV")
        self._status_lbl.setStyleSheet("color:#444; font-size:10px;")

    def _elapsed_tick(self):
        self._elapsed += 1
        self._status_lbl.setText(
            f"🔴 Recording… {self._elapsed}s  (click STOP RECORDING when done)"
        )

    def _pulse_tick(self):
        self._pulse_on = not self._pulse_on
        color  = "#ff0000" if self._pulse_on else "#880000"
        radius = 36        if self._pulse_on else 12
        self._apply_glow(self._hum_btn, color, radius)


# ─────────────────────────────────────────────────────────────────────────────
#  Audio Engine  — 16-bit chiptune synth + step sequencer via pygame.mixer
# ─────────────────────────────────────────────────────────────────────────────
class AudioEngine:
    """16-bit chiptune audio engine built on pygame.mixer + numpy synthesis."""

    SR = 44100          # sample rate

    # waveform per instrument category
    _WAVE_MAP = {
        "lead": "square",  "bass": "sawtooth", "perc": "noise",
        "pad":  "sine",    "fx":   "triangle",  "hum":  "square",
    }

    _CAT_AMP = {
        "lead": 0.50,
        "bass": 0.60,
        "perc": 0.75,
        "pad": 0.35,
        "fx": 0.45,
        "hum": 0.55,
    }

    _INSTRUMENT_WAVE = {
        "NES Lead": "square",
        "Chiptune High": "square",
        "Buzz Lead": "sawtooth",
        "FM Sine": "sine",
        "Sub Bass": "sine",
        "8-Bit Bass": "square",
        "Pulse Bass": "square",
        "Saw Bass": "sawtooth",
        "Warm Pad": "sine",
        "Space Choir": "triangle",
        "String 16b": "sawtooth",
        "Analog Pad": "triangle",
    }

    def __init__(self):
        self._ok = False
        if pygame is None:
            return
        try:
            pygame.mixer.pre_init(self.SR, -16, 1, 512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(12)
            self._ok = True
        except Exception as exc:
            print(f"[AudioEngine] init failed: {exc}")
            return

        self._bpm      = 120
        self._step     = 0
        self._playing  = False
        self._lanes: list | None = None

        # (waveform, midi_note) -> pygame.mixer.Sound
        self._cache: dict[tuple, object] = {}

        self._channels = [pygame.mixer.Channel(i) for i in range(12)]

        self._seq_timer = QTimer()
        self._seq_timer.timeout.connect(self._tick)

    # ── synthesis ─────────────────────────────────────────────────────────────
    @staticmethod
    def _midi_freq(note: int) -> float:
        return 440.0 * (2.0 ** ((note - 69) / 12.0))

    def _build_sound(self, waveform: str, midi_note: int,
                     dur: float, amp: float) -> object:
        sr = self.SR
        n  = max(1, int(sr * dur))
        t  = np.arange(n, dtype=np.float32) / sr

        if waveform == "noise":
            rng   = np.random.default_rng(seed=midi_note)
            noise = rng.uniform(-1.0, 1.0, n).astype(np.float32)
            if midi_note == 36:                          # kick
                tone = np.sin(
                    2 * np.pi * 60.0 * t * np.exp(-t * 25)
                ).astype(np.float32)
                wave = 0.4 * noise * np.exp(-t * 35) + 0.6 * tone
            elif midi_note == 38:                        # snare
                wave = noise * np.exp(-t * 22).astype(np.float32)
            else:
                wave = noise * np.exp(-t * 18).astype(np.float32)
        else:
            freq = self._midi_freq(midi_note)
            if waveform == "square":
                wave = np.where((t * freq) % 1.0 < 0.5, 1.0, -1.0
                                ).astype(np.float32)
            elif waveform == "sawtooth":
                wave = (2.0 * ((t * freq) % 1.0) - 1.0).astype(np.float32)
            elif waveform == "triangle":
                ph   = (t * freq) % 1.0
                wave = (2.0 * np.abs(2.0 * ph - 1.0) - 1.0).astype(np.float32)
            elif waveform == "sine":
                wave = np.sin(2.0 * np.pi * freq * t).astype(np.float32)
            else:
                wave = np.zeros(n, dtype=np.float32)

        # simple attack / release envelope
        atk = min(int(sr * 0.005), n // 8)
        rel = min(int(sr * 0.08),  n // 2)
        env = np.ones(n, dtype=np.float32)
        if atk:
            env[:atk] = np.linspace(0.0, 1.0, atk)
        if rel:
            env[n - rel:] = np.linspace(1.0, 0.0, rel)

        samples = np.ascontiguousarray(
            np.clip(wave * env * amp, -1.0, 1.0) * 32767, dtype=np.int16
        )
        return pygame.mixer.Sound(samples)

    def _sound(self, waveform: str, midi_note: int,
               dur: float, amp: float) -> object:
        key = (waveform, midi_note)
        if key not in self._cache:
            self._cache[key] = self._build_sound(waveform, midi_note, dur, amp)
        return self._cache[key]

    # ── public API ────────────────────────────────────────────────────────────
    @property
    def ok(self) -> bool:
        return self._ok

    def set_lanes(self, lanes) -> None:
        self._lanes = lanes

    def set_bpm(self, bpm: int) -> None:
        self._bpm = bpm
        if self._playing:
            self._seq_timer.setInterval(self._step_ms())

    def set_hum_instrument(self, cat: str, instrument_name: str) -> None:
        if not self._lanes:
            return
        for lane in self._lanes:
            if lane._name == "Hum Channel":
                lane._category = cat
                lane.set_instrument_name(instrument_name)
                break

    def _wave_for_lane(self, lane) -> str:
        if lane.instrument_name and lane.instrument_name in self._INSTRUMENT_WAVE:
            return self._INSTRUMENT_WAVE[lane.instrument_name]
        return self._WAVE_MAP.get(lane.category, "square")

    def start(self) -> None:
        if not self._ok:
            return
        self._playing = True
        self._step    = 0
        self._seq_timer.start(self._step_ms())

    def stop(self) -> None:
        if not self._ok:
            return
        self._playing = False
        self._seq_timer.stop()
        pygame.mixer.stop()
        if self._lanes:
            for lane in self._lanes:
                lane.set_active_step(-1)

    # ── sequencer tick ────────────────────────────────────────────────────────
    def _step_ms(self) -> int:
        return max(50, int(60_000 / self._bpm / 4))  # 16th-note in ms

    def _tick(self) -> None:
        if not self._playing or not self._lanes:
            return
        step = self._step % 16
        dur  = self._step_ms() / 1000.0 * 1.18   # gate slightly open

        for lane in self._lanes:
            lane.set_active_step(step)
            ch_idx = lane._index % len(self._channels)
            amp = self._CAT_AMP.get(lane.category, 0.5)
            waveform = self._wave_for_lane(lane)

            if lane.is_muted:
                continue
            note = lane.step_notes[step]
            if note <= 0:
                continue
            vol = lane.volume

            try:
                snd = self._sound(waveform, note, dur, amp)
                ch  = self._channels[ch_idx]
                ch.set_volume(float(vol))
                ch.play(snd)  # type: ignore[arg-type]
            except Exception:
                pass

        self._step += 1


# ─────────────────────────────────────────────────────────────────────────────
#  Main Window
# ─────────────────────────────────────────────────────────────────────────────
class Koke16BitStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Koke16-Bit Studio  —  Hum to Music DAW")
        self.resize(1280, 720)
        self.setMinimumSize(960, 600)
        self.setStyleSheet(GLOBAL_QSS)
        self._audio = AudioEngine()
        self._setup_ui()
        self._wire_signals()
        # pass lane references so sequencer can read mute/volume live
        self._audio.set_lanes(self._arrangement.lanes)

    # ── UI construction ──────────────────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_body(), 1)
        root.addWidget(self._build_hum_footer())
        root.addWidget(self._build_status_bar())

    def _build_header(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("headerBar")
        bar.setFixedHeight(80)

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 8, 20, 8)
        lay.setSpacing(0)

        # ── Left: logo ────────────────────────────────────────────────────
        logo_col = QVBoxLayout()
        logo_col.setSpacing(0)
        title = QLabel("KOKE16-BIT STUDIO")
        title.setObjectName("appTitle")
        sub = QLabel("HUM  •  COMPOSE  •  CREATE")
        sub.setObjectName("appSubtitle")
        logo_col.addWidget(title)
        logo_col.addWidget(sub)
        lay.addLayout(logo_col)

        lay.addStretch(1)

        # ── Center: transport ─────────────────────────────────────────────
        self._transport = TransportControls()
        lay.addWidget(self._transport)

        lay.addStretch(1)

        # ── Right: BPM + extras ───────────────────────────────────────────
        right_col = QHBoxLayout()
        right_col.setSpacing(12)

        self._bpm = BPMDisplay()
        right_col.addWidget(self._bpm)

        # master vol
        master_col = QVBoxLayout()
        master_col.setSpacing(2)
        master_lbl = QLabel("MASTER")
        master_lbl.setStyleSheet("color:#555; font-size:8px; letter-spacing:2px;")
        master_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        master_vol = QSlider(Qt.Orientation.Vertical)
        master_vol.setObjectName("volSlider")
        master_vol.setRange(0, 100)
        master_vol.setValue(85)
        master_vol.setFixedHeight(50)
        master_vol.setCursor(Qt.CursorShape.PointingHandCursor)
        master_col.addWidget(master_lbl)
        master_col.addWidget(master_vol, 0, Qt.AlignmentFlag.AlignHCenter)
        right_col.addLayout(master_col)

        lay.addLayout(right_col)
        return bar

    def _build_body(self) -> QWidget:
        body = QWidget()
        body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        row = QHBoxLayout(body)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self._sidebar = ResourceSidebar()
        row.addWidget(self._sidebar)

        self._arrangement = ArrangementCanvas()
        row.addWidget(self._arrangement, 1)

        return body

    def _build_hum_footer(self) -> QWidget:
        self._hum_footer = HumFooter()
        return self._hum_footer

    def _build_status_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("statusBar")
        bar.setFixedHeight(22)

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(0)

        self._status_text = QLabel("Koke16-Bit Studio  |  Click any lane grid to plot notes  |  Press ▶ to hear")
        self._status_text.setObjectName("statusText")
        lay.addWidget(self._status_text, 1)

        self._status_indicator = QLabel("● STANDBY")
        self._status_indicator.setObjectName("statusIndicator")
        lay.addWidget(self._status_indicator)

        return bar

    # ── Signal wiring ────────────────────────────────────────────────────────
    def _wire_signals(self):
        self._transport.play_toggled.connect(self._on_play)
        self._transport.stop_clicked.connect(self._on_stop)
        self._transport.record_toggled.connect(self._on_record)
        self._hum_footer.hum_done.connect(self._on_hum_done)
        self._sidebar.sample_selected.connect(self._on_sample_selected)
        self._bpm.bpm_changed.connect(self._audio.set_bpm)

    def _on_play(self, playing: bool):
        self._arrangement.ruler.set_playing(playing)
        if playing:
            self._audio.start()
            self._status_indicator.setText("● PLAYING")
            self._status_indicator.setStyleSheet("color: #00ffc8;")
            if not self._audio.ok:
                self._status_text.setText(
                    "Audio engine unavailable — install pygame & numpy to hear sound"
                )
            else:
                self._status_text.setText("Playing plotted notes — click cells to edit pattern")
        else:
            self._audio.stop()
            self._status_indicator.setText("● STANDBY")
            self._status_indicator.setStyleSheet("color: #555555;")
            self._status_text.setText("Stopped — click lane grid cells to plot notes")

    def _on_stop(self):
        self._audio.stop()
        self._arrangement.ruler.reset()
        self._arrangement.clear_active_step()
        self._status_indicator.setText("● STANDBY")
        self._status_indicator.setStyleSheet("color: #555555;")

    def _on_record(self, recording: bool):
        if recording:
            self._status_indicator.setText("● RECORDING")
            self._status_indicator.setStyleSheet("color: #ff2222;")
        else:
            self._status_indicator.setText("● STANDBY")
            self._status_indicator.setStyleSheet("color: #555555;")

    def _on_hum_done(self, instrument: str, cat: str, notes: list, create_new_track: bool, target_name: str):
        target_track = self._arrangement.apply_hum_result(
            notes=notes,
            instrument_name=instrument,
            category=cat,
            create_new_track=create_new_track,
            target_track_name=target_name,
        )
        self._audio.set_hum_instrument(cat, instrument)
        self._status_text.setText(
            f"Hum → Music  |  [{cat.upper()}] {instrument} plotted to '{target_track}'  |  Press ▶"
        )

    def _on_sample_selected(self, cat: str, name: str):
        self._status_text.setText(f"Sample loaded: [{cat.upper()}]  {name}  —  drag to timeline to place")


# ─────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # Must be set before QApplication is created
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Koke16-Bit Studio")
    app.setOrganizationName("KokeSynth")

    window = Koke16BitStudio()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
