#!/usr/bin/env python3
"""Phase 1 testing script for speech-to-text components."""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_hotkey_listener():
    """Test global hotkey listener."""
    print("\n" + "=" * 60)
    print("TEST 1: Hotkey Listener")
    print("=" * 60)

    from src.hotkey import HotkeyListener

    pressed = {"count": 0}
    released = {"count": 0}

    def on_press():
        pressed["count"] += 1
        print(f"  ✓ Hotkey PRESSED (count: {pressed['count']})")

    def on_release():
        released["count"] += 1
        print(f"  ✓ Hotkey RELEASED (count: {released['count']})")

    print("\nStarting hotkey listener (Ctrl+Win)...")
    print("Press Ctrl+Win 3 times (hold briefly each time)")
    print("Press Ctrl+C to stop\n")

    listener = HotkeyListener(on_press, on_release, hotkey="ctrl+win", mode="hold")
    listener.start()

    try:
        import time

        time.sleep(15)  # Wait 15 seconds for test input
    except KeyboardInterrupt:
        print("\nTest interrupted")
    finally:
        listener.stop()

    print(f"\nResults: {pressed['count']} presses, {released['count']} releases")
    success = pressed["count"] >= 1 and released["count"] >= 1
    print(f"Status: {'✓ PASS' if success else '✗ FAIL'}\n")
    return success


def test_audio_capture():
    """Test audio capture."""
    print("\n" + "=" * 60)
    print("TEST 2: Audio Capture & Silence Detection")
    print("=" * 60)

    from src.audio import AudioCapture
    import numpy as np

    print("\nInitializing audio capture...")
    audio = AudioCapture(
        sample_rate=16000,
        channels=1,
        silence_threshold=0.02,
        silence_duration=1.5,
    )

    print("Recording for 5 seconds...")
    print("Try to make some noise in the first 2-3 seconds, then be silent\n")

    audio_data = audio.record()

    print(f"\nCaptured {len(audio_data)} samples")
    if len(audio_data) > 0:
        rms = np.sqrt(np.mean(audio_data**2))
        print(f"Audio RMS: {rms:.4f}")

    success = len(audio_data) > 0
    print(f"Status: {'✓ PASS' if success else '✗ FAIL'}\n")
    return success


def test_text_injection():
    """Test text injection."""
    print("\n" + "=" * 60)
    print("TEST 3: Text Injection (Clipboard)")
    print("=" * 60)

    from src.inject import TextInjector
    import time

    print("\nInitializing text injector...")
    injector = TextInjector(method="clipboard", restore_clipboard=True)

    print("\nTest 1: Clipboard paste")
    print("Click in a text field (Notepad, browser, etc.) and wait...\n")

    time.sleep(3)

    test_text = "Hello from Wisper Akash! This is a test injection."
    print(f"Injecting: '{test_text}'")

    success = injector.inject(test_text)

    time.sleep(2)
    print(f"Status: {'✓ PASS' if success else '✗ FAIL'}\n")
    return success


def test_whisper_transcription():
    """Test whisper.cpp transcription."""
    print("\n" + "=" * 60)
    print("TEST 4: Whisper.cpp Transcription")
    print("=" * 60)

    print("\nInitializing whisper.cpp transcriber...")
    print("(This may take a moment to download the model on first run)\n")

    try:
        from src.transcribe import WhisperTranscriber
        import numpy as np

        # Create a silent audio sample (just to test the transcriber loads)
        sample_audio = np.zeros(16000, dtype=np.float32)

        print("Loading model...")
        transcriber = WhisperTranscriber(
            model_name="tiny",  # Use tiny model for fast testing
            device="cpu",
        )

        print("Model loaded successfully!")
        print("\nNote: Full transcription test requires actual audio input")
        print("This will be tested in the end-to-end test.\n")

        success = True
    except Exception as e:
        print(f"Error: {e}")
        success = False

    print(f"Status: {'✓ PASS' if success else '✗ FAIL'}\n")
    return success


def main():
    """Run all Phase 1 tests."""
    print("\n" + "=" * 60)
    print("PHASE 1 COMPONENT TESTS")
    print("=" * 60)

    results = {}

    # Test each component
    results["hotkey"] = test_hotkey_listener()
    results["audio"] = test_audio_capture()
    results["injection"] = test_text_injection()
    results["whisper"] = test_whisper_transcription()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name.upper():20} {status}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All Phase 1 component tests passed!\n")
    else:
        print(f"\n✗ {total - passed} test(s) failed. Review the output above.\n")


if __name__ == "__main__":
    main()
