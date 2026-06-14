# CLAUDE.md

> Guidance for Claude Code working in this repository. Read this fully at the start of every session before writing code. The detailed **what to build** lives in the PRD (see §Project Context). This file covers **how to work**.

## Project Context

This is a **fully local, offline speech-to-text dictation tool for Windows**.

The user presses a global hotkey (`Ctrl + Win`) anywhere in Windows, speaks, and the transcribed + cleaned-up text is typed into whatever text field has focus. Everything runs locally — no cloud APIs.

**The full spec is the PRD.** Treat it as the source of truth. Always follow the PRD's phase order and acceptance criteria.

## Confirmed Stack (do not swap without asking)

- **Language:** Python 3.10+
- **STT engine:** whisper.cpp (lightweight C++) — via `pywhispercpp` bindings or a bundled `whisper.cpp` binary
- **Default model:** `ggml-base.en` (configurable to `small.en` / `medium.en`)
- **LLM cleanup:** Ollama at `http://localhost:11434` (model name configurable), in scope for v1
- **Global hotkey:** `Ctrl + Win` (configurable)
- **Packaging:** PyInstaller → single `.exe`, plus a `run.bat` for dev
- **Target OS:** Windows only

## Golden Rules

1. **Phase 1 reliability beats everything.** A flaky hotkey or text injection makes the whole tool useless. Do not add features until the core capture → transcribe → inject loop is rock solid and meets the PRD's Phase 1 acceptance criteria (10/10 successful trials).
2. **Build in PRD phase order.** Phase 0 → 1 → 2 → 3 → 4. Do not jump ahead.
3. **Everything is config-driven.** Hotkey, model path, Ollama URL/model, silence threshold — all live in `config.yaml`. No hardcoded paths or magic values.
4. **Stay local and offline.** Never introduce a cloud STT API or any paid/online dependency. Free and open-source only.
5. **Fail gracefully.** If Ollama is unreachable, fall back to raw transcript. If the model is missing, give a clear error, not a stack trace.

## Workflow Expectations

- **Commit after every meaningful change**, and tag a commit at the end of each phase (e.g. `phase-1-complete`). The user explicitly does not want to lose progress.
- **Plan before large changes.** For any multi-file change, briefly state the plan first, then execute.
- **Verify, don't assume.** After implementing a piece, actually run it (or write/run a quick test) before claiming it works. The final deliverable must be a built `.exe` with a filled-in test checklist proving it was run.
- **Keep changes scoped.** Touch only what the current task needs. Don't refactor unrelated code mid-task.
- **Ask when genuinely blocked** (e.g. an ambiguous design choice, a hotkey conflict), but make reasonable assumptions for small decisions and note them.

## Code Conventions

- Follow the repo structure in the PRD (`src/` with `main.py`, `hotkey.py`, `audio.py`, `transcribe.py`, `cleanup.py`, `inject.py`, `overlay.py`).
- Keep modules single-purpose and importable.
- Add docstrings to public functions and a short comment for any non-obvious logic.
- Use type hints.
- No secrets or absolute machine-specific paths in committed code.

## Text Injection Notes (high-risk area — handle with care)

- Prefer **clipboard-paste** injection for Unicode safety.
- **Always restore the user's previous clipboard contents** after pasting.
- Provide a keystroke-typing method as a fallback.
- Test injection across at least 3 apps (Notepad, a browser field, a chat app).

## Definition of Done (v1)

- [ ] Global `Ctrl+Win` hotkey works system-wide (configurable).
- [ ] Mic capture with hold-to-talk + toggle modes and silence auto-stop.
- [ ] whisper.cpp transcription with configurable model.
- [ ] Ollama cleanup pass, toggleable, with raw-text fallback.
- [ ] Reliable text injection (clipboard + keystroke fallback, clipboard restored).
- [ ] Listening/transcribing indicator + system tray (pause/exit/settings).
- [ ] `config.yaml` drives all tunables.
- [ ] `run.bat` (dev) + built `.exe` + desktop shortcut.
- [ ] `README.md` with setup (Ollama install + `ollama pull`, mic permissions, GPU notes), run, and build instructions.
- [ ] Test checklist filled in, showing the tool was actually run and passed.

## Common Commands (fill in / update as the project takes shape)

```bash
# Dev run
./run.bat

# Or manually
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python src/main.py

# Build the .exe
pyinstaller build.spec
```
