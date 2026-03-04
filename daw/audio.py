from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
import pygame
import pygame.mixer

from daw.models import Project
from daw.instruments import get_preset, SynthPreset


# ── Shared synthesis (used by both audio.py and exporter.py) ────────

def synthesize_note(
    waveform: str,
    midi_note: int,
    duration: float,
    amp: float = 1.0,
    preset: SynthPreset | None = None,
    apply_attack: bool = True,
    apply_release: bool = True,
    sample_rate: int = 44100,
) -> np.ndarray:
    """Synthesise a single note as float32 samples in [-1, 1].

    Applies per-instrument ADSR envelope, vibrato, and low-pass filter.
    """
    if preset is None:
        preset = SynthPreset()

    n_samples = max(1, int(sample_rate * duration))
    t = np.arange(n_samples, dtype=np.float32) / sample_rate
    freq = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))

    # ── Vibrato (pitch modulation) ──────────────────────────────────
    if preset.vibrato_rate > 0 and preset.vibrato_depth > 0:
        # vibrato_depth is in semitones; convert to freq multiplier
        vib = preset.vibrato_depth * np.sin(
            2.0 * np.pi * preset.vibrato_rate * t
        ).astype(np.float32)
        instantaneous_freq = freq * (2.0 ** (vib / 12.0))
        # Phase accumulation for vibrato
        phase = np.cumsum(instantaneous_freq / sample_rate).astype(np.float32)
    else:
        phase = (t * freq).astype(np.float32)

    # ── Waveform generation ─────────────────────────────────────────
    if waveform == "square":
        wave = np.where(phase % 1.0 < 0.5, 1.0, -1.0).astype(np.float32)
    elif waveform == "pulse25":
        wave = np.where(phase % 1.0 < 0.25, 1.0, -1.0).astype(np.float32)
    elif waveform == "pulse12":
        wave = np.where(phase % 1.0 < 0.125, 1.0, -1.0).astype(np.float32)
    elif waveform == "sawtooth":
        wave = (2.0 * (phase % 1.0) - 1.0).astype(np.float32)
    elif waveform == "triangle":
        ph = phase % 1.0
        wave = (2.0 * np.abs(2.0 * ph - 1.0) - 1.0).astype(np.float32)
    elif waveform == "noise":
        rng = np.random.default_rng(seed=(midi_note * 31 + int(duration * 1000)))
        wave = rng.uniform(-1.0, 1.0, n_samples).astype(np.float32)
        # Noise uses a simple decay from the preset
        decay_samples = max(1, int(max(preset.decay, duration) * sample_rate))
        if decay_samples < n_samples:
            decay_env = np.ones(n_samples, dtype=np.float32)
            decay_env[decay_samples:] = 0.0
            ramp = np.linspace(1.0, 0.0, decay_samples, dtype=np.float32)
            decay_env[:decay_samples] = ramp
            wave *= decay_env
        else:
            wave *= np.linspace(1.0, 0.0, n_samples, dtype=np.float32)
    else:  # sine
        wave = np.sin(2.0 * np.pi * phase).astype(np.float32)

    # ── Low-pass filter (simple 1-pole IIR) ─────────────────────────
    if 0 < preset.filter_cutoff < 1.0:
        # Map cutoff (0–1) to a frequency, then to alpha
        # cutoff=1.0 → no filter, cutoff=0.0 → very dark
        cutoff_freq = 200.0 + preset.filter_cutoff * (sample_rate * 0.45 - 200.0)
        rc = 1.0 / (2.0 * np.pi * cutoff_freq)
        dt = 1.0 / sample_rate
        alpha = dt / (rc + dt)
        # Apply using vectorized lfilter-style
        _simple_lowpass_inplace(wave, alpha)

    # ── ADSR envelope ───────────────────────────────────────────────
    env = _build_adsr(
        n_samples, sample_rate, preset,
        apply_attack=apply_attack,
        apply_release=apply_release,
    )
    wave *= env

    # ── Final amplitude + clipping ──────────────────────────────────
    wave *= amp
    np.clip(wave, -1.0, 1.0, out=wave)

    # Tiny tail to avoid clicks
    if apply_release:
        tail = np.zeros(int(0.005 * sample_rate), dtype=np.float32)
        wave = np.concatenate([wave, tail])

    return wave


def _simple_lowpass_inplace(buf: np.ndarray, alpha: float) -> None:
    """In-place single-pole low-pass filter (fast C-loop via numpy)."""
    # Fallback to a vectorized approximation for speed:
    # For very short buffers a simple loop is fine,
    # but for longer ones we approximate using a multi-pass convolution.
    if len(buf) < 2:
        return
    # Number of passes for a steeper rolloff (2-pole approximation)
    for _ in range(2):
        prev = buf[0]
        for i in range(1, len(buf)):
            prev = prev + alpha * (buf[i] - prev)
            buf[i] = prev


