from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from daw.models import NoteEvent, Track


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def midi_name(midi_note: int) -> str:
    octave = midi_note // 12 - 1
    return f"{NOTE_NAMES[midi_note % 12]}{octave}"


class PianoRollCanvas(QWidget):
    note_selected = pyqtSignal(object)
    note_audition = pyqtSignal(int)

    KEY_WIDTH = 64
    TICK_WIDTH = 22
    ROW_HEIGHT = 18
    TOTAL_TICKS = 256
    NOTE_TOP = 108
    NOTE_BOTTOM = 21
    DEFAULT_VIEW_TOP = 84      # C6
    DEFAULT_VIEW_BOTTOM = 41   # F2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.track: Track | None = None
        self.playhead_tick = 0
        self.selected_note: NoteEvent | None = None
        self.hover_note: NoteEvent | None = None
        self.hover_edge: str | None = None
        self._drag_note: NoteEvent | None = None
        self._drag_mode: str | None = None
        self._drag_origin_tick = 0
        self._drag_origin_note = 0
        self._drag_origin_length = 0
        self._drag_mouse_tick = 0
        self._drag_end_tick = 0
        self._last_audition_pitch: int | None = None
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumSize(self.KEY_WIDTH + self.TOTAL_TICKS * self.TICK_WIDTH, (self.NOTE_TOP - self.NOTE_BOTTOM + 1) * self.ROW_HEIGHT)

    def set_track(self, track: Track | None):
        self.track = track
        self.selected_note = None
        self.hover_note = None
        self.hover_edge = None
        self.update()

    def set_playhead(self, tick: int):
        self.playhead_tick = tick
        self.update()

    def pitch_to_row(self, midi_note: int) -> int:
        return self.NOTE_TOP - midi_note

    def row_to_pitch(self, row: int) -> int:
        return self.NOTE_TOP - row

    def x_to_tick(self, x: int) -> int:
        return max(0, min(self.TOTAL_TICKS - 1, int((x - self.KEY_WIDTH) / self.TICK_WIDTH)))

    def y_to_pitch(self, y: int) -> int:
        row = max(0, min(self.NOTE_TOP - self.NOTE_BOTTOM, int(y / self.ROW_HEIGHT)))
        return self.row_to_pitch(row)

    def note_rect(self, note: NoteEvent) -> QRect:
        row = self.pitch_to_row(note.midi_note)
        x = self.KEY_WIDTH + note.start_tick * self.TICK_WIDTH
        y = row * self.ROW_HEIGHT + 1
        w = max(self.TICK_WIDTH, note.length_tick * self.TICK_WIDTH)
        h = self.ROW_HEIGHT - 2
        return QRect(x, y, w, h)

    def hit_note(self, pos: QPoint) -> tuple[NoteEvent | None, str | None]:
        if not self.track:
            return None, None
        for note in reversed(self.track.notes):
            rect = self.note_rect(note)
            if rect.contains(pos):
                near_left = abs(pos.x() - rect.left()) <= 6
                near_right = abs(pos.x() - rect.right()) <= 6
                if near_left:
                    return note, "left"
                if near_right:
                    return note, "right"
                return note, "body"
        return None, None

    def _update_hover_state(self, pos: QPoint):
        if pos.x() < self.KEY_WIDTH:
            self.hover_note = None
            self.hover_edge = None
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.update()
            return

        note, edge = self.hit_note(pos)
        self.hover_note = note
        self.hover_edge = edge
        if note is None:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif edge in ("left", "right"):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.update()

    def mousePressEvent(self, event):  # noqa: N802
        if not self.track:
            return

        pos = event.position().toPoint()

        if pos.x() < self.KEY_WIDTH:
            pitch = self.y_to_pitch(pos.y())
            self.note_audition.emit(pitch)
            return

        if event.button() == Qt.MouseButton.RightButton:
            note, _ = self.hit_note(pos)
            if note:
                self.track.notes.remove(note)
                if self.selected_note is note:
                    self.selected_note = None
                    self.note_selected.emit(None)
                self.update()
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        note, edge = self.hit_note(pos)
        if note:
            self.selected_note = note
            self.note_selected.emit(note)
            self.note_audition.emit(note.midi_note)
            self._drag_note = note
            self._drag_mode = "resize-left" if edge == "left" else "resize-right" if edge == "right" else "move"
            self._drag_origin_tick = note.start_tick
            self._drag_origin_note = note.midi_note
            self._drag_origin_length = note.length_tick
            self._drag_end_tick = note.start_tick + note.length_tick
            self._drag_mouse_tick = self.x_to_tick(pos.x())
            self._last_audition_pitch = note.midi_note
            self.update()
            return

        # create note
        tick = self.x_to_tick(pos.x())
        pitch = self.y_to_pitch(pos.y())
        new_note = NoteEvent(start_tick=tick, length_tick=4, midi_note=pitch, velocity=100)
        self.track.notes.append(new_note)
        self.selected_note = new_note
        self.note_selected.emit(new_note)
        self._drag_note = new_note
        self._drag_mode = "resize"
        self._drag_origin_tick = new_note.start_tick
        self._drag_origin_note = new_note.midi_note
        self._drag_origin_length = new_note.length_tick
        self._drag_mouse_tick = tick
        self.note_audition.emit(new_note.midi_note)
        self._last_audition_pitch = new_note.midi_note
        self.update()

    def mouseMoveEvent(self, event):  # noqa: N802
        if not self.track:
            return

        pos = event.position().toPoint()
        if self._drag_note is None or self._drag_mode is None:
            self._update_hover_state(pos)
            return

        tick_now = self.x_to_tick(pos.x())
        delta_tick = tick_now - self._drag_mouse_tick

        if self._drag_mode == "resize-right":
            self._drag_note.length_tick = max(1, self._drag_origin_length + delta_tick)
        elif self._drag_mode == "resize-left":
            new_start = max(0, self._drag_origin_tick + delta_tick)
            new_end = max(new_start + 1, self._drag_end_tick)
            self._drag_note.start_tick = new_start
            self._drag_note.length_tick = max(1, new_end - new_start)
        else:
            self._drag_note.start_tick = max(0, self._drag_origin_tick + delta_tick)
            self._drag_note.midi_note = self.y_to_pitch(pos.y())
            if self._drag_note.midi_note != self._last_audition_pitch:
                self.note_audition.emit(self._drag_note.midi_note)
                self._last_audition_pitch = self._drag_note.midi_note

        self.note_selected.emit(self._drag_note)
        self.update()

    def mouseReleaseEvent(self, event):  # noqa: N802
        self._drag_note = None
        self._drag_mode = None
        self._last_audition_pitch = None
        self._update_hover_state(event.position().toPoint())

    def leaveEvent(self, event):  # noqa: N802
        self.hover_note = None
        self.hover_edge = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        width = self.width()
        height = self.height()

        p.fillRect(0, 0, width, height, QColor("#101010"))

        # key background
        p.fillRect(0, 0, self.KEY_WIDTH, height, QColor("#0a0a0a"))

        rows = self.NOTE_TOP - self.NOTE_BOTTOM + 1
        for row in range(rows):
            midi_note = self.row_to_pitch(row)
            y = row * self.ROW_HEIGHT
            is_black = NOTE_NAMES[midi_note % 12].endswith("#")
            row_bg = QColor("#161616" if is_black else "#131313")
            p.fillRect(self.KEY_WIDTH, y, width - self.KEY_WIDTH, self.ROW_HEIGHT, row_bg)
            p.setPen(QPen(QColor("#222222"), 1))
            p.drawLine(0, y, width, y)

            if row % 12 == 0:
                p.setPen(QPen(QColor("#2f2f2f"), 1))
                p.drawLine(self.KEY_WIDTH, y, width, y)

            p.setPen(QColor("#666666"))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(6, y + self.ROW_HEIGHT - 5, midi_name(midi_note))

        # vertical timeline grid
        for t in range(self.TOTAL_TICKS + 1):
            x = self.KEY_WIDTH + t * self.TICK_WIDTH
            if t % 16 == 0:
                c = QColor("#3f3f3f")
            elif t % 4 == 0:
                c = QColor("#2b2b2b")
            else:
                c = QColor("#1c1c1c")
            p.setPen(QPen(c, 1))
            p.drawLine(x, 0, x, height)

        # playhead
        px = self.KEY_WIDTH + self.playhead_tick * self.TICK_WIDTH
        p.fillRect(px, 0, self.TICK_WIDTH, height, QColor("#00ffc81c"))
        p.setPen(QPen(QColor("#00ffc8"), 1))
        p.drawLine(px, 0, px, height)

        if self.track:
            for note in self.track.notes:
                rect = self.note_rect(note)
                selected = note is self.selected_note
                hovered = note is self.hover_note
                fill = QColor("#00d8a8" if not selected else "#25ffcf")
                if hovered and not selected:
                    fill = QColor("#19f0be")
                border = QColor("#b6fff0" if selected else "#00ffc8")
                if hovered and not selected:
                    border = QColor("#78ffe2")
                p.setPen(QPen(border, 1))
                p.setBrush(fill)
                p.drawRect(rect)

                if hovered and self.hover_edge in ("left", "right"):
                    edge_x = rect.left() if self.hover_edge == "left" else rect.right() - 1
                    p.fillRect(edge_x, rect.top(), 2, rect.height(), QColor("#d5fff5"))

                label = f"{midi_name(note.midi_note)} v{note.velocity}"
                p.setPen(QColor("#001e17"))
                p.setFont(QFont("Segoe UI", 7))
                p.drawText(rect.adjusted(2, 1, -2, -1), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)

        p.end()


class PianoRollEditor(QWidget):
    note_selected = pyqtSignal(object)
    note_audition = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.canvas = PianoRollCanvas()
        self.canvas.note_selected.connect(self.note_selected)
        self.canvas.note_audition.connect(self.note_audition)

        self.scroll.setWidget(self.canvas)
        layout.addWidget(self.scroll)
        self._apply_default_viewport()

    def _apply_default_viewport(self):
        top_row = self.canvas.pitch_to_row(self.canvas.DEFAULT_VIEW_TOP)
        top_y = top_row * self.canvas.ROW_HEIGHT
        self.scroll.verticalScrollBar().setValue(top_y)

    def set_track(self, track: Track | None):
        self.canvas.set_track(track)

    def set_playhead(self, tick: int):
        self.canvas.set_playhead(tick)
