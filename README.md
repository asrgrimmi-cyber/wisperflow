# Wisper

**Local, offline speech-to-text dictation for Windows.**

Press a hotkey anywhere, speak, and the transcribed text is typed into the focused window. No cloud APIs, no subscriptions — everything runs on your hardware.

---

## Two Ways to Use Wisper

| Setup | Best For | Speed | What You Need |
|---|---|---|---|
| **Same machine** | GPU laptops / workstations | ~0.5s | Windows + NVIDIA GPU |
| **Two machines** | Desktop + separate GPU server | ~0.5s | Windows client + any GPU machine on LAN |
| **CPU only** | No GPU at all | ~5-15s | Windows (any hardware) |

---

## Quick Start

```bash
python setup.py
```

The setup wizard auto-detects your GPU and walks you through everything:

```
  ====================================================
         Wisper — Speech-to-Text Setup Wizard
  ====================================================

  ── Step 1: Python Environment ──────────────────
    Creating virtual environment... [OK]
    Installing dependencies... [OK]

  ── Step 2: Transcription Engine ────────────────

    GPU detected: NVIDIA RTX 4060 Laptop GPU, 8192 MiB

    This machine has a GPU. How do you want to use it?

      1) Same machine — run GPU server + client together (easiest)
      2) This is the CLIENT — connect to a DIFFERENT GPU server
      3) CPU only — don't use the GPU

    Enter choice: _
```

After setup, run:

```bash
wisper.bat          # Same machine (starts server + client)
run.bat             # Remote server or CPU only
```

---

## Setup A: Same Machine (GPU Laptop/Workstation)

You have a Windows machine with an NVIDIA GPU. Both the transcription server and the dictation client run on the same machine.

```
┌─────────────────────────────────────┐
│          Your Machine               │
│                                     │
│  ┌───────────┐    ┌──────────────┐  │
│  │  Wisper    │───>│  GPU Server  │  │
│  │  Client    │<───│  (localhost) │  │
│  │  (PyQt UI) │    │  Whisper on  │  │
│  └───────────┘    │  CUDA        │  │
│                    └──────────────┘  │
└─────────────────────────────────────┘
```

### What `setup.py` does:

1. Creates a virtual environment
2. Installs client dependencies (PyQt5, keyboard, sounddevice, etc.)
3. Detects your NVIDIA GPU and CUDA version
4. Installs PyTorch with the correct CUDA build
5. Installs server dependencies (Flask, openai-whisper)
6. Lets you choose the Whisper model (medium.en recommended)
7. Creates `wisper.bat` — a single launcher that starts the GPU server in the background, waits for it to load, then launches the client

### Running:

```bash
wisper.bat    # Starts everything — server loads model, then client opens
```

The floating island pill appears. Press **Ctrl+Win** or click it to dictate.

When you close the client, the server shuts down automatically.

---

## Setup B: Two Machines (Client + Remote GPU Server)

Your Windows machine (client) sends audio over the network to a separate GPU machine (server). The GPU machine can be Linux, Windows, or WSL — anything with an NVIDIA GPU.

```
┌──────────────┐         ┌──────────────────┐
│  Windows PC  │  HTTP   │  GPU Machine     │
│  (Client)    │────────>│  (Server)        │
│              │<────────│  RTX 5070 Ti     │
│  PyQt UI     │  JSON   │  Whisper medium  │
│  Microphone  │         │  Flask :8765     │
└──────────────┘         └──────────────────┘
        LAN (192.168.x.x)
```

### On the GPU machine (one-time setup):

Copy the `server/` folder to the GPU machine, then:

```bash
# Option 1: One-click setup script
bash setup.sh --model medium.en --port 8765

# Option 2: Manual
pip install flask openai-whisper numpy
pip install torch --index-url https://download.pytorch.org/whl/cu121
sudo apt install ffmpeg
python whisper_server.py --model medium.en --port 8765
```

Verify it works:

```bash
curl http://localhost:8765/health
# → {"status": "ok", "model_loaded": true}
```

Open the firewall:

```bash
sudo ufw allow 8765
```

Run in background (production):

```bash
nohup python whisper_server.py --model medium.en --port 8765 > server.log 2>&1 &
```

### On the Windows machine (client):

