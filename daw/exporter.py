"""Offline WAV renderer for Koke16-Bit Studio.

Renders the project to a numpy buffer (or directly to a WAV file)
by synthesising every note with the same waveforms used by the
real-time playback engine.  Supports exporting multiple loops.
Now renders **stereo** output with per-track panning and instrument
presets (ADSR, vibrato, filter).
"""

from __future__ import annotations

import wave
from typing import Callable

import numpy as np

from daw.models import Project
from daw.instruments import get_preset
from daw.audio import synthesize_note   # single synthesis path shared with playback


# ─── Loop-window helper (mirrors audio.py) ────────────────────────────

def _dynamic_loop_window(project: Project) -> tuple[int, int]:
    """Compute the loop range from all notes across all tracks."""
    min_start: int | None = None
    max_end = 0
    for track in project.tracks:
        for note in track.notes:
            if min_start is None:
                min_start = note.start_tick
            else:
                min_start = min(min_start, note.start_tick)
            max_end = max(max_end, note.start_tick + note.length_tick)
    if max_end <= 0 or min_start is None:
        return 0, max(16, project.ticks_per_beat * 4)
    if max_end <= min_start:
        return min_start, min_start + 1
    return min_start, max_end


def _loop_window(project: Project) -> tuple[int, int]:
    if project.loop_mode == "timeline":
        return 0, 256
    if project.loop_mode == "custom":
        return 0, max(1, project.custom_loop_ticks)
    return _dynamic_loop_window(project)


# ─── Render ────────────────────────────────────────────────────────────

def render_project(
    project: Project,
    loops: int = 1,
    sample_rate: int = 44100,
    progress_callback: Callable[[int, str], None] | None = None,
) -> np.ndarray:
    """Render the whole project to a float32 **stereo** buffer.

    Parameters
    ----------
    project : Project
        The project to render.
    loops : int
        Number of times to repeat the loop region (≥ 1).
    sample_rate : int
        Output sample rate (default 44 100).
    progress_callback : callable, optional
        ``(percent: int, message: str) -> None``

    Returns
    -------
    np.ndarray
        Stereo float32 array of shape ``(N, 2)`` with values in ``[-1, 1]``.
    """
    loops = max(1, loops)

    loop_start, loop_end = _loop_window(project)
    loop_ticks = max(1, loop_end - loop_start)

    # Seconds per tick
    spt = 60.0 / (project.bpm * project.ticks_per_beat)

    # Total duration
    total_ticks = loop_ticks * loops
    total_seconds = total_ticks * spt
    total_samples = int(total_seconds * sample_rate) + sample_rate  # +1s safety

    # Stereo buffer: (N, 2)
    buf = np.zeros((total_samples, 2), dtype=np.float32)

    if progress_callback:
        progress_callback(5, "Preparing render\u2026")

    # Determine active tracks (respect mute/solo)
    soloed = [t for t in project.tracks if t.solo]
    if soloed:
        active_tracks = [t for t in soloed if t.notes]
    else:
        active_tracks = [t for t in project.tracks if t.notes and not t.muted]

    # Count total notes to render for progress
    total_notes = 0
    for track in active_tracks:
        notes_in_range = [n for n in track.notes
                          if loop_start <= n.start_tick < loop_end]
        total_notes += len(notes_in_range) * loops
    rendered_notes = 0

    for track in active_tracks:
        notes_in_range = [n for n in track.notes
                          if loop_start <= n.start_tick < loop_end]
        if not notes_in_range:
            continue

        preset = get_preset(track.instrument_name)
        # Pan: -1.0 (left) .. +1.0 (right)
        left_gain = min(1.0, 1.0 - track.pan)
        right_gain = min(1.0, 1.0 + track.pan)

        for loop_i in range(loops):
            tick_offset = loop_i * loop_ticks

            for note in notes_in_range:
                # Note start relative to loop start + loop offset
                rel_tick = (note.start_tick - loop_start) + tick_offset
                start_s = rel_tick * spt
                dur_s = max(0.04, note.length_tick * spt)
                vel_amp = max(0.05, min(1.0, note.velocity / 127.0)) * track.volume
                note_end_tick = note.start_tick + note.length_tick
                apply_attack = not (loop_i > 0 and note.start_tick == loop_start)
                apply_release = not (loop_i < loops - 1 and note_end_tick >= loop_end)

                mono = synthesize_note(
                    track.waveform,
                    note.midi_note,
                    dur_s,
                    amp=vel_amp,
                    preset=preset,
                    apply_attack=apply_attack,
                    apply_release=apply_release,
                    sample_rate=sample_rate,
                )

                start_idx = int(start_s * sample_rate)
                end_idx = start_idx + len(mono)

                if start_idx >= total_samples:
                    continue
                if end_idx > total_samples:
                    mono = mono[: total_samples - start_idx]
                    end_idx = total_samples

                buf[start_idx:end_idx, 0] += mono * left_gain
                buf[start_idx:end_idx, 1] += mono * right_gain

                rendered_notes += 1
                if progress_callback and total_notes > 0:
                    pct = 5 + int(90 * rendered_notes / total_notes)
                    progress_callback(
                        min(95, pct),
                        f"Rendering note {rendered_notes}/{total_notes}\u2026",
                    )

    # Trim trailing silence (no extra tail pad for seamless loops)
    mag = np.max(np.abs(buf), axis=1)
    last_nonzero = np.flatnonzero(mag > 1e-6)
    if last_nonzero.size > 0:
        buf = buf[: last_nonzero[-1] + 1]
    else:
        buf = buf[:sample_rate]  # 1 second of silence if nothing rendered

    # Normalize to avoid clipping (per-channel aware)
    peak = float(np.max(np.abs(buf)))
    if peak > 1.0:
        buf /= peak
    elif peak > 0:
        # Gentle boost if quiet
        buf *= min(1.0 / peak, 2.0)
        np.clip(buf, -1.0, 1.0, out=buf)

    if progress_callback:
        progress_callback(100, "Render complete.")

    return buf


# ─── WAV writer ────────────────────────────────────────────────────────

def export_wav(
    path: str,
    project: Project,
    loops: int = 1,
    sample_rate: int = 44100,
    progress_callback: Callable[[int, str], None] | None = None,
) -> None:
    """Render and write a 16-bit **stereo** WAV file."""
    buf = render_project(project, loops, sample_rate, progress_callback)

    # buf is (N, 2) float32 — interleave to [L0, R0, L1, R1, ...]
    stereo_16 = np.clip(buf * 32767, -32768, 32767).astype(np.int16)
    interleaved = np.ascontiguousarray(stereo_16)

    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(interleaved.tobytes())
