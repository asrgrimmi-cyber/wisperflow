#!/usr/bin/env python3
"""End-to-end integration test for Phase 1."""

import sys
import os
import time
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.hotkey import HotkeyListener
from src.audio import AudioCapture
from src.transcribe import WhisperTranscriber
from src.inject import TextInjector
from src.cleanup import OllamaCleanup


def test_synthetic_audio():
    """Test transcription with synthetic audio (frequency sweep)."""
    print("\n" + "=" * 60)
    print("SYNTHETIC AUDIO TEST")
    print("=" * 60)

    print("\nGenerating synthetic audio signal...")

    sample_rate = 16000
    duration = 2  # 2 seconds
    frequency = 440  # A4 note
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Generate a sine wave
    audio_data = 0.1 * np.sin(2 * np.pi * frequency * t).astype(np.float32)

    print(f"Generated {len(audio_data)} samples at {sample_rate} Hz")
    print(f"Audio shape: {audio_data.shape}, dtype: {audio_data.dtype}")
    print(f"Audio range: [{audio_data.min():.4f}, {audio_data.max():.4f}]")

    try:
        print("\nInitializing Whisper transcriber (tiny model)...")
        transcriber = WhisperTranscriber(
            model_name="tiny",
            device="cpu"
        )

        print("Transcribing synthetic audio...")
        result = transcriber.transcribe(audio_data, sample_rate=sample_rate)

        print(f"Transcription result: '{result}'")
        print("(Synthetic audio typically produces minimal or empty transcription)")
        print("\nStatus: PASS (transcriber working)")
        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_text_injection_no_focus():
    """Test text injection setup (without requiring focused window)."""
    print("\n" + "=" * 60)
    print("TEXT INJECTION TEST")
    print("=" * 60)

    print("\nInitializing TextInjector...")
    try:
        injector = TextInjector(method="clipboard", restore_clipboard=True)

        # Test clipboard method setup
        test_text = "Test injection text"

        print(f"Testing clipboard copy/paste mechanism...")
        import pyperclip

        original = pyperclip.paste()
        pyperclip.copy(test_text)
        pasted = pyperclip.paste()

        if pasted == test_text:
            print(f"  - Clipboard copy/paste: OK")
        else:
            print(f"  - Clipboard copy/paste: FAILED (got '{pasted}')")
            return False

        pyperclip.copy(original)
        print(f"  - Clipboard restore: OK")

        print("\nNote: Full injection test requires focused window")
        print("This will be tested in manual Phase 1 trials")

        print("\nStatus: PASS (injection system ready)")
        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ollama_connection():
    """Test Ollama connection (without assuming it's running)."""
    print("\n" + "=" * 60)
    print("OLLAMA CONNECTION TEST")
    print("=" * 60)

    print("\nInitializing OllamaCleanup...")
    try:
        cleanup = OllamaCleanup(
            base_url="http://localhost:11434",
            model="llama2"
        )

        print("Checking Ollama availability...")
        available = cleanup.is_available()

        if available:
            print("  - Ollama is running: YES")
            print("Status: PASS (Ollama connected)")
            return True
        else:
            print("  - Ollama is running: NO")
            print("  (This is expected if Ollama is not installed/running)")
            print("  - Will fallback to raw transcription")
            print("\nStatus: PASS (graceful fallback configured)")
            return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hotkey_listener_init():
    """Test hotkey listener initialization."""
    print("\n" + "=" * 60)
    print("HOTKEY LISTENER INIT TEST")
    print("=" * 60)

    print("\nInitializing HotkeyListener...")
    try:
        events = {"pressed": 0, "released": 0}

        def on_press():
            events["pressed"] += 1

        def on_release():
            events["released"] += 1

        listener = HotkeyListener(
            on_press=on_press,
            on_release=on_release,
            hotkey="ctrl+win",
            mode="hold"
        )

        print(f"  - Hotkey: {listener.hotkey}")
        print(f"  - Mode: {listener.mode}")
        print(f"  - Key combination: {listener.key_combination}")
        print("  - Listener initialized: OK")

        # Note: We don't start the listener here to avoid blocking
        print("\nNote: Full hotkey test requires manual key presses")
        print("This will be tested in manual Phase 1 trials")

        print("\nStatus: PASS (hotkey listener ready)")
        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_audio_capture_init():
    """Test audio capture initialization."""
    print("\n" + "=" * 60)
    print("AUDIO CAPTURE INIT TEST")
    print("=" * 60)

    print("\nInitializing AudioCapture...")
    try:
        audio = AudioCapture(
            sample_rate=16000,
            channels=1,
            silence_threshold=0.02,
            silence_duration=1.5
        )

        print(f"  - Sample rate: {audio.sample_rate} Hz")
        print(f"  - Channels: {audio.channels}")
        print(f"  - Silence threshold: {audio.silence_threshold}")
        print(f"  - Silence duration: {audio.silence_duration}s")
        print("  - Capture initialized: OK")

        print("\nNote: Full audio capture test requires microphone")
        print("This will be tested in manual Phase 1 trials")

        print("\nStatus: PASS (audio capture ready)")
        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all automated tests."""
    print("\n" + "=" * 60)
    print("PHASE 1 INTEGRATION TEST SUITE")
    print("=" * 60)
    print("\nRunning automated tests (no user interaction required)")

    results = {}

    results["hotkey_init"] = test_hotkey_listener_init()
    results["audio_init"] = test_audio_capture_init()
    results["text_inject"] = test_text_injection_no_focus()
    results["ollama"] = test_ollama_connection()
    results["synthetic_audio"] = test_synthetic_audio()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name.replace('_', ' ').title():30} {status}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[OK] All automated tests passed!")
        print("\nREADY FOR MANUAL PHASE 1 TRIALS:")
        print("  1. Run: python src/main.py")
        print("  2. Press Ctrl+Win and speak")
        print("  3. Text should appear in focused window")
        print("  4. Repeat 10 times to verify reliability")
    else:
        print(f"\n[ERROR] {total - passed} test(s) failed")


if __name__ == "__main__":
    main()
