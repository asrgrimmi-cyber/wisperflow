# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Read this fully at the start of every session before writing code. The detailed **what to build** lives in the PRD (see §Project Context). This file covers **how to work**.

## Project Context

This is a **fully local, offline speech-to-text dictation tool for Windows**.

The user presses a global hotkey (`Ctrl + Win`) anywhere in Windows, speaks, and the transcribed + cleaned-up text is typed into whatever text field has focus. Everything runs locally — no cloud APIs.

**The full spec is the PRD.** Treat it as the source of truth. Always follow the PRD's phase order and acceptance criteria.

## Confirmed Stack (do not swap without asking)

- **Language:** Python 3.10+
- **STT engine:** OpenAI Whisper (via GPU server or local CPU fallback)
  - GPU server: PyTorch + Whisper on separate machine (Linux/WSL or Windows)
  - Local CPU: `openai-whisper` package with tiny model (~1 GB VRAM)
- **Default models:** Remote GPU uses `medium.en` (5 GB VRAM); local CPU fallback uses `tiny`
- **LLM cleanup:** Ollama at `http://localhost:11434` (optional, disabled by default)
- **UI:** PyQt5 with floating island pill (pause/resume, settings, exit)
- **Text-to-speech:** edge-tts (read text aloud with separate hotkey)
- **Global hotkey:** `Ctrl + Win` (configurable in config.yaml)
- **Text injection:** Clipboard paste (restores clipboard) with keystroke fallback
- **Packaging:** PyInstaller → single `.exe`, plus `run.bat` and `wisper.bat` for dev/deployment
- **Target OS:** Windows (client); Linux/WSL/Windows (GPU server)

## Golden Rules

1. **Phase 1 reliability beats everything.** A flaky hotkey or text injection makes the whole tool useless. Do not add features until the core capture → transcribe → inject loop is rock solid and meets the PRD's Phase 1 acceptance criteria (10/10 successful trials).
2. **Build in PRD phase order.** Phase 0 → 1 → 2 → 3 → 4. Do not jump ahead.
3. **Everything is config-driven.** Hotkey, model path, Ollama URL/model, silence threshold — all live in `config.yaml`. No hardcoded paths or magic values.
4. **Stay local and offline.** Never introduce a cloud STT API or any paid/online dependency. Free and open-source only.
5. **Fail gracefully.** If Ollama is unreachable, fall back to raw transcript. If the model is missing, give a clear error, not a stack trace.

## Workflow Expectations

- **Commit after every meaningful change**, and tag a commit at the end of each phase (e.g. `phase-1-complete`). The user explicitly does not want to lose progress.
- **Plan before large changes.** For any multi-file change, briefly state the plan first, then execute.
- **Verify, don't assume.** After implementing a piece, actually run it locally (see "Testing & Debugging" §) and verify it works. The final deliverable must be a built `.exe` with a test checklist proving it was run.
- **Keep changes scoped.** Touch only what the current task needs. Don't refactor unrelated code mid-task.
- **Ask when genuinely blocked** (e.g. an ambiguous design choice, a hotkey conflict), but make reasonable assumptions for small decisions and note them.
- **Setup wizard (`setup.py`)**: Used for first-time user setup, auto-detects GPU, creates venv, installs deps. Touch this carefully — changing it affects all end users.

## Code Conventions

- **Module structure:** Single-purpose modules in `src/` — each handles one concern (hotkey, audio, transcription, injection, UI).
- **Config-driven everything:** All tunable behavior lives in `config.yaml`. Never hardcode paths, timeouts, models, or hotkeys.
- **Docstrings & type hints:** Public functions have docstrings; type hints are used throughout.
- **Error handling:** Graceful fallbacks (e.g., remote GPU unreachable → local CPU; Ollama down → raw transcript).
- **No machine-specific or secret paths:** Use relative paths; all absolute paths must be generated at runtime via `_app_dir()` or config.
- **Imports:** Keep module imports lean. Client code (`src/`) does not import from `server/` and vice versa.

## Text Injection Notes (high-risk area — handle with care)

- Prefer **clipboard-paste** injection for Unicode safety.
- **Always restore the user's previous clipboard contents** after pasting.
- Provide a keystroke-typing method as a fallback.
- Test injection across at least 3 apps (Notepad, a browser field, a chat app).

## Definition of Done (v1)

Refer to `README.md` for full deployment and setup details. Core requirements:

- [x] Global `Ctrl+Win` hotkey works system-wide (configurable in config.yaml).
- [x] Mic capture with hold-to-talk + toggle modes and silence auto-stop.
- [x] Whisper transcription via remote GPU server (Flask) + local CPU fallback.
- [x] Optional Ollama cleanup pass (toggleable, disabled by default).
- [x] Reliable text injection (clipboard paste with restore, keystroke fallback).
- [x] PyQt5 floating island UI with pause/resume, settings, exit.
- [x] `config.yaml` drives all tunables (hotkey, models, timeouts, injection method, TTS).
- [x] Interactive setup wizard (`setup.py`) with GPU auto-detect.
- [x] `run.bat` (client dev/deploy) + `wisper.bat` (combined same-machine launcher).
- [x] Built `.exe` via PyInstaller with desktop shortcut.
- [x] Text-to-speech playback (edge-tts, separate hotkey).
- [ ] Full end-to-end test checklist filled in, showing the tool was actually run and passed all trials.