```bash
python setup.py
# Choose: "This is the CLIENT — connect to a DIFFERENT GPU server"
# Enter the GPU machine's IP and port
```

Or configure manually in `config.yaml`:

```yaml
whisper:
  remote_url: "http://192.168.0.5:8765"
```

Then run:

```bash
run.bat
```

If the GPU server goes down, Wisper automatically falls back to local CPU transcription (slower but never breaks).

---

## Setup C: CPU Only

No GPU at all. Uses the `tiny` Whisper model locally. Slower (~5-15s per clip) but works on any Windows machine.

```bash
python setup.py
# Choose: "CPU only"
run.bat
```

---

## GPU Server API Reference

The server is a simple Flask app with two endpoints:

### `GET /health`

```bash
curl http://<IP>:8765/health
```

```json
{ "status": "ok", "model_loaded": true }
```

### `POST /transcribe`

**File upload:**

```bash
curl -X POST http://<IP>:8765/transcribe -F "audio=@recording.wav"
```

**Raw PCM (float32, 16kHz mono):**

```python
import requests, numpy as np
audio = np.array(samples, dtype=np.float32)
r = requests.post("http://<IP>:8765/transcribe", data=audio.tobytes())
print(r.json())
```

**Response:**

```json
{ "text": "Hello, how are you doing today?", "time": 0.601 }
```

### Whisper Models

| Model | VRAM | Speed | Use Case |
|---|---|---|---|
| `tiny` | ~1 GB | Fastest | CPU fallback, quick tests |
| `base` | ~1 GB | Fast | Light GPU |
| `small` | ~2 GB | Medium | Balanced |
| `medium.en` | ~5 GB | Good | **Recommended for English** |
| `large` | ~10 GB | Slow | Multilingual, highest accuracy |

---

## Configuration

All settings in `config.yaml`:

```yaml
hotkey:
  key: "ctrl+win"            # Global hotkey
  mode: "hold"                # "hold" or "toggle"

audio:
  sample_rate: 16000
  channels: 1
  silence_threshold: 0.02
  silence_duration: 1.5       # Auto-stop after this much silence

whisper:
  model_name: "tiny"          # Local fallback model
  language: "en"
  device: "cpu"               # "cpu" or "cuda"
  remote_url: ""              # GPU server URL (empty = local only)
  remote_timeout: 30

ollama:
  enabled: false              # Optional LLM text cleanup
  base_url: "http://localhost:11434"
  model: "llama2"
  timeout: 10

injection:
  method: "clipboard"         # "clipboard" or "keystroke"
  restore_clipboard: true
```

---

## Project Structure

```
Wisper/
├── src/                          # Client application
│   ├── main.py                   # Entry point & pipeline
│   ├── audio.py                  # Mic capture + silence detection
│   ├── transcribe.py             # GPU remote + local CPU Whisper
│   ├── cleanup.py                # Optional Ollama LLM cleanup
│   ├── inject.py                 # Text injection (clipboard paste)
│   ├── hotkey.py                 # Global hotkey (Ctrl+Win)
│   └── floating_island.py        # PyQt5 floating pill UI
├── server/                       # GPU server (deploy separately or same machine)
│   ├── whisper_server.py         # Flask transcription API
│   ├── setup.sh                  # One-click server setup (Linux)
│   └── requirements.txt
├── config.yaml                   # All settings
├── setup.py                      # Interactive setup wizard
├── requirements.txt              # Client dependencies
├── build.spec                    # PyInstaller config
├── run.bat                       # Client launcher
└── wisper.bat                    # Combined launcher (same machine)
```

---

## Build Standalone .exe

```bash
pip install pyinstaller
pyinstaller build.spec
```

Output: `dist/Wisper.exe`

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "No module named PyQt5" | Run `setup.py` or `pip install PyQt5` |
| GPU server unreachable | Check firewall, run `curl http://<IP>:8765/health` |
| Slow transcription | You're on CPU fallback — set up GPU server |
| Text not pasting | Focus a text field before speaking |
| Hotkey not working | Run as administrator |
| DLL load error on startup | Harmless if GPU server is healthy (local torch fallback) |
| Server won't start | Check `nvidia-smi`, install ffmpeg, verify CUDA |