def _build_adsr(
    n_samples: int,
    sample_rate: int,
    preset: SynthPreset,
    apply_attack: bool = True,
    apply_release: bool = True,
) -> np.ndarray:
    """Build an ADSR envelope array."""
    env = np.ones(n_samples, dtype=np.float32)

    a_samples = int(preset.attack * sample_rate) if apply_attack else 0
    d_samples = int(preset.decay * sample_rate)
    r_samples = int(preset.release * sample_rate) if apply_release else 0
    sustain = preset.sustain

    # Clamp: attack + decay must not exceed total length
    ad = a_samples + d_samples
    if ad > n_samples:
        ratio = n_samples / max(ad, 1)
        a_samples = int(a_samples * ratio)
        d_samples = n_samples - a_samples

    # Attack: 0 → 1
    if a_samples > 0:
        env[:a_samples] = np.linspace(0.0, 1.0, a_samples, dtype=np.float32)

    # Decay: 1 → sustain
    if d_samples > 0 and sustain < 1.0:
        d_start = a_samples
        d_end = d_start + d_samples
        if d_end > n_samples:
            d_end = n_samples
            d_samples = d_end - d_start
        if d_samples > 0:
            env[d_start:d_end] = np.linspace(1.0, sustain, d_samples, dtype=np.float32)

    # Sustain: hold at sustain level
    sustain_start = a_samples + d_samples
    if sustain_start < n_samples and sustain < 1.0:
        env[sustain_start:] = sustain

    # Release: sustain → 0
    if r_samples > 0:
        r_samples = min(r_samples, n_samples)
        # Blend the release over the last r_samples
        release_curve = np.linspace(1.0, 0.0, r_samples, dtype=np.float32)
        env[-r_samples:] *= release_curve

    return env