## Architecture

The system has three main components:

1. **GPU Server** (`server/whisper_server.py`): Flask API that runs Whisper transcription on a GPU machine. Separate deployment or same machine.
2. **Client** (`src/`): PyQt5 application that captures audio, sends to server, cleans up text, injects into focused window.
3. **Config** (`config.yaml`): Drives all runtime behavior — hotkey, transcription model, Ollama settings, TTS, injection method.

### Pipeline Flow

```
Hotkey pressed → AudioCapture → WhisperTranscriber (remote GPU or local CPU) → OllamaCleanup (optional) → TextInjector → Floating Island UI
```

### Key Modules

- **`main.py`**: Entry point. Initializes hotkey listener, audio capture, transcriber, UI. Orchestrates the pipeline.
- **`hotkey.py`**: Global Ctrl+Win hotkey listener (or custom hotkey from config).
- **`audio.py`**: Mic capture with silence detection and auto-stop.
- **`transcribe.py`**: Whisper transcription — tries remote GPU server first, falls back to local CPU model.
- **`cleanup.py`**: Optional Ollama LLM pass to clean up raw transcripts (disabled by default).
- **`inject.py`**: Text injection via clipboard paste (restores clipboard after) or keystroke typing fallback.
- **`floating_island.py`**: PyQt5 floating pill UI with pause/resume, settings, exit.
- **`tts.py`**: Text-to-speech playback (edge-tts), separate hotkey to read transcribed text aloud.
- **`first_run.py`**: Setup wizard for first-time initialization.

### GPU Server Architecture

The `server/` folder contains a Flask transcription service:

- Runs on `http://localhost:8765` (same machine) or a remote LAN machine.
- Client sends audio (WAV file or raw PCM float32) via HTTP POST.
- Server loads Whisper model (configurable: tiny/base/small/medium.en/large) on startup.
- Client health-checks the server; if unreachable, falls back to local CPU Whisper (tiny model).

## Configuration (config.yaml)

This file is the source of truth for all runtime behavior. Key sections:

```yaml
hotkey:
  key: "ctrl+win"               # Global hotkey to start/stop recording
  mode: "hold"                  # "hold" (press to start, release to stop) or "toggle"

audio:
  sample_rate: 16000
  silence_threshold: 0.02       # Audio level below this is silence
  silence_duration: 1.5         # Auto-stop after 1.5s of silence

whisper:
  model_name: "tiny"            # Local fallback model (tiny/base/small/medium)
  language: "en"
  remote_url: "http://192.168.0.5:8765"  # Empty = local CPU only
  remote_timeout: 30            # Seconds to wait for GPU server

ollama:
  enabled: false                # Optional cleanup pass
  base_url: "http://localhost:11434"
  model: "llama2"
  timeout: 10

injection:
  method: "clipboard"           # "clipboard" (safe, Unicode-friendly) or "keystroke"
  restore_clipboard: true       # Always restore user's clipboard after injection

tts:
  hotkey: "ctrl+win+r"          # Hotkey to read transcribed text aloud
  voice: "en-US-GuyNeural"
  rate: "+0%"                   # Speech rate adjustment

_setup_complete: true           # Set by setup.py; don't edit manually
```

Editing `config.yaml` takes effect on next app restart. No code changes needed.

## Common Commands

```bash
# First-time setup (interactive wizard, creates venv, installs deps, configures GPU/CPU)
python setup.py

# Dev run (single machine with GPU server + client, or CPU-only)
wisper.bat              # If same machine: starts GPU server in background, then client
# OR
run.bat                 # If remote GPU server or CPU-only: just runs client

# Manually (without setup wizard)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python src/main.py      # Launch client app

# Build standalone .exe
pip install pyinstaller
pyinstaller build.spec
# Output: dist/Wisper.exe

# Deploy GPU server (Linux/WSL on separate machine)
cd server/
bash setup.sh --model medium.en --port 8765
# OR manually:
pip install flask openai-whisper numpy torch
python whisper_server.py --model medium.en --port 8765
```

## Testing & Debugging

### Local testing without setup wizard:
1. Ensure `config.yaml` has `_setup_complete: true`.
2. Set `whisper.remote_url` to empty string to use local CPU transcription.
3. Run `python src/main.py`.

### Debugging hotkey issues:
- Hotkey requires running as Administrator on Windows.
- Test with `Ctrl+Win` (default) or check `config.yaml` for custom hotkey.
- See `src/hotkey.py` for the listener logic.

### Testing text injection:
- Open Notepad, a browser input field, and a chat app (3+ apps per CLAUDE.md § Text Injection Notes).
- Press the hotkey, speak, and verify text pastes correctly.
- If injection fails, check `injection.method` in config (clipboard vs keystroke fallback).
- Verify clipboard is restored after injection (check by pasting after a transcription).

### Testing GPU server connection:
```bash
curl http://<IP>:8765/health
# Should return: {"status": "ok", "model_loaded": true}

# Send test audio
curl -X POST http://<IP>:8765/transcribe -F "audio=@sample.wav"
```

If server is unreachable, client auto-falls back to local CPU (slow but functional).
