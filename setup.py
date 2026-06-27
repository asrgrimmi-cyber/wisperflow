"""Wisper — Interactive Setup Wizard

Serves two types of users:
  1. Same machine  — GPU laptop, runs client + server together
  2. Two machines  — Client on Windows, GPU server on a separate machine (LAN)

Also handles CPU-only users who have no GPU at all.
"""

import os
import platform
import subprocess
import sys
import time

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.yaml")
VENV_DIR = os.path.join(ROOT, "venv")
REQ_CLIENT = os.path.join(ROOT, "requirements.txt")
REQ_SERVER = os.path.join(ROOT, "server", "requirements.txt")
SERVER_SCRIPT = os.path.join(ROOT, "server", "whisper_server.py")


# ── Helpers ───────────────────────────────────────────────

def banner():
    print()
    print("=" * 56)
    print("        Wisper — Speech-to-Text Setup Wizard")
    print("=" * 56)
    print()
    print("  This wizard will set up Wisper on your machine.")
    print("  It detects your hardware and configures everything.")
    print()


def ask(prompt, default=""):
    suffix = f" [{default}]" if default else ""
    val = input(f"  {prompt}{suffix}: ").strip()
    return val if val else default


def ask_yn(prompt, default="y"):
    val = ask(prompt, default).lower()
    return val in ("y", "yes")


