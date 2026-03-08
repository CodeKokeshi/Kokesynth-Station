# Koke16-Bit Studio

Koke16-Bit Studio is a retro-styled desktop DAW for making game music with a 16-bit feel. It combines a piano-roll editor, procedural music generation, audio-to-MIDI transcription, hum-to-music recording, sheet-music reading, WAV export, and sheet export into a single PyQt6 app.

The project is aimed at quick soundtrack sketching: sing or import an idea, split it into usable tracks, clean it up, assign game-style instruments, and export the result.

## What It Can Do

- Record from your microphone with `Hum → Music` and turn a melody into playable note data.
- Import audio files and convert them into one track or auto-split them into Lead, Bass, Harmony, and Drums.
- Generate retro loops by genre and platform flavor.
- Edit notes in a piano roll with playback, undo/redo, selection tools, velocity editing, and track controls.
- Beautify tracks with theory-aware cleanup tools.
- Read music sheets from PDF or image files and convert them through OMR into usable musical data.
- Export projects to `.wav` audio.
- Export sheet music to `.png` or `.pdf`.
- Save and load projects as `.kokestudio` files.
- Switch themes and customize shortcuts.

## Main Features

### Composition and Editing

- Multi-track piano-roll workflow
- Add, duplicate, rename, mute, solo, pan, and rebalance tracks
- Per-track instruments and note editing
- Play all tracks or only the selected track
- Undo/redo support for project and editor actions

### Audio to Music

- Microphone recording with a live waveform monitor
- Audio import for WAV, MP3, FLAC, OGG, and other formats supported by `librosa`
- Auto-retrofy mode that can split imported audio into role-based tracks
- Automatic instrument assignment for generated tracks

### Game-Music Generation

- Genre-aware loop generation
- Hardware-flavor presets such as NES, SNES, and GBA style output
- Built-in instrument library for retro-inspired sounds

### Cleanup and Theory Tools

- `Beautify` for key-aware note cleanup
- `Remove Gaps` to tighten phrasing
- `Balance` to align track lengths
- `Fix Loops` to make loop endings restart more smoothly

### Import and Export

- Save/load `.kokestudio` project files
- Export WAV renders
- Export sheet music to PNG or PDF
- Read PDF/image sheet music through OMR and MusicXML parsing

## Tech Stack

- Python
- PyQt6 for the desktop UI
- NumPy for synthesis and processing
- pygame-ce for playback and mixing
- sounddevice for microphone input and audio-device interaction
- librosa and soundfile for audio loading and transcription
- matplotlib for sheet export
- music21, PyMuPDF, oemer, and OpenCV for sheet reading and OMR

## Requirements

- Python 3.10 or newer
- Git
- A working audio output device for playback
- A microphone if you want to use `Hum → Music`

Windows users can build an `.exe` with PyInstaller. The app also runs directly from source.

Note on Python versions:

- The codebase uses modern type syntax that requires Python 3.10+.
- If the OMR feature gives ONNX runtime or DLL issues on Windows, Python 3.11 or 3.12 is a safer choice than bleeding-edge Python versions.

## Install the Repo

Clone the repository:

```bash
git clone https://github.com/CodeKokeshi/Koke16-bit-Studio.git
cd Koke16-bit-Studio
```

Create and activate a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project requirements:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run the App

From the project root:

```bash
python main.py
```

That launches the desktop app defined by `main.py`, which starts the main window from `daw/main_window.py`.

## Build a Windows Executable

The repository already includes a PyInstaller command in `BUILD.txt`.

First install PyInstaller into your virtual environment:

```bash
python -m pip install pyinstaller
```

Then build from the project root:

```powershell
pyinstaller --onefile --windowed ^
  --icon=Koke16.ico ^
  --name="Kokesynth-Station" ^
  --add-data "assets;assets" ^
  --add-data "Koke16.png;." ^
  main.py
```

Build output:

```text
dist\Kokesynth-Station.exe
```

Notes:

