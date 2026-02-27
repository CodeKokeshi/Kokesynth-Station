from __future__ import annotations

import sys
import numpy as np
import sounddevice as sd

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QProgressDialog,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from daw.audio import AudioEngine
from daw.dialogs import AddTrackDialog, RoleInstrumentDialog
from daw.exporter import export_wav
from daw.models import NoteEvent, Project, Track
from daw.pianoroll import PianoRollEditor, midi_name
from daw.transcriber import audio_to_multitrack_events, load_audio, TranscriptionCancelled


APP_QSS = """
QMainWindow, QWidget { background: #101010; color: #e7e7e7; font-family: Segoe UI; }
QPushButton { background: #1f1f1f; border: 1px solid #343434; border-radius: 6px; padding: 6px 10px; }
QPushButton:hover { border-color: #00ffc8; color: #00ffc8; }
QListWidget { background: #121212; border: 1px solid #2a2a2a; border-radius: 6px; }
QFrame#panel { background: #111111; border: 1px solid #292929; border-radius: 8px; }
QLabel#title { color: #00ffc8; font-size: 20px; font-weight: 700; }
"""


class ImportCancelledError(Exception):
    pass


class ImportProgressDialog(QProgressDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_close = False

    def closeEvent(self, event):
        if self.allow_close:
            super().closeEvent(event)
            return
        event.ignore()
        self.canceled.emit()


class AudioImportWorker(QObject):
    progress_changed = pyqtSignal(int, str)
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(
        self,
        source_label: str,
        audio: np.ndarray | None = None,
        sample_rate: int = 22050,
        file_path: str | None = None,
        bpm: int = 120,
        ticks_per_beat: int = 4,
    ):
        super().__init__()
        self.source_label = source_label
        self.audio = audio
        self.sample_rate = sample_rate
        self.file_path = file_path
        self.bpm = bpm
        self.ticks_per_beat = ticks_per_beat
        self._cancel_requested = False

    @pyqtSlot()
    def request_cancel(self):
        self._cancel_requested = True

    @pyqtSlot()
    def run(self):
        try:
            if self.file_path:
                self._emit_progress(6, "Loading audio file...")
                audio, sr = load_audio(self.file_path, target_sr=22050)
            else:
                audio = self.audio
                sr = self.sample_rate

            if audio is None:
                raise ValueError("No audio data provided")

            if self._cancel_requested:
                raise ImportCancelledError()

            split = audio_to_multitrack_events(
                audio,
                sr,
                bpm=self.bpm,
                ticks_per_beat=self.ticks_per_beat,
                progress_callback=self._emit_progress,
                should_cancel=self._should_cancel,
            )
            self.finished.emit(split)
        except ImportCancelledError:
            self.cancelled.emit()
        except TranscriptionCancelled:
            self.cancelled.emit()
        except RuntimeError as exc:
            if "cancel" in str(exc).lower():
                self.cancelled.emit()
            else:
                self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(str(exc))

    def _should_cancel(self) -> bool:
        return self._cancel_requested

    def _emit_progress(self, percent: int, message: str):
        if self._cancel_requested:
            raise ImportCancelledError()
        self.progress_changed.emit(int(percent), message)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project = Project()
        self.audio = AudioEngine(self.project)

        self.setWindowTitle("Koke16-Bit Studio")
        self.resize(1400, 860)
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(APP_QSS)

        self._active_note: NoteEvent | None = None
        self._hum_recording = False
        self._hum_sample_rate = 22050
        self._hum_chunks: list[np.ndarray] = []
        self._hum_stream = None
        self._import_thread: QThread | None = None
        self._import_worker: AudioImportWorker | None = None
        self._import_progress_dialog: QProgressDialog | None = None
        self._import_source_label = ""

        self._build_ui()
        self._wire_signals()
        self._refresh_track_list()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        main = QVBoxLayout(root)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        # Header
        header = QFrame()
        header.setObjectName("panel")
        h = QHBoxLayout(header)
        h.setContentsMargins(12, 10, 12, 10)

        title = QLabel("Koke16-Bit Studio")
        title.setObjectName("title")
        h.addWidget(title)

        h.addStretch(1)

        self.btn_add_track = QPushButton("+ Add Piano Roll Track")
        self.btn_hum_music = QPushButton("🎙 Hum → Music")
        self.btn_import_music = QPushButton("📁 Import Audio → Music")
        self.btn_play = QPushButton("▶ Play")
        self.btn_stop = QPushButton("■ Stop")
        self.btn_export = QPushButton("💾 Export WAV")

        h.addWidget(self.btn_add_track)
        h.addWidget(self.btn_hum_music)
        h.addWidget(self.btn_import_music)
        h.addWidget(self.btn_play)
        h.addWidget(self.btn_stop)
        h.addWidget(self.btn_export)

        bpm_label = QLabel("BPM")
        self.spin_bpm = QSpinBox()
        self.spin_bpm.setRange(40, 260)
        self.spin_bpm.setValue(self.project.bpm)
        self.spin_bpm.setFixedWidth(74)

        h.addSpacing(10)
        h.addWidget(bpm_label)
        h.addWidget(self.spin_bpm)

        h.addSpacing(12)
        h.addWidget(QLabel("Loop"))
        self.combo_loop_mode = QComboBox()
        self.combo_loop_mode.addItems([
            "Dynamic (All Tracks)",
            "Full Timeline",
            "Custom Length",
        ])
        self.combo_loop_mode.setCurrentIndex(0)
        h.addWidget(self.combo_loop_mode)

        self.spin_loop_beats = QSpinBox()
        self.spin_loop_beats.setRange(1, 128)
        self.spin_loop_beats.setValue(16)
        self.spin_loop_beats.setFixedWidth(74)
        self.spin_loop_beats.setEnabled(False)
        h.addWidget(QLabel("Bars"))
        h.addWidget(self.spin_loop_beats)

        main.addWidget(header)

        # Body splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main.addWidget(splitter, 1)

        # Left panel: tracks
        left = QFrame()
        left.setObjectName("panel")
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(10, 10, 10, 10)

        left_l.addWidget(QLabel("Tracks"))
        self.list_tracks = QListWidget()
        left_l.addWidget(self.list_tracks, 1)

        self.track_volume = QSlider(Qt.Orientation.Horizontal)
        self.track_volume.setRange(0, 100)
        self.track_volume.setValue(80)
        left_l.addWidget(QLabel("Track Volume"))
        left_l.addWidget(self.track_volume)

        splitter.addWidget(left)

        # Center: empty placeholder or piano roll
        center = QFrame()
        center.setObjectName("panel")
        center_l = QVBoxLayout(center)
        center_l.setContentsMargins(8, 8, 8, 8)

        self.center_stack = QStackedWidget()

        self.empty_view = QLabel(
            "Blank canvas\n\nClick '+ Add Piano Roll Track' to choose an instrument and create your first track."
        )
        self.empty_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_view.setStyleSheet("color:#6f6f6f; font-size:14px;")
        self.center_stack.addWidget(self.empty_view)

        self.editor = PianoRollEditor()
        self.center_stack.addWidget(self.editor)

        center_l.addWidget(self.center_stack)
        splitter.addWidget(center)

        # Right panel: note inspector
        right = QFrame()
        right.setObjectName("panel")
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(10, 10, 10, 10)
        right_l.setSpacing(8)

        right_l.addWidget(QLabel("Note Inspector"))
        self.lbl_note = QLabel("No note selected")
        self.lbl_note.setStyleSheet("color:#8a8a8a;")
        right_l.addWidget(self.lbl_note)

        self.spin_velocity = QSpinBox()
        self.spin_velocity.setRange(1, 127)
        self.spin_velocity.setValue(100)
        right_l.addWidget(QLabel("Velocity"))
        right_l.addWidget(self.spin_velocity)

        self.spin_length = QSpinBox()
        self.spin_length.setRange(1, 64)
        self.spin_length.setValue(4)
        right_l.addWidget(QLabel("Length (ticks)"))
        right_l.addWidget(self.spin_length)

        right_l.addStretch(1)

        tips = QLabel(
            "Piano Roll Controls:\n"
            "- Left click empty grid: create note\n"
            "- Drag note body: move\n"
            "- Drag note right edge: resize\n"
            "- Right click note: delete\n"
            "- Click note keys (left): preview pitch"
        )
        tips.setStyleSheet("color:#7a7a7a; font-size:11px;")
        tips.setWordWrap(True)
        right_l.addWidget(tips)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([260, 850, 250])

        self.status = self.statusBar()
        self.status.showMessage("Ready. Add a track to start composing.")

    def _wire_signals(self):
        self.btn_add_track.clicked.connect(self._on_add_track)
        self.btn_hum_music.clicked.connect(self._on_hum_music)
        self.btn_import_music.clicked.connect(self._on_import_audio_music)
        self.btn_play.clicked.connect(self._on_play)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_export.clicked.connect(self._on_export_wav)
        self.spin_bpm.valueChanged.connect(self._on_bpm_changed)
        self.combo_loop_mode.currentIndexChanged.connect(self._on_loop_mode_changed)
        self.spin_loop_beats.valueChanged.connect(self._on_loop_beats_changed)

        self.list_tracks.currentRowChanged.connect(self._on_track_selected)
        self.track_volume.valueChanged.connect(self._on_track_volume_changed)

        self.editor.note_selected.connect(self._on_note_selected)
        self.editor.note_audition.connect(self._on_note_audition)

        self.spin_velocity.valueChanged.connect(self._on_velocity_changed)
        self.spin_length.valueChanged.connect(self._on_length_changed)

        self.audio.position_changed.connect(self.editor.set_playhead)

    def _on_add_track(self):
        dialog = AddTrackDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            selected = dialog.selected_instrument()
            if not selected:
                return
            index = len(self.project.tracks) + 1
            name = f"{selected['name']} {index}"
            track = Track(name=name, instrument_name=selected["name"], waveform=selected["waveform"], volume=0.8)
            self.project.tracks.append(track)
            self.project.selected_track_index = len(self.project.tracks) - 1
            self._refresh_track_list()
            self.list_tracks.setCurrentRow(self.project.selected_track_index)
            self.status.showMessage(f"Track created: {track.name}", 3000)

    def _on_hum_music(self):
        if not self._hum_recording:
            self._start_hum_capture()
        else:
            self._stop_hum_capture_and_process()

    def _start_hum_capture(self):
        self._hum_chunks = []
        self._hum_recording = True
        self.btn_hum_music.setText("⏹ Stop Hum")
        self.status.showMessage("Hum capture started... click again to stop and process.")

        def _callback(indata, frames, time_info, status):
            if self._hum_recording:
                self._hum_chunks.append(indata[:, 0].copy())

        try:
            self._hum_stream = sd.InputStream(
                samplerate=self._hum_sample_rate,
                channels=1,
                dtype="float32",
                callback=_callback,
            )
            self._hum_stream.start()
        except Exception:
            self._hum_recording = False
            self._hum_stream = None
            self.btn_hum_music.setText("🎙 Hum → Music")
            self.status.showMessage("Microphone unavailable.", 3000)

    def _stop_hum_capture_and_process(self):
        self._hum_recording = False
        self.btn_hum_music.setText("🎙 Hum → Music")
        if self._hum_stream is not None:
            self._hum_stream.stop()
            self._hum_stream.close()
            self._hum_stream = None

        if not self._hum_chunks:
            self.status.showMessage("No hum captured.", 2500)
            return

        audio = np.concatenate(self._hum_chunks).astype(np.float32)
        self._start_audio_import_job(source_label="Hum", audio=audio, sample_rate=self._hum_sample_rate)

    def _on_import_audio_music(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Audio",
                "",
                "WAV Audio (*.wav)",
            )
        except KeyboardInterrupt:
            self.status.showMessage("Import interrupted.", 2500)
            return
        except Exception as exc:
            self.status.showMessage("Could not open import dialog.", 3000)
            QMessageBox.warning(self, "Import Error", f"Could not open file dialog:\n{exc}")
            return

        if not file_path:
            return

        self._start_audio_import_job(source_label="Imported audio", file_path=file_path)

    def _start_audio_import_job(
        self,
        source_label: str,
        audio: np.ndarray | None = None,
        sample_rate: int = 22050,
        file_path: str | None = None,
    ):
        if self._import_thread is not None:
            self.status.showMessage("Audio import already in progress...", 2000)
            return

        self._import_source_label = source_label
        self._set_import_controls_enabled(False)

        progress = ImportProgressDialog("Preparing audio analysis...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Importing Audio")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        progress.setWindowFlag(Qt.WindowType.MSWindowsFixedSizeDialogHint, True)
        progress.setValue(0)
        progress.show()
        progress.setFixedSize(progress.sizeHint())
        self._import_progress_dialog = progress

        self._import_thread = QThread(self)
        self._import_worker = AudioImportWorker(
            source_label=source_label,
            audio=audio,
            sample_rate=sample_rate,
            file_path=file_path,
            bpm=self.project.bpm,
            ticks_per_beat=self.project.ticks_per_beat,
        )
        self._import_worker.moveToThread(self._import_thread)

        self._import_thread.started.connect(self._import_worker.run)
        self._import_worker.progress_changed.connect(self._on_import_progress)
        self._import_worker.finished.connect(self._on_import_analysis_finished)
        self._import_worker.failed.connect(self._on_import_analysis_failed)
        self._import_worker.cancelled.connect(self._on_import_analysis_cancelled)
        self._import_worker.finished.connect(self._import_thread.quit)
        self._import_worker.failed.connect(self._import_thread.quit)
        self._import_worker.cancelled.connect(self._import_thread.quit)
        self._import_thread.finished.connect(self._on_import_thread_finished)
        self._import_thread.finished.connect(self._import_worker.deleteLater)
        self._import_thread.finished.connect(self._import_thread.deleteLater)

        progress.canceled.connect(self._on_import_cancel_requested)

        self.status.showMessage("Import analysis started...", 2000)
        self._import_thread.start()

    def _on_import_progress(self, percent: int, message: str):
        dialog = self._import_progress_dialog
        if dialog is not None:
            try:
                dialog.setValue(max(0, min(100, percent)))
                dialog.setLabelText(message)
            except RuntimeError:
                pass
        self.status.showMessage(message)

    def _on_import_analysis_finished(self, split_obj):
        split = split_obj if isinstance(split_obj, dict) else {}
        dialog = self._import_progress_dialog
        if dialog is not None:
            try:
                dialog.setValue(100)
                dialog.setLabelText("Finalizing track setup...")
            except RuntimeError:
                pass

        self._finalize_audio_to_music(split, self._import_source_label)

    def _on_import_analysis_failed(self, error_message: str):
        self._close_import_progress_dialog()
        self._set_import_controls_enabled(True)
        self.status.showMessage("Audio analysis failed.", 3000)
        QMessageBox.warning(self, "Import Failed", f"Could not convert audio:\n{error_message}")

    def _on_import_analysis_cancelled(self):
        self._close_import_progress_dialog()
        self._set_import_controls_enabled(True)
        self.status.showMessage("Import cancelled.", 3000)

    def _on_import_cancel_requested(self):
        if self._import_worker is None:
            return

        answer = QMessageBox.warning(
            self,
            "Cancel Import?",
            "Cancel this audio import/conversion now?\nAny generated tracks for this run will be discarded.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._import_worker.request_cancel()
            if self._import_progress_dialog is not None:
                self._import_progress_dialog.setLabelText("Cancelling import...")

    def _close_import_progress_dialog(self):
        dialog = self._import_progress_dialog
        if dialog is None:
            return
        dialog.allow_close = True
        dialog.blockSignals(True)
        dialog.close()
        dialog.blockSignals(False)
        self._import_progress_dialog = None

    def _on_import_thread_finished(self):
        self._close_import_progress_dialog()
        self._set_import_controls_enabled(True)
        self._import_worker = None
        self._import_thread = None

    def _set_import_controls_enabled(self, enabled: bool):
        self.btn_add_track.setEnabled(enabled)
        self.btn_hum_music.setEnabled(enabled)
        self.btn_import_music.setEnabled(enabled)
        self.btn_play.setEnabled(enabled)
        self.btn_stop.setEnabled(enabled)

    def _finalize_audio_to_music(self, split: dict[str, list[NoteEvent]], source_label: str):
        default_plan = [
            ("Lead", "NES Square", "square", split.get("lead", []), 0.95),
            ("Bass", "Gameboy Square", "square", split.get("bass", []), 0.55),
            ("Harmony", "Generic Triangle", "triangle", split.get("harmony", []), 0.40),
            ("Drums", "NES Noise", "noise", split.get("drums", []), 0.60),
        ]
        available_roles = [row for row in default_plan if row[3]]
        if not available_roles:
            self.status.showMessage("No clear parts detected for auto-retrofy.", 3000)
            return

        answer = QMessageBox.question(
            self,
            "Auto-select instruments?",
            "Automatically choose instruments for detected tracks?\n\n"
            "Yes = quick auto assignment\n"
            "No = choose instrument per track (Lead/Bass/Harmony/Drums)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            self.status.showMessage(f"{source_label} processing cancelled.", 2000)
            return

        if answer == QMessageBox.StandardButton.Yes:
            plan = available_roles
        else:
            plan = []
            for role, default_name, default_waveform, events, vol in available_roles:
                chooser = RoleInstrumentDialog(role, default_name, self)
                if chooser.exec() != chooser.DialogCode.Accepted:
                    self.status.showMessage("Multi-track conversion cancelled.", 2500)
                    return
                chosen = chooser.selected_instrument()
                if not chosen:
                    self.status.showMessage("Instrument selection missing.", 2500)
                    return
                plan.append((role, chosen["name"], chosen["waveform"], events, vol))

        created_or_updated = 0
        for role, inst_name, waveform, events, vol in plan:
            index = len(self.project.tracks) + 1
            name = f"{source_label} {role} {index}"
            track = Track(
                name=name,
                instrument_name=inst_name,
                waveform=waveform,
                volume=vol,
                notes=events,
            )
            self.project.tracks.append(track)
            self.project.selected_track_index = len(self.project.tracks) - 1
            created_or_updated += 1

        self._refresh_track_list()
        self.list_tracks.setCurrentRow(self.project.selected_track_index)
        self.status.showMessage(
            f"{source_label} retrofied: {created_or_updated} tracks generated",
            4000,
        )

    def _refresh_track_list(self):
        self.list_tracks.clear()
        for track in self.project.tracks:
            self.list_tracks.addItem(f"{track.name}  [{track.instrument_name}]")

        has_tracks = len(self.project.tracks) > 0
        self.center_stack.setCurrentIndex(1 if has_tracks else 0)

    def _on_track_selected(self, row: int):
        if row < 0 or row >= len(self.project.tracks):
            self.project.selected_track_index = -1
            self.editor.set_track(None)
            self._active_note = None
            self.lbl_note.setText("No note selected")
            return

        self.project.selected_track_index = row
        track = self.project.tracks[row]
        self.editor.set_track(track)
        self.track_volume.blockSignals(True)
        self.track_volume.setValue(int(track.volume * 100))
        self.track_volume.blockSignals(False)
        self.status.showMessage(f"Editing {track.name}", 2000)

    def _on_track_volume_changed(self, value: int):
        track = self.project.selected_track
        if track:
            track.volume = value / 100.0

    def _on_note_selected(self, note_obj):
        self._active_note = note_obj
        if not note_obj:
            self.lbl_note.setText("No note selected")
            return
        note: NoteEvent = note_obj
        self.lbl_note.setText(f"{midi_name(note.midi_note)} at tick {note.start_tick}")
        self.spin_velocity.blockSignals(True)
        self.spin_length.blockSignals(True)
        self.spin_velocity.setValue(note.velocity)
        self.spin_length.setValue(note.length_tick)
        self.spin_velocity.blockSignals(False)
        self.spin_length.blockSignals(False)

    def _on_velocity_changed(self, value: int):
        if self._active_note:
            self._active_note.velocity = value
            self.editor.canvas.update()

    def _on_length_changed(self, value: int):
        if self._active_note:
            self._active_note.length_tick = value
            self.editor.canvas.update()

    def _on_note_audition(self, midi_note: int):
        track = self.project.selected_track
        if track:
            self.audio.preview_note(track.waveform, midi_note, 110)

    def _on_bpm_changed(self, value: int):
        self.audio.set_bpm(value)

    def _on_loop_mode_changed(self, index: int):
        if index == 0:
            self.project.loop_mode = "dynamic"
            self.spin_loop_beats.setEnabled(False)
            self.status.showMessage("Loop mode: Dynamic (all tracks)", 2000)
        elif index == 1:
            self.project.loop_mode = "timeline"
            self.spin_loop_beats.setEnabled(False)
            self.status.showMessage("Loop mode: Full timeline", 2000)
        else:
            self.project.loop_mode = "custom"
            self.spin_loop_beats.setEnabled(True)
            self._on_loop_beats_changed(self.spin_loop_beats.value())

    def _on_loop_beats_changed(self, bars: int):
        self.project.custom_loop_ticks = max(1, bars * self.project.ticks_per_beat * 4)
        if self.project.loop_mode == "custom":
            self.status.showMessage(f"Loop mode: Custom ({bars} bars)", 2000)

    def _on_play(self):
        if not self.project.tracks:
            self.status.showMessage("Add at least one track first.", 2000)
            return
        self.audio.start()
        self.status.showMessage("Playback started", 1500)

    def _on_stop(self):
        self.audio.stop()
        self.status.showMessage("Playback stopped", 1500)

    # ── Export WAV ──────────────────────────────────────────────────

    def _on_export_wav(self):
        """Ask loop count, pick save path, render + export WAV."""
        if not self.project.tracks:
            self.status.showMessage("Nothing to export — add tracks first.", 2500)
            return

        # Stop playback so audio engine doesn't interfere
        if self.audio.playing:
            self.audio.stop()

        # Ask how many loops
        from PyQt6.QtWidgets import QInputDialog
        loops, ok = QInputDialog.getInt(
            self, "Export — Loop Count",
            "How many loops to render?\n"
            "(1 = single pass, 2 = plays the loop twice, etc.)",
            value=1, min=1, max=99,
        )
        if not ok:
            return

        # Pick save location
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, "Export WAV", "", "WAV Files (*.wav)"
            )
        except KeyboardInterrupt:
            return
        if not path:
            return
        if not path.lower().endswith(".wav"):
            path += ".wav"

        # Show a progress dialog
        dlg = QProgressDialog("Rendering audio\u2026", "Cancel", 0, 100, self)
        dlg.setWindowTitle("Exporting WAV")
        dlg.setMinimumWidth(380)
        dlg.setMinimumDuration(0)
        dlg.setValue(0)
        dlg.setAutoClose(False)
        dlg.setAutoReset(False)

        cancelled = False

        def _on_cancel():
            nonlocal cancelled
            cancelled = True

        dlg.canceled.connect(_on_cancel)

        def _progress(pct: int, msg: str) -> None:
            if cancelled:
                raise RuntimeError("Export cancelled")
            try:
                dlg.setValue(pct)
                dlg.setLabelText(msg)
            except RuntimeError:
                pass
            QApplication.processEvents()

        try:
            export_wav(
                path, self.project,
                loops=loops,
                sample_rate=44100,
                progress_callback=_progress,
            )
            dlg.setValue(100)
            dlg.setLabelText("Done!")
            dlg.close()

            QMessageBox.information(
                self, "Export Complete",
                f"Exported {loops} loop(s) to:\n{path}",
            )
            self.status.showMessage(f"Exported WAV → {path}", 5000)

        except RuntimeError as exc:
            dlg.close()
            if "cancel" in str(exc).lower():
                self.status.showMessage("Export cancelled.", 2500)
            else:
                QMessageBox.warning(self, "Export Error", str(exc))
        except Exception as exc:
            dlg.close()
            QMessageBox.warning(self, "Export Error", str(exc))


def run_app():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Koke16-Bit Studio")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
