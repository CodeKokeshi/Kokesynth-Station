from __future__ import annotations

from dataclasses import dataclass, field

from PyQt6.QtCore import Qt


MODIFIER_MASK = (
    Qt.KeyboardModifier.ShiftModifier
    | Qt.KeyboardModifier.ControlModifier
    | Qt.KeyboardModifier.AltModifier
    | Qt.KeyboardModifier.MetaModifier
)


@dataclass
class KeyBinding:
    modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier
    key: int = int(Qt.Key.Key_unknown)


@dataclass
class ShortcutConfig:
    modifier: Qt.KeyboardModifier = Qt.KeyboardModifier.ShiftModifier
    controller: Qt.KeyboardModifier = Qt.KeyboardModifier.ControlModifier
    box_select: KeyBinding = field(
        default_factory=lambda: KeyBinding(Qt.KeyboardModifier.ShiftModifier, int(Qt.Key.Key_unknown))
    )
    zoom: KeyBinding = field(
        default_factory=lambda: KeyBinding(Qt.KeyboardModifier.ShiftModifier, int(Qt.Key.Key_unknown))
    )
    undo: KeyBinding = field(
        default_factory=lambda: KeyBinding(Qt.KeyboardModifier.ControlModifier, int(Qt.Key.Key_Z))
    )
    redo_primary: KeyBinding = field(
        default_factory=lambda: KeyBinding(Qt.KeyboardModifier.ControlModifier, int(Qt.Key.Key_Y))
    )
    redo_secondary: KeyBinding = field(
        default_factory=lambda: KeyBinding(
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
            int(Qt.Key.Key_Z),
        )
    )
    select_all_notes: KeyBinding = field(
        default_factory=lambda: KeyBinding(Qt.KeyboardModifier.ControlModifier, int(Qt.Key.Key_A))
    )
    delete_primary: KeyBinding = field(
        default_factory=lambda: KeyBinding(Qt.KeyboardModifier.NoModifier, int(Qt.Key.Key_Delete))
    )
    delete_secondary: KeyBinding = field(
        default_factory=lambda: KeyBinding(Qt.KeyboardModifier.NoModifier, int(Qt.Key.Key_Backspace))
    )


def normalize_modifiers(mods: Qt.KeyboardModifier) -> Qt.KeyboardModifier:
    return mods & MODIFIER_MASK


def modifiers_equal(left: Qt.KeyboardModifier, right: Qt.KeyboardModifier) -> bool:
    return normalize_modifiers(left) == normalize_modifiers(right)


def binding_matches(event_key: int, event_mods: Qt.KeyboardModifier, binding: KeyBinding) -> bool:
    if binding.key == int(Qt.Key.Key_unknown):
        return False
    return int(event_key) == int(binding.key) and modifiers_equal(event_mods, binding.modifiers)


def modifier_to_text(mod: Qt.KeyboardModifier) -> str:
    parts = []
    if mod & Qt.KeyboardModifier.ControlModifier:
        parts.append("Ctrl")
    if mod & Qt.KeyboardModifier.ShiftModifier:
        parts.append("Shift")
    if mod & Qt.KeyboardModifier.AltModifier:
        parts.append("Alt")
    if mod & Qt.KeyboardModifier.MetaModifier:
        parts.append("Meta")
    return " + ".join(parts) if parts else "None"


def modifier_from_key(key: int) -> Qt.KeyboardModifier | None:
    key_map = {
        int(Qt.Key.Key_Shift): Qt.KeyboardModifier.ShiftModifier,
        int(Qt.Key.Key_Control): Qt.KeyboardModifier.ControlModifier,
        int(Qt.Key.Key_Alt): Qt.KeyboardModifier.AltModifier,
        int(Qt.Key.Key_Meta): Qt.KeyboardModifier.MetaModifier,
    }
    return key_map.get(int(key))


def key_to_text(key: int) -> str:
    key = int(key)
    if key == int(Qt.Key.Key_Delete):
        return "Delete"
    if key == int(Qt.Key.Key_Backspace):
        return "Backspace"
    if key == int(Qt.Key.Key_Space):
        return "Space"
    if int(Qt.Key.Key_A) <= key <= int(Qt.Key.Key_Z):
        return chr(key)
    if int(Qt.Key.Key_0) <= key <= int(Qt.Key.Key_9):
        return chr(key)
    text = Qt.Key(key).name
    if text.startswith("Key_"):
        text = text[4:]
    return text


def is_pure_modifier_key(key: int) -> bool:
    return int(key) in {
        int(Qt.Key.Key_Shift),
        int(Qt.Key.Key_Control),
        int(Qt.Key.Key_Alt),
        int(Qt.Key.Key_Meta),
    }


def chord_to_binding(keys: list[int]) -> KeyBinding:
    modifiers = Qt.KeyboardModifier.NoModifier
    trigger_key = int(Qt.Key.Key_unknown)
    for key in keys:
        mod = modifier_from_key(key)
        if mod is not None:
            modifiers |= mod
        else:
            trigger_key = int(key)
    return KeyBinding(normalize_modifiers(modifiers), trigger_key)


def binding_to_text(binding: KeyBinding) -> str:
    parts = []
    mod_text = modifier_to_text(binding.modifiers)
    if mod_text != "None":
        parts.append(mod_text)
    if binding.key != int(Qt.Key.Key_unknown):
        parts.append(key_to_text(binding.key))
    return " + ".join(parts) if parts else "None"
