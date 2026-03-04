from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NoteEvent:
    start_tick: int
    length_tick: int
    midi_note: int
    velocity: int = 100


@dataclass
class Track:
    name: str
    instrument_name: str
    waveform: str
    volume: float = 0.8
    pan: float = 0.0            # -1.0 (full left) to +1.0 (full right)
    muted: bool = False
    solo: bool = False
    notes: list[NoteEvent] = field(default_factory=list)


@dataclass
class Project:
    bpm: int = 120
    ticks_per_beat: int = 4
    loop_mode: str = "dynamic"   # dynamic | timeline | custom
    custom_loop_ticks: int = 64
    tracks: list[Track] = field(default_factory=list)
    selected_track_index: int = -1

    @property
    def selected_track(self) -> Track | None:
        if 0 <= self.selected_track_index < len(self.tracks):
            return self.tracks[self.selected_track_index]
        return None