class AudioEngine(QObject):
    position_changed = pyqtSignal(int)

    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.sample_rate = 44100
        self.current_tick = 0
        self.playing = False
        self.paused = False
        self._solo_track_index: int | None = None
        self._start_tick: int | None = None
        self._loop_cycle_index = 0
        self._cache: dict = {}

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self.available = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(self.sample_rate, -16, 2, 512)
                pygame.mixer.init()
            pygame.mixer.set_num_channels(64)
            self.available = True
        except Exception:
            self.available = False

    def set_bpm(self, bpm: int) -> None:
        self.project.bpm = max(40, min(260, bpm))
        if self.playing:
            self._timer.setInterval(self._tick_ms())

    def start(self, solo_track_index: int | None = None, start_tick: int | None = None) -> None:
        if not self.available:
            return
        self._solo_track_index = solo_track_index
        self._start_tick = start_tick
        loop_start, loop_end = self._loop_window()
        self.playing = True
        self.paused = False
        self._loop_cycle_index = 0
        self.current_tick = self._resolve_start_tick(loop_start, loop_end)
        self.position_changed.emit(self.current_tick)
        self._timer.start(self._tick_ms())

    def pause(self) -> None:
        if not self.available or not self.playing:
            return
        self._timer.stop()
        pygame.mixer.pause()
        self.playing = False
        self.paused = True

    def resume(self) -> None:
        if not self.available or not self.paused:
            return
        pygame.mixer.unpause()
        self._timer.start(self._tick_ms())
        self.playing = True
        self.paused = False

    def switch_playback_mode(self, solo_track_index: int | None) -> None:
        """Switch between all-track and solo playback without moving current tick."""
        self._solo_track_index = solo_track_index
        if self.available:
            pygame.mixer.stop()

    def stop(self) -> None:
        self.playing = False
        self.paused = False
        loop_start, loop_end = self._loop_window()
        self.current_tick = self._resolve_start_tick(loop_start, loop_end)
        self.position_changed.emit(self.current_tick)
        self._timer.stop()
        if self.available:
            pygame.mixer.stop()
        self._solo_track_index = None

    def preview_note(self, waveform: str, midi_note: int, velocity: int = 100,
                     instrument_name: str = "") -> None:
        if not self.available:
            return
        duration = 0.25
        amp = max(0.05, min(1.0, velocity / 127.0)) * 0.6
        preset = get_preset(instrument_name) if instrument_name else SynthPreset()
        sound = self._get_sound(waveform, midi_note, duration, preset=preset)
        ch = pygame.mixer.find_channel(True)
        if ch:
            ch.set_volume(amp, amp)  # stereo: equal L/R for preview
            ch.play(sound)

    def _tick_ms(self) -> int:
        return max(15, int(60000 / (self.project.bpm * self.project.ticks_per_beat)))

    def _tick(self) -> None:
        loop_start, loop_end = self._loop_window()
        for track in self._playback_tracks():
            if track.muted:
                continue
            preset = get_preset(track.instrument_name)
            for note in track.notes:
                if note.start_tick == self.current_tick:
                    dur = max(0.04, note.length_tick / self.project.ticks_per_beat * 60.0 / self.project.bpm)
                    vel_amp = max(0.05, min(1.0, note.velocity / 127.0))
                    note_end_tick = note.start_tick + note.length_tick
                    apply_attack = not (
                        note.start_tick == loop_start
                        and self._loop_cycle_index > 0
                    )
                    apply_release = not (note_end_tick >= loop_end)
                    sound = self._get_sound(
                        track.waveform,
                        note.midi_note,
                        dur,
                        preset=preset,
                        apply_attack=apply_attack,
                        apply_release=apply_release,
                    )
                    ch = pygame.mixer.find_channel(True)
                    if ch is not None:
                        # Stereo panning: pan -1..+1 → left/right volume
                        vol = vel_amp * track.volume
                        left_vol = vol * min(1.0, 1.0 - track.pan)
                        right_vol = vol * min(1.0, 1.0 + track.pan)
                        ch.set_volume(left_vol, right_vol)
                        ch.play(sound)

        next_tick = self.current_tick + 1
        if next_tick >= loop_end:
            self.current_tick = loop_start
            self._loop_cycle_index += 1
        else:
            self.current_tick = next_tick
        self.position_changed.emit(self.current_tick)

    def _dynamic_loop_window(self) -> tuple[int, int]:
        min_start = None
        max_end = 0
        for track in self._playback_tracks():
            for note in track.notes:
                if min_start is None:
                    min_start = note.start_tick
                else:
                    min_start = min(min_start, note.start_tick)
                max_end = max(max_end, note.start_tick + note.length_tick)

        if max_end <= 0 or min_start is None:
            default_len = max(16, self.project.ticks_per_beat * 4)
            return 0, default_len

        if max_end <= min_start:
            return min_start, min_start + 1

        return min_start, max_end

    def _loop_window(self) -> tuple[int, int]:
        if self.project.loop_mode == "timeline":
            # Keep legacy minimum timeline span, but don't truncate longer songs.
            _, dyn_end = self._dynamic_loop_window()
            return 0, max(256, dyn_end)
        if self.project.loop_mode == "custom":
            return 0, max(1, self.project.custom_loop_ticks)
        return self._dynamic_loop_window()

    def _resolve_start_tick(self, loop_start: int, loop_end: int) -> int:
        if loop_end <= loop_start:
            return loop_start
        if self._start_tick is None:
            return loop_start
        return max(loop_start, min(loop_end - 1, self._start_tick))

    def _playback_tracks(self) -> list:
        if self._solo_track_index is not None:
            if 0 <= self._solo_track_index < len(self.project.tracks):
                return [self.project.tracks[self._solo_track_index]]
            return []
        # Check if any track has solo enabled
        soloed = [t for t in self.project.tracks if t.solo]
        if soloed:
            return soloed
        return self.project.tracks

    def _get_sound(
        self,
        waveform: str,
        midi_note: int,
        duration: float,
        preset: SynthPreset | None = None,
        apply_attack: bool = True,
        apply_release: bool = True,
    ):
        """Return a cached stereo Sound at full volume (volume applied via channel)."""
        p = preset or SynthPreset()
        key = (
            waveform,
            midi_note,
            int(duration * 1000),
            int(apply_attack),
            int(apply_release),
            id(type(p)),  # preset identity for cache discrimination
            int(p.attack * 10000),
            int(p.decay * 10000),
            int(p.sustain * 100),
            int(p.release * 10000),
            int(p.vibrato_rate * 100),
            int(p.vibrato_depth * 100),
            int(p.filter_cutoff * 100),
        )
        if key not in self._cache:
            wave = synthesize_note(
                waveform, midi_note, duration,
                amp=1.0, preset=p,
                apply_attack=apply_attack,
                apply_release=apply_release,
                sample_rate=self.sample_rate,
            )
            # Convert mono float32 → stereo int16 for pygame
            samples_16 = np.ascontiguousarray(wave * 32767, dtype=np.int16)
            # Interleave for stereo (identical L/R — panning done via channel volume)
            stereo = np.column_stack([samples_16, samples_16]).flatten()
            stereo = np.ascontiguousarray(stereo)
            self._cache[key] = pygame.mixer.Sound(stereo)
        return self._cache[key]
