from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QRadioButton,
    QVBoxLayout,
)

from daw.instruments import INSTRUMENT_LIBRARY


class AddTrackDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Piano Roll Track")
        self.resize(420, 360)

        layout = QVBoxLayout(self)

        title = QLabel("Choose an instrument")
        title.setStyleSheet("font-size: 15px; font-weight: 700;")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        for inst in INSTRUMENT_LIBRARY:
            item = QListWidgetItem(f"{inst['name']}  ·  {inst['family']}")
            item.setData(Qt.ItemDataRole.UserRole, inst)
            self.list_widget.addItem(item)
        self.list_widget.setCurrentRow(0)
        self.list_widget.itemDoubleClicked.connect(lambda _: self.accept())
        layout.addWidget(self.list_widget, 1)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def selected_instrument(self) -> dict[str, str] | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)


class AudioToMusicDialog(QDialog):
    def __init__(self, track_names: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Audio → Music")
        self.resize(460, 460)

        layout = QVBoxLayout(self)

        title = QLabel("Choose conversion mode + destination")
        title.setStyleSheet("font-size: 15px; font-weight: 700;")
        layout.addWidget(title)

        self.chk_auto_multitrack = QCheckBox("Auto-retrofy to multiple tracks (Lead/Bass/Harmony/Drums)")
        self.chk_auto_multitrack.setChecked(True)
        layout.addWidget(self.chk_auto_multitrack)

        self.chk_auto_select_instruments = QCheckBox("Auto-select instruments for generated tracks")
        self.chk_auto_select_instruments.setChecked(True)
        layout.addWidget(self.chk_auto_select_instruments)

        self.lbl_single_instr = QLabel("Single-track instrument (used when auto-multitrack is OFF):")
        self.lbl_single_instr.setStyleSheet("color:#9a9a9a; font-size:11px;")
        layout.addWidget(self.lbl_single_instr)

        self.list_widget = QListWidget()
        for inst in INSTRUMENT_LIBRARY:
            item = QListWidgetItem(f"{inst['name']}  ·  {inst['family']}")
            item.setData(Qt.ItemDataRole.UserRole, inst)
            self.list_widget.addItem(item)
        self.list_widget.setCurrentRow(0)
        layout.addWidget(self.list_widget, 1)

        self.radio_new = QRadioButton("Create new track")
        self.radio_overwrite = QRadioButton("Write to existing track")
        self.radio_new.setChecked(True)
        layout.addWidget(self.radio_new)
        layout.addWidget(self.radio_overwrite)

        row = QHBoxLayout()
        row.addWidget(QLabel("Target Track"))
        self.combo_tracks = QComboBox()
        self.combo_tracks.addItems(track_names)
        self.combo_tracks.setEnabled(False)
        row.addWidget(self.combo_tracks, 1)
        layout.addLayout(row)

        self.chk_auto_multitrack.toggled.connect(self._update_destination_controls)
        self.chk_auto_select_instruments.toggled.connect(self._update_destination_controls)
        self.radio_new.toggled.connect(self._update_destination_controls)
        self.radio_overwrite.toggled.connect(self._update_destination_controls)
        self._update_destination_controls()

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _update_destination_controls(self):
        allow_overwrite_target = self.radio_overwrite.isChecked() and not self.chk_auto_multitrack.isChecked()
        self.combo_tracks.setEnabled(allow_overwrite_target)

        if self.chk_auto_multitrack.isChecked():
            self.radio_new.setChecked(True)
            self.radio_overwrite.setEnabled(False)
            self.chk_auto_select_instruments.setEnabled(True)
            self.list_widget.setEnabled(False)
            self.lbl_single_instr.setEnabled(False)
        else:
            self.radio_overwrite.setEnabled(True)
            self.chk_auto_select_instruments.setEnabled(False)
            self.list_widget.setEnabled(True)
            self.lbl_single_instr.setEnabled(True)

    def selected_instrument(self) -> dict[str, str] | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def create_new_track(self) -> bool:
        return self.radio_new.isChecked()

    def target_track_name(self) -> str:
        return self.combo_tracks.currentText()

    def auto_multitrack(self) -> bool:
        return self.chk_auto_multitrack.isChecked()

    def auto_select_instruments(self) -> bool:
        return self.chk_auto_select_instruments.isChecked()


class RoleInstrumentDialog(QDialog):
    def __init__(self, role_name: str, default_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Choose Instrument: {role_name}")
        self.resize(420, 360)

        layout = QVBoxLayout(self)
        title = QLabel(f"Choose instrument for {role_name}")
        title.setStyleSheet("font-size: 15px; font-weight: 700;")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        default_index = 0
        for idx, inst in enumerate(INSTRUMENT_LIBRARY):
            item = QListWidgetItem(f"{inst['name']}  ·  {inst['family']}")
            item.setData(Qt.ItemDataRole.UserRole, inst)
            self.list_widget.addItem(item)
            if inst["name"] == default_name:
                default_index = idx

        self.list_widget.setCurrentRow(default_index)
        self.list_widget.itemDoubleClicked.connect(lambda _: self.accept())
        layout.addWidget(self.list_widget, 1)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def selected_instrument(self) -> dict[str, str] | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)
