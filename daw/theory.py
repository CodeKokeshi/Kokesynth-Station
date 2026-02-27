"""SmartTheoryFixer – context-aware music-theory post-processor.

Cleans up raw CQT transcription output by applying scale-aware
corrections **without** destroying intentional dissonance or character.

Design principles
-----------------
* Detect the key / scale from the note histogram (Krumhansl-Schmuckler).
* Preserve "blue notes" common in retro soundtracks (b3 in major, b5).
* Only snap *short, quiet* out-of-scale notes; leave long or loud ones
  (they are intentional).
* Fill melodic gaps with scale-aware linear interpolation that respects
  the direction of the preceding melody contour.
* All behaviour is tuneable via a ``strictness`` parameter (0 = raw,
  1 = strict theory enforcement).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Sequence

from daw.models import NoteEvent


# ─── Scale / key data ──────────────────────────────────────────────────

# Pitch-class profiles (Krumhansl-Kessler) – used for key detection.
_MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

# Semitone intervals for common scales (relative to root)
_MAJOR_INTERVALS = {0, 2, 4, 5, 7, 9, 11}
_MINOR_INTERVALS = {0, 2, 3, 5, 7, 8, 10}

# Retro "blue note" extensions – tolerated extra pitch classes
_BLUE_NOTES_MAJOR = {3, 6}      # minor 3rd + tritone (b5) in a major key
_BLUE_NOTES_MINOR = {6, 1}      # tritone + b9 (passing tones in minor)

# Note names for debug / display
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


# ─── Key detection ─────────────────────────────────────────────────────

def _detect_key(notes: Sequence[NoteEvent]) -> tuple[int, str, set[int]]:
    """Return ``(root_pc, quality, scale_pcs)`` detected from *notes*.

    Uses the Krumhansl-Schmuckler algorithm: correlate the
    pitch-class histogram of the input with the major/minor profile
    rotated to every possible root.
    """
    if not notes:
        return 0, "major", _MAJOR_INTERVALS

    # Build weighted pitch-class histogram (weight by duration * velocity)
    hist = [0.0] * 12
    for n in notes:
        pc = n.midi_note % 12
        hist[pc] += n.length_tick * (n.velocity / 127.0)

    best_root = 0
    best_quality = "major"
    best_corr = -999.0

    for root in range(12):
        # Rotate histogram so 'root' aligns with index 0
        rotated = [hist[(root + i) % 12] for i in range(12)]
        for quality, profile in [("major", _MAJOR_PROFILE), ("minor", _MINOR_PROFILE)]:
            # Pearson correlation
            mean_r = sum(rotated) / 12.0
            mean_p = sum(profile) / 12.0
            num = sum((r - mean_r) * (p - mean_p) for r, p in zip(rotated, profile))
            den_r = math.sqrt(sum((r - mean_r) ** 2 for r in rotated)) or 1e-9
            den_p = math.sqrt(sum((p - mean_p) ** 2 for p in profile)) or 1e-9
            corr = num / (den_r * den_p)
            if corr > best_corr:
                best_corr = corr
                best_root = root
                best_quality = quality

    if best_quality == "major":
        scale_pcs = {(best_root + i) % 12 for i in _MAJOR_INTERVALS}
    else:
        scale_pcs = {(best_root + i) % 12 for i in _MINOR_INTERVALS}

    return best_root, best_quality, scale_pcs


def _get_blue_pcs(root: int, quality: str) -> set[int]:
    """Return pitch classes that qualify as 'blue notes'."""
    raw = _BLUE_NOTES_MAJOR if quality == "major" else _BLUE_NOTES_MINOR
    return {(root + offset) % 12 for offset in raw}


# ─── Helpers ───────────────────────────────────────────────────────────

def _nearest_scale_tone(midi_note: int, scale_pcs: set[int]) -> int:
    """Snap *midi_note* to the closest pitch class in *scale_pcs*."""
    pc = midi_note % 12
    if pc in scale_pcs:
        return midi_note
    # Search ±1, ±2, ... semitones
    for delta in range(1, 7):
        if (pc + delta) % 12 in scale_pcs:
            return midi_note + delta
        if (pc - delta) % 12 in scale_pcs:
            return midi_note - delta
    return midi_note  # fallback (shouldn't happen with 7-note scales)


def _median_length(notes: Sequence[NoteEvent]) -> float:
    """Median note length – used as the 'typical' duration baseline."""
    if not notes:
        return 4.0
    lengths = sorted(n.length_tick for n in notes)
    mid = len(lengths) // 2
    if len(lengths) % 2 == 0:
        return (lengths[mid - 1] + lengths[mid]) / 2.0
    return float(lengths[mid])


def _median_velocity(notes: Sequence[NoteEvent]) -> float:
    if not notes:
        return 90.0
    vels = sorted(n.velocity for n in notes)
    mid = len(vels) // 2
    return float(vels[mid])


# ─── SmartTheoryFixer ──────────────────────────────────────────────────

class SmartTheoryFixer:
    """Context-aware music-theory post-processor.

    Parameters
    ----------
    strictness : float
        0.0 = leave everything untouched (raw import).
        1.0 = strict theory enforcement (robot-clean).
        Default 0.65 balances clean output with character preservation.

    Typical usage::

        fixer = SmartTheoryFixer(strictness=0.65)
        clean_lead = fixer.fix(lead_events, role="lead")
        clean_bass = fixer.fix(bass_events, role="bass")
    """

    def __init__(self, strictness: float = 0.65) -> None:
        self.strictness = max(0.0, min(1.0, strictness))

    # ─── public API ────────────────────────────────────────────────

    def fix(
        self,
        notes: list[NoteEvent],
        role: str = "lead",
    ) -> list[NoteEvent]:
        """Apply theory cleaning to *notes* for a given track *role*.

        Steps performed (in order):
        1. Detect key / scale from note content.
        2. Snap out-of-scale "glitch" notes (short + quiet).
        3. Remove duplicate-pitch overlaps.
        4. Fill melodic gaps with interpolated passing tones (lead only).
        """
        if not notes or self.strictness <= 0.0:
            return notes

        # Work on copies so caller's data isn't mutated unexpectedly
        notes = [NoteEvent(n.start_tick, n.length_tick, n.midi_note, n.velocity)
                 for n in notes]

        # Sort by start time
        notes.sort(key=lambda n: n.start_tick)

        # 1) Detect key from ALL notes (best accuracy from full set)
        root, quality, scale_pcs = _detect_key(notes)
        blue_pcs = _get_blue_pcs(root, quality)

        # 2) Chromatic snap (glitch notes)
        notes = self._snap_glitches(notes, scale_pcs, blue_pcs)

        # 3) Remove duplicate-pitch overlaps
        notes = self._remove_overlaps(notes)

        # 4) Melodic gap fill (lead & harmony only – bass should stay sparse)
        if role in ("lead", "harmony") and self.strictness > 0.3:
            notes = self._fill_gaps(notes, scale_pcs)

        return notes

    def fix_multitrack(
        self,
        split: dict[str, list[NoteEvent]],
    ) -> dict[str, list[NoteEvent]]:
        """Convenience: fix every pitched track in a split dict.

        Drums are never theory-fixed (they don't have pitched semantics).
        The detected key uses ALL pitched notes combined for accuracy.
        """
        # Combine pitched notes for global key detection
        pitched = []
        for role in ("lead", "bass", "harmony"):
            pitched.extend(split.get(role, []))

        if not pitched or self.strictness <= 0.0:
            return split

        root, quality, scale_pcs = _detect_key(pitched)
        blue_pcs = _get_blue_pcs(root, quality)

        result: dict[str, list[NoteEvent]] = {}
        for role in ("lead", "bass", "harmony"):
            events = split.get(role, [])
            if not events:
                result[role] = events
                continue

            # Copy
            events = [NoteEvent(n.start_tick, n.length_tick, n.midi_note, n.velocity)
                      for n in events]
            events.sort(key=lambda n: n.start_tick)

            events = self._snap_glitches(events, scale_pcs, blue_pcs)
            events = self._remove_overlaps(events)
            if role in ("lead", "harmony") and self.strictness > 0.3:
                events = self._fill_gaps(events, scale_pcs)

            result[role] = events

        # Pass drums through untouched
        result["drums"] = split.get("drums", [])
        return result

    # ─── internal steps ────────────────────────────────────────────

    def _snap_glitches(
        self,
        notes: list[NoteEvent],
        scale_pcs: set[int],
        blue_pcs: set[int],
    ) -> list[NoteEvent]:
        """Snap short/quiet out-of-scale notes to the nearest scale tone.

        Long or loud chromatic notes are presumed intentional and kept.
        Blue notes (b3 in major, b5) are always preserved.
        """
        if not notes:
            return notes

        med_len = _median_length(notes)
        med_vel = _median_velocity(notes)

        # Thresholds scale with strictness:
        # At strictness=1.0: snap anything shorter than 1.2× median
        # At strictness=0.5: snap only things shorter than 0.4× median
        len_threshold = med_len * (0.2 + self.strictness * 1.0)
        vel_threshold = med_vel * (0.4 + self.strictness * 0.4)

        cleaned: list[NoteEvent] = []
        for note in notes:
            pc = note.midi_note % 12

            if pc in scale_pcs:
                # Already in scale → keep as-is
                cleaned.append(note)
                continue

            if pc in blue_pcs:
                # Blue note → always preserve (retro character)
                cleaned.append(note)
                continue

            # Out of scale – decide: intentional or glitch?
            is_long = note.length_tick >= len_threshold
            is_loud = note.velocity >= vel_threshold

            if is_long or is_loud:
                # Intentional dissonance → keep
                cleaned.append(note)
            else:
                # Glitch → snap to nearest scale tone
                note.midi_note = _nearest_scale_tone(note.midi_note, scale_pcs)
                cleaned.append(note)

        return cleaned

    def _remove_overlaps(self, notes: list[NoteEvent]) -> list[NoteEvent]:
        """Merge or trim notes with the same pitch that overlap in time."""
        if len(notes) < 2:
            return notes

        notes.sort(key=lambda n: (n.midi_note, n.start_tick))
        cleaned: list[NoteEvent] = []

        for note in notes:
            if cleaned and cleaned[-1].midi_note == note.midi_note:
                prev = cleaned[-1]
                prev_end = prev.start_tick + prev.length_tick
                # Overlapping or adjacent → merge
                if note.start_tick <= prev_end + 1:
                    new_end = max(prev_end, note.start_tick + note.length_tick)
                    prev.length_tick = new_end - prev.start_tick
                    prev.velocity = max(prev.velocity, note.velocity)
                    continue
            cleaned.append(note)

        # Re-sort by time for downstream consumers
        cleaned.sort(key=lambda n: n.start_tick)
        return cleaned

    def _fill_gaps(
        self,
        notes: list[NoteEvent],
        scale_pcs: set[int],
    ) -> list[NoteEvent]:
        """Fill large melodic gaps with scale-aware passing tones.

        Analyses the direction of the preceding 3 notes and continues
        the contour through the gap using scale tones.

        Only activates when strictness > 0.3 and the gap is
        significantly larger than the median note length.
        """
        if len(notes) < 3:
            return notes

        med_len = _median_length(notes)
        # Only fill gaps bigger than this threshold
        gap_threshold = max(2, int(med_len * (2.5 - self.strictness * 1.5)))
        # How long should filler notes be?  Roughly half the median
        filler_len = max(1, int(med_len * 0.5))

        sorted_pcs = sorted(scale_pcs)

        result: list[NoteEvent] = list(notes)
        inserts: list[NoteEvent] = []

        for i in range(3, len(result)):
            prev_end = result[i - 1].start_tick + result[i - 1].length_tick
            gap = result[i].start_tick - prev_end

            if gap < gap_threshold:
                continue

            # Determine contour direction from previous 3 notes
            pitches = [result[i - 3].midi_note, result[i - 2].midi_note, result[i - 1].midi_note]
            diffs = [pitches[1] - pitches[0], pitches[2] - pitches[1]]
            avg_dir = sum(diffs) / len(diffs)

            if abs(avg_dir) < 0.5:
                # Melody is roughly flat → don't fill
                continue

            going_up = avg_dir > 0
            cur_pitch = pitches[-1]
            target_pitch = result[i].midi_note
            fill_start = prev_end

            # Generate at most a few passing tones (don't overdo it)
            max_fillers = min(4, gap // max(1, filler_len + 1))
            filled = 0

            while filled < max_fillers and fill_start + filler_len < result[i].start_tick:
                # Step to next scale tone in the contour direction
                next_pitch = self._next_scale_pitch(cur_pitch, sorted_pcs, going_up)

                # Safety: don't overshoot the target note
                if going_up and next_pitch > target_pitch + 4:
                    break
                if not going_up and next_pitch < target_pitch - 4:
                    break

                vel = int(result[i - 1].velocity * (0.5 + 0.3 * self.strictness))
                vel = max(40, min(120, vel))

                inserts.append(NoteEvent(
                    start_tick=fill_start,
                    length_tick=filler_len,
                    midi_note=next_pitch,
                    velocity=vel,
                ))

                cur_pitch = next_pitch
                fill_start += filler_len + 1
                filled += 1

        result.extend(inserts)
        result.sort(key=lambda n: n.start_tick)
        return result

    @staticmethod
    def _next_scale_pitch(current: int, sorted_pcs: list[int], going_up: bool) -> int:
        """Return the next scale pitch above/below *current*."""
        pc = current % 12
        octave = current // 12

        if going_up:
            # Find the next higher pitch class in the scale
            for spc in sorted_pcs:
                if spc > pc:
                    return octave * 12 + spc
            # Wrap to next octave
            return (octave + 1) * 12 + sorted_pcs[0]
        else:
            # Find the next lower pitch class
            for spc in reversed(sorted_pcs):
                if spc < pc:
                    return octave * 12 + spc
            # Wrap to previous octave
            return (octave - 1) * 12 + sorted_pcs[-1]
