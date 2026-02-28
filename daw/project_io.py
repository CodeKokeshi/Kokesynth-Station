from __future__ import annotations

import base64
import json

from daw.models import NoteEvent, Project, Track


MAGIC_HEADER = "KOKESTUDIO::PROJECT::1"


class ProjectFormatError(Exception):
    pass


def _project_to_dict(project: Project) -> dict:
    return {
        "bpm": int(project.bpm),
        "ticks_per_beat": int(project.ticks_per_beat),
        "loop_mode": str(project.loop_mode),
        "custom_loop_ticks": int(project.custom_loop_ticks),
        "selected_track_index": int(project.selected_track_index),
        "tracks": [
            {
                "name": track.name,
                "instrument_name": track.instrument_name,
                "waveform": track.waveform,
                "volume": float(track.volume),
                "notes": [
                    {
                        "start_tick": int(note.start_tick),
                        "length_tick": int(note.length_tick),
                        "midi_note": int(note.midi_note),
                        "velocity": int(note.velocity),
                    }
                    for note in track.notes
                ],
            }
            for track in project.tracks
        ],
    }


def _project_from_dict(data: dict) -> Project:
    project = Project(
        bpm=int(data.get("bpm", 120)),
        ticks_per_beat=int(data.get("ticks_per_beat", 4)),
        loop_mode=str(data.get("loop_mode", "dynamic")),
        custom_loop_ticks=int(data.get("custom_loop_ticks", 64)),
        selected_track_index=int(data.get("selected_track_index", -1)),
        tracks=[],
    )

    for track_data in data.get("tracks", []):
        notes = [
            NoteEvent(
                start_tick=int(note_data.get("start_tick", 0)),
                length_tick=max(1, int(note_data.get("length_tick", 1))),
                midi_note=int(note_data.get("midi_note", 60)),
                velocity=int(note_data.get("velocity", 100)),
            )
            for note_data in track_data.get("notes", [])
        ]
        project.tracks.append(
            Track(
                name=str(track_data.get("name", "Track")),
                instrument_name=str(track_data.get("instrument_name", "Unknown")),
                waveform=str(track_data.get("waveform", "square")),
                volume=float(track_data.get("volume", 0.8)),
                notes=notes,
            )
        )

    if not (0 <= project.selected_track_index < len(project.tracks)):
        project.selected_track_index = -1

    return project


def save_kokestudio_file(
    path: str,
    project: Project,
    session_state: dict,
):
    data = {
        "project": _project_to_dict(project),
        "session_state": session_state,
    }
    raw_json = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    encoded = base64.urlsafe_b64encode(raw_json.encode("utf-8")).decode("ascii")
    content = f"{MAGIC_HEADER}\n{encoded}"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def load_kokestudio_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()

    if len(lines) < 2 or lines[0].strip() != MAGIC_HEADER:
        raise ProjectFormatError("Invalid .kokestudio file header.")

    encoded = "".join(lines[1:]).strip()
    if not encoded:
        raise ProjectFormatError("Missing project payload.")

    try:
        decoded = base64.urlsafe_b64decode(encoded.encode("ascii"))
        data = json.loads(decoded.decode("utf-8"))
    except Exception as exc:
        raise ProjectFormatError(f"Could not decode project payload: {exc}") from exc

    if not isinstance(data, dict):
        raise ProjectFormatError("Project payload is not a valid object.")

    project = _project_from_dict(data.get("project", {}))
    session_state = data.get("session_state", {})
    if not isinstance(session_state, dict):
        session_state = {}

    # Backward compatibility with earlier save payload keys.
    if not session_state:
        legacy_editor = data.get("editor_state", {})
        legacy_ui = data.get("ui_state", {})
        if isinstance(legacy_editor, dict):
            session_state["editor"] = legacy_editor
        if isinstance(legacy_ui, dict) and "play_start_tick" in legacy_ui:
            session_state["play_start_tick"] = legacy_ui.get("play_start_tick", 0)

    return {
        "project": project,
        "session_state": session_state,
    }