- `--onefile` creates a single executable.
- `--windowed` suppresses the console window.
- `--add-data` bundles the assets folder and app icon resources.
- If you want faster startup and do not mind a folder build, replace `--onefile` with `--onedir`.

## How to Use the App

### 1. Start a Project

When the app opens, you can either:

- create tracks manually with `+ Add Piano Roll Track`
- generate music automatically
- import audio
- hum a melody into the mic
- read a music sheet from a PDF or image
- load an existing `.kokestudio` project

### 2. Build Music Manually

Use `+ Add Piano Roll Track` to add an instrument track from the built-in library. Then edit notes in the piano roll:

- click to place notes
- drag notes to move them
- drag note edges to resize them
- select notes for bulk edits
- play all tracks or only the selected track

Use the track list to manage:

- track name
- instrument
- mute and solo
- volume
- pan
- role labels such as Lead, Bass, Harmony, and Drums

### 3. Use `Hum → Music`

Click `Hum → Music` to start microphone capture. The app shows a live waveform monitor while recording. Click the same button again to stop recording and process the captured audio into music data.

This is useful for sketching melodies quickly without entering notes by hand.

### 4. Use `Import Audio → Music`

Import an audio file and choose one of these workflows:

- convert the audio into a single track
- auto-retrofy it into multiple role-based tracks

You can also let the app auto-select instruments for generated tracks.

### 5. Use `Read Music Sheet`

Import a PDF or image of sheet music. The app runs OMR to interpret the notation, parses the resulting MusicXML, and turns it into usable musical information.

This workflow depends on the OMR stack and is the most environment-sensitive part of the project.

### 6. Generate Music Automatically

Use `Generate Music` to create retro-styled loops from built-in genre presets. This is the fastest way to get a starting arrangement and then refine it in the editor.

### 7. Clean Up the Arrangement

Use the magic toolbar tools:

- `Beautify` to clean notes with music-theory-aware correction
- `Remove Gaps` to tighten phrases
- `Balance` to align track lengths
- `Fix Loops` to improve seamless looping

### 8. Export the Result

When you are happy with the arrangement:

- use `Save Project` to save a `.kokestudio` project
- use `Export WAV` to render audio
- use `Export Music Sheet` to create a PNG or PDF score

## Project File Format

- Project files use the `.kokestudio` extension.
- They contain a base64-encoded JSON payload with a project header and session state.
- Saved data includes BPM, loop settings, selected track, track instruments, note events, and editor/session metadata.

## Project Structure

```text
main.py                  Entry point
daw/main_window.py       Main application window and user workflows
daw/audio.py             Synth engine and playback
daw/pianoroll.py         Piano-roll editor
daw/transcriber.py       Audio-to-note transcription
daw/generator.py         Procedural music generation
daw/theory.py            Beautify and theory helpers
daw/project_io.py        .kokestudio save/load format
daw/exporter.py          WAV export
daw/sheet_export.py      PNG/PDF sheet export
daw/sheet_reader.py      PDF/image OMR pipeline
BUILD.txt                PyInstaller build command
requirements.txt         Runtime dependencies
assets/                  Fonts and SVG icons
```

## Troubleshooting

### OMR or Sheet Reading Fails

If `Read Music Sheet` fails on Windows with ONNX runtime or DLL errors:

- make sure the virtual environment was created cleanly
- reinstall requirements in a fresh venv
- try Python 3.11 or 3.12
- note that the OMR stack is more fragile than the rest of the app

### No Input Device for `Hum → Music`

- check that your microphone is connected and enabled
- verify your OS permissions allow microphone access
- confirm your selected/default audio input device is valid

### No Sound During Playback

- verify your output device is working outside the app
- check mute, solo, volume, and pan settings on each track
- ensure the project actually contains note data

### Build Fails With Missing Asset Errors

- run the build from the project root
- keep `assets`, `Koke16.png`, and `Koke16.ico` in place
- do not remove the `--add-data` flags from the PyInstaller command

## Credits

This project builds on a Python desktop stack that includes PyQt6, librosa, matplotlib, music21, PyMuPDF, OpenCV, pygame-ce, sounddevice, and oemer.