def ask_choice(prompt, options):
    print(f"\n  {prompt}\n")
    for i, (label, _) in enumerate(options, 1):
        print(f"    {i}) {label}")
    print()
    while True:
        choice = input("  Enter choice: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1][1]
        print("  Invalid choice, try again.")


def pip_cmd():
    """Return the pip executable path (venv or system)."""
    venv_pip = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    if os.path.exists(venv_pip):
        return f'"{venv_pip}"'
    venv_pip = os.path.join(VENV_DIR, "Scripts", "pip")
    if os.path.exists(venv_pip):
        return f'"{venv_pip}"'
    return "pip"


def python_cmd():
    """Return the python executable (venv or system)."""
    venv_py = os.path.join(VENV_DIR, "Scripts", "python.exe")
    if os.path.exists(venv_py):
        return f'"{venv_py}"'
    return "python"


def run(cmd, desc=None, quiet=False):
    if desc:
        print(f"  {desc}...")
    kwargs = {"shell": True}
    if quiet:
        kwargs["capture_output"] = True
    result = subprocess.run(cmd, **kwargs)
    return result.returncode == 0


def check_gpu_local():
    """Check if this machine has an NVIDIA GPU with CUDA."""
    try:
        result = subprocess.run(
            "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader",
            shell=True, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def check_cuda_python():
    """Check if PyTorch with CUDA is importable."""
    try:
        result = subprocess.run(
            f'{python_cmd()} -c "import torch; print(torch.cuda.is_available())"',
            shell=True, capture_output=True, text=True, timeout=30,
        )
        return "True" in result.stdout
    except Exception:
        return False


def check_server_health(url, timeout=5):
    """Check if a Wisper GPU server is reachable."""
    try:
        import requests
        resp = requests.get(f"{url}/health", timeout=timeout)
        if resp.ok:
            return resp.json()
    except Exception:
        pass
    return None


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def save_config(config):
    # Preserve readable YAML with comments-style ordering
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


# ── Step 1: Environment ──────────────────────────────────

def step_environment():
    print("── Step 1: Python Environment ──────────────────")
    print()

    if not os.path.exists(VENV_DIR):
        print("  Creating virtual environment...")
        run(f'python -m venv "{VENV_DIR}"')
    else:
        print("  Virtual environment found.")

    print("  Installing client dependencies...")
    run(f'{pip_cmd()} install -q -r "{REQ_CLIENT}"')
    print("  [OK] Client dependencies installed.")


# ── Step 2: Detect hardware & choose mode ────────────────

def step_transcription():
    print()
    print("── Step 2: Transcription Engine ────────────────")

    # Auto-detect GPU
    gpu_info = check_gpu_local()
    if gpu_info:
        print(f"\n  GPU detected: {gpu_info}")
    else:
        print("\n  No NVIDIA GPU detected on this machine.")

    # Choose mode
    if gpu_info:
        mode = ask_choice(
            "This machine has a GPU. How do you want to use it?",
            [
                ("Same machine — run GPU server + client together (easiest)", "same"),
                ("This is the CLIENT — connect to a DIFFERENT GPU server", "remote"),
                ("CPU only — don't use the GPU", "cpu"),
            ],
        )
    else:
        mode = ask_choice(
            "Choose transcription mode:",
            [
                ("Connect to a GPU server on another machine (recommended)", "remote"),
                ("CPU only — no GPU (slower, but works)", "cpu"),
            ],
        )

    config = load_config()

    if mode == "same":
        return _setup_same_machine(config, gpu_info)
    elif mode == "remote":
        return _setup_remote(config)
    else:
        return _setup_cpu(config)


def _setup_same_machine(config, gpu_info):
    """Both client and server on this machine."""
    print()
    print("  ── Same Machine Setup ──")
    print(f"  GPU: {gpu_info}")
    print()
    print("  This will:")
    print("    1. Install GPU server dependencies (torch, whisper, flask)")
    print("    2. Configure the client to use localhost:8765")
    print("    3. Create a launcher that starts both server + client")
    print()

    if not ask_yn("Proceed?", "y"):
        return _setup_cpu(config)

    # Install server deps
    print("\n  Installing server dependencies (this may take a few minutes)...")

    # Check if torch+CUDA already works
    if check_cuda_python():
        print("  [OK] PyTorch with CUDA already installed.")
    else:
        print("  Installing PyTorch with CUDA support...")
        # Detect CUDA version from nvidia-smi
        try:
            result = subprocess.run(
                "nvidia-smi", shell=True, capture_output=True, text=True, timeout=10,
            )
            import re
            match = re.search(r"CUDA Version:\s*(\d+)", result.stdout)
            cuda_major = int(match.group(1)) if match else 12
        except Exception:
            cuda_major = 12

        idx = "cu121" if cuda_major >= 12 else "cu118"
        run(f'{pip_cmd()} install torch --index-url https://download.pytorch.org/whl/{idx}')

    # Install flask, whisper, numpy
    run(f'{pip_cmd()} install flask openai-whisper numpy')

    # Verify CUDA
    print("\n  Verifying CUDA...")
    if check_cuda_python():
        print("  [OK] CUDA is working!")
    else:
        print("  [WARNING] CUDA verification failed. Server may run on CPU.")

    # Choose model
    model = ask("Whisper model for GPU server (tiny/base/small/medium/large)", "medium.en")
    port = ask("Server port", "8765")

    # Configure
    config["whisper"]["remote_url"] = f"http://localhost:{port}"
    config["whisper"]["model_name"] = "tiny"   # light fallback if server restarts
    config["whisper"]["device"] = "cpu"        # client fallback is CPU
    save_config(config)

    # Create combined launcher
    _create_combined_launcher(model, port)

    print(f"\n  [OK] Config saved: localhost:{port}, model = {model}")
    print()
    print("  To start Wisper (server + client together):")
    print("    wisper.bat")
    print()
    print("  Or start them separately:")
    print(f"    Server: python server/whisper_server.py --model {model} --port {port}")
    print("    Client: python src/main.py")

    return config


def _create_combined_launcher(model, port):
    """Create wisper.bat that starts server in background then launches client."""
    bat_path = os.path.join(ROOT, "wisper.bat")
    venv_python = os.path.join("venv", "Scripts", "python.exe")
    content = f"""@echo off
title Wisper — Speech-to-Text

if not exist venv (
    echo ERROR: Run setup.py first
    pause
    exit /b 1
)

echo Starting Wisper GPU server...
start /B "" "{venv_python}" server/whisper_server.py --model {model} --port {port} > server.log 2>&1

echo Waiting for server to load model...
:wait_loop
timeout /t 2 /nobreak >nul
"{venv_python}" -c "import requests; r=requests.get('http://localhost:{port}/health',timeout=2); exit(0 if r.ok else 1)" 2>nul
if errorlevel 1 goto wait_loop
echo Server ready!

echo Starting Wisper client...
"{venv_python}" src/main.py

echo Shutting down server...
taskkill /F /FI "WINDOWTITLE eq Wisper*" >nul 2>&1
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr "PID"') do (
    "{venv_python}" -c "import requests; requests.get('http://localhost:{port}/health',timeout=1)" 2>nul
)
taskkill /F /FI "MODULES eq whisper_server*" >nul 2>&1
"""
    with open(bat_path, "w") as f:
        f.write(content)
    print(f"  Created wisper.bat (combined launcher)")


def _setup_remote(config):
    """Client connects to a GPU server on another machine."""
    print()
    print("  ── Remote GPU Server ──")
    print()
    print("  You need a machine on your network running the Wisper GPU server.")
    print()

    ip = ask("GPU server IP address", "192.168.0.5")
    port = ask("GPU server port", "8765")
    url = f"http://{ip}:{port}"

    # Test
    print(f"\n  Testing connection to {url}...")
    health = check_server_health(url)
    if health:
        loaded = health.get("model_loaded", False)
        status = "running, model loaded" if loaded else "running, model loading"
        print(f"  [OK] Server is {status}!")
    else:
        print(f"  [WARNING] Could not reach {url}")
        print("  The app will fall back to local CPU until the server is available.")

    config["whisper"]["remote_url"] = url
    config["whisper"]["model_name"] = "tiny"
    config["whisper"]["device"] = "cpu"
    save_config(config)

    print(f"\n  [OK] Config saved: remote_url = {url}")

    # Print server setup instructions for the other machine
    print()
    print("  ┌─────────────────────────────────────────────┐")
    print("  │  GPU Server Setup (run on the GPU machine)  │")
    print("  └─────────────────────────────────────────────┘")
    print(f"""
  Copy the server/ folder to your GPU machine, then:

    # Install dependencies
    pip install flask openai-whisper numpy
    pip install torch --index-url https://download.pytorch.org/whl/cu121

    # Install ffmpeg (required by Whisper)
    sudo apt install ffmpeg

    # Start the server
    python whisper_server.py --model medium.en --port {port}

    # Or use the one-click setup script:
    bash setup.sh --model medium.en --port {port}

    # Verify
    curl http://localhost:{port}/health

  Make sure port {port} is open in the firewall:
    sudo ufw allow {port}
    """)

    return config


def _setup_cpu(config):
    """CPU-only, no GPU."""
    print()
    print("  ── CPU Only ──")
    print("  Using 'tiny' model for best CPU performance.")
    print("  Transcription will be slower (~5-15s per clip).")

    config["whisper"]["remote_url"] = ""
    config["whisper"]["model_name"] = "tiny"
    config["whisper"]["device"] = "cpu"
    save_config(config)

    print("  [OK] Config saved: CPU only, model = tiny")
    return config


# ── Step 3: Ollama ───────────────────────────────────────

def step_ollama():
    print()
    print("── Step 3: LLM Text Cleanup (Optional) ────────")
    print()
    print("  Ollama can clean up transcription (fix punctuation,")
    print("  remove filler words like um/uh).")
    print("  Requires Ollama: https://ollama.ai")
    print()

    config = load_config()

    if not ask_yn("Enable Ollama text cleanup?", "n"):
        config["ollama"]["enabled"] = False
        save_config(config)
        print("  Skipped. Raw transcription will be used.")
        return

    ollama_url = ask("Ollama URL", "http://localhost:11434")
    model = ask("Ollama model", "llama2")

    # Test
    print(f"\n  Testing Ollama at {ollama_url}...")
    try:
        import requests
        resp = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if resp.ok:
            models = [m["name"] for m in resp.json().get("models", [])]
            if models:
                print(f"  [OK] Ollama running. Available: {', '.join(models)}")
            else:
                print(f"  [OK] Ollama running but no models. Run: ollama pull {model}")
        else:
            print("  [WARNING] Ollama returned an error.")
    except Exception:
        print("  [WARNING] Ollama not reachable.")
        print(f"  Install from https://ollama.ai, then: ollama pull {model}")
        print("  You can enable it later in config.yaml")

    config["ollama"]["enabled"] = True
    config["ollama"]["base_url"] = ollama_url
    config["ollama"]["model"] = model
    save_config(config)
    print(f"  [OK] Ollama enabled: {model} @ {ollama_url}")


# ── Step 4: Preferences ─────────────────────────────────

def step_preferences():
    print()
    print("── Step 4: Hotkey & Preferences ────────────────")

    config = load_config()

    hotkey = ask("Global hotkey", config["hotkey"]["key"])
    mode = ask_choice("Hotkey mode:", [
        ("Hold to talk (release to stop)", "hold"),
        ("Toggle (press once to start, again to stop)", "toggle"),
    ])

    config["hotkey"]["key"] = hotkey
    config["hotkey"]["mode"] = mode
    save_config(config)
    print(f"\n  [OK] Hotkey: {hotkey} ({mode})")


# ── Summary ──────────────────────────────────────────────

def print_summary():
    config = load_config()
    w = config["whisper"]
    o = config["ollama"]
    h = config["hotkey"]

    print()
    print("=" * 56)
    print("               Setup Complete!")
    print("=" * 56)
    print()

    # Transcription mode
    if w.get("remote_url"):
        url = w["remote_url"]
        if "localhost" in url or "127.0.0.1" in url:
            print(f"  Mode:          Same machine (GPU server @ {url})")
        else:
            print(f"  Mode:          Remote GPU server @ {url}")
        print(f"  Fallback:      Local CPU ({w['model_name']})")
    elif w["device"] == "cuda":
        print(f"  Mode:          Local GPU (model: {w['model_name']})")
    else:
        print(f"  Mode:          Local CPU (model: {w['model_name']})")

    print(f"  LLM Cleanup:   {'ON (' + o['model'] + ')' if o['enabled'] else 'OFF'}")
    print(f"  Hotkey:        {h['key']} ({h['mode']})")

    print()
    print("  ┌─────────────────────────────────────────┐")

    if w.get("remote_url") and ("localhost" in w["remote_url"] or "127.0.0.1" in w["remote_url"]):
        print("  │  Start:  wisper.bat                    │")
        print("  │  (launches server + client together)   │")
    else:
        print("  │  Start:  run.bat                       │")
        print("  │  Or:     python src/main.py            │")

    print("  │  Build:  pyinstaller build.spec         │")
    print("  └─────────────────────────────────────────┘")
    print()


# ── Main ─────────────────────────────────────────────────

def main():
    banner()

    try:
        step_environment()
        step_transcription()
        step_ollama()
        step_preferences()
        print_summary()
    except KeyboardInterrupt:
        print("\n\n  Setup cancelled.")
        sys.exit(0)


if __name__ == "__main__":
    main()
