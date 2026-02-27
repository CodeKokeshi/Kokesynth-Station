from __future__ import annotations


INSTRUMENT_LIBRARY: list[dict[str, str]] = [
    {"name": "Generic Saw", "waveform": "sawtooth", "family": "Generic"},
    {"name": "Generic Sine", "waveform": "sine", "family": "Generic"},
    {"name": "Generic Square", "waveform": "square", "family": "Generic"},
    {"name": "Generic Triangle", "waveform": "triangle", "family": "Generic"},
    {"name": "Generic Pulse 25%", "waveform": "pulse25", "family": "Generic"},
    {"name": "Generic Pulse 12.5%", "waveform": "pulse12", "family": "Generic"},
    {"name": "Generic Noise Drum", "waveform": "noise", "family": "Generic"},
    {"name": "NES Square", "waveform": "square", "family": "NES"},
    {"name": "NES Triangle", "waveform": "triangle", "family": "NES"},
    {"name": "NES Pulse 25%", "waveform": "pulse25", "family": "NES"},
    {"name": "NES Noise", "waveform": "noise", "family": "NES"},
    {"name": "Gameboy Square", "waveform": "square", "family": "Gameboy"},
    {"name": "Gameboy Pulse 12.5%", "waveform": "pulse12", "family": "Gameboy"},
]
