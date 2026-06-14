# 📋 PRD — Local Speech-to-Text Dictation Tool (Windows)
> **For Claude Code:** This is a complete, self-contained build spec. Read the whole document before starting. Build in the phase order given. Do not skip Phase 1 acceptance criteria before moving on. Commit to git after every phase. Target a **working, tested ****`.exe`** as the final deliverable — not a prototype.

## 1. Goal & Summary
Build a **fully local, offline speech-to-text dictation tool for Windows** that works as seamlessly as commercial tools (e.g. Wispr Flow, Windows Voice Typing). The user presses a **global hotkey (****`Ctrl + Win`****)** anywhere in Windows, speaks, and the transcribed text is typed into whatever text field currently has focus. A local LLM (Ollama) cleans up the raw transcript before it is inserted. Ships as a launchable `.exe` (plus a `run.bat` for development) with a desktop shortcut.

**Hard constraints:**
- 100% local / offline. No cloud STT APIs. All free/open-source components.
- Windows PC target. Final artifact must be a `.bat` or `.exe` the user can double-click.
- Must be a complete, tested project — not a snippet.

## 2. Confirmed Technical Decisions
| Decision | Choice | Notes |
|----------|--------|-------|
| STT engine | **whisper.cpp** (lightweight C++) | Use `pywhispercpp` bindings or shell out to a bundled `whisper.cpp` binary. CPU-friendly; GGML/GGUF models. |
| Default model | `ggml-base.en` (start), allow `small.en`/`medium.en` via config | User has GPU + overnight compute available for larger models if desired. |
| LLM cleanup | **In scope for v1** | Punctuation, capitalization, formatting of raw transcript. |
| LLM backend | **Ollama** | Local OpenAI-compatible / native API at `http://localhost:11434`. Model name configurable (e.g. `llama3.1`). |
| Language | Python 3.10+ | Packaged with PyInstaller. |
| Global hotkey | `Ctrl + Win` | Use `keyboard` or `pynput`; verify it works system-wide. |

## 3. User Flow
1. User launches the app (`.exe` / shortcut) → it runs in the background with a system tray icon.
2. User focuses any text field in any app.
3. User presses & holds (or toggles) **`Ctrl + Win`** → a small on-screen "Listening…" indicator appears.
4. App captures microphone audio until release / silence / second hotkey press.
5. whisper.cpp transcribes audio → raw text.
6. Raw text is sent to Ollama for cleanup (punctuation/formatting).
7. Cleaned text is injected into the focused field via simulated keystrokes / clipboard paste.
8. Indicator disappears. Ready for next dictation.

## 4. Build Phases
### Phase 0 — Research & Scaffold
- Confirm `whisper.cpp` build/binding path on Windows (prebuilt binary vs `pywhispercpp` pip install). Document the chosen approach in `README.md`.
- Create repo structure (see §6), `requirements.txt`, `config.yaml` (hotkey, model path, Ollama URL/model, silence threshold).
- Set up git; commit scaffold.

### Phase 1 — Base Integration (PRIMARY FOCUS — get this rock solid first)
1. **Global hotkey listener** — `Ctrl + Win` triggers capture system-wide. Support both hold-to-talk and toggle modes (config flag).
2. **Audio capture** — record from default mic (`sounddevice`/`pyaudio`), 16kHz mono WAV in memory. Stop on hotkey release, silence timeout, or toggle-off.
3. **Transcription** — feed audio to whisper.cpp, return raw text.
4. **Text injection** — insert text into the currently focused field (clipboard-paste method preferred for reliability with Unicode; keystroke method as fallback).
5. **Listening indicator** — minimal always-on-top overlay or tray-state change showing idle / listening / transcribing.

**Phase 1 acceptance criteria:** From any focused text field, pressing `Ctrl+Win`, speaking a sentence, and releasing results in the (raw) transcribed sentence appearing in that field, end-to-end, reliably across 10 trials.

### Phase 2 — Local LLM Cleanup (Ollama)
- POST raw transcript to Ollama (`/api/generate` or OpenAI-compat `/v1/chat/completions`) with a cleanup prompt (fix punctuation/capitalization/filler words; do **not** add new content).
- Config: `llm_enabled` toggle, model name, timeout, and graceful fallback to raw text if Ollama is unreachable.
- Keep latency reasonable; show "transcribing/formatting" state.

### Phase 3 — Packaging
- `run.bat` to launch in dev (creates/activates venv, installs deps, runs `main.py`).
- PyInstaller spec → single-file `.exe` bundling the whisper.cpp binary + default GGML model (or first-run model download with offline-friendly fallback).
- Generate a desktop shortcut (or document the one-step way to create it).
- Optional: register to run on Windows startup (config flag).

### Phase 4 — Execution & Testing
- `README.md`: setup, prerequisites (Ollama install + `ollama pull <model>`, mic permissions, optional GPU/CUDA notes for larger whisper models), how to run, how to build the `.exe`.
- Test checklist: hotkey works system-wide; capture starts/stops correctly; transcription accuracy on a sample script; LLM cleanup on/off; text injection across ≥3 apps (Notepad, browser field, chat app); Ollama-down fallback; `.exe` launches on a clean machine.
- Document measured latency (capture→insert) and known limitations.

## 5. Functional Requirements
- **FR1** Global `Ctrl+Win` hotkey, configurable, works in any focused app.
- **FR2** Mic capture with hold-to-talk and toggle modes + silence auto-stop.
- **FR3** Local whisper.cpp transcription, configurable model.
- **FR4** Ollama-based cleanup pass, toggleable, with raw-text fallback.
- **FR5** Reliable text injection into the focused field (clipboard + keystroke fallback).
- **FR6** Visual listening/transcribing indicator + system tray control (pause/exit/settings).
- **FR7** External `config.yaml` for all tunables; no hardcoded paths.
- **FR8** Packaged `.exe` + dev `run.bat` + desktop shortcut.

## 6. Suggested Repo Structure
```
speech-to-text/
├── src/
│   ├── main.py            # entry point, tray, orchestration
│   ├── hotkey.py          # global hotkey listener
│   ├── audio.py           # mic capture + silence detection
│   ├── transcribe.py      # whisper.cpp wrapper
│   ├── cleanup.py         # Ollama client + prompt
│   ├── inject.py          # focused-field text injection
│   └── overlay.py         # listening indicator / tray
├── models/                # GGML whisper model(s)
├── config.yaml
├── requirements.txt
├── run.bat
├── build.spec             # PyInstaller
└── README.md
```

## 7. Non-Goals (v1)
- Multi-language UI (English-focused; whisper model still supports others if swapped).
- Real-time streaming transcription (batch on stop is acceptable for v1).
- Cloud sync, accounts, or telemetry.

## 8. Notes for Claude Code
- Prioritize **Phase 1 reliability** above features. A flaky hotkey or injection makes the whole tool unusable.
- Prefer clipboard-paste injection for Unicode safety; restore the user's previous clipboard contents after pasting.
- Make every external dependency (model path, Ollama URL/model, hotkey) config-driven.
- Push every change to git so progress isn't lost; tag a commit at the end of each phase.
- Deliver with the `.exe` built and a filled-in test checklist showing it was actually run and passed.
