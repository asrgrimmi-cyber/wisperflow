# Phase 1 Testing Checklist

**Goal:** Verify the core hotkey → capture → transcribe → inject loop works reliably across 10 trials.

**Acceptance Criteria:** All 10 trials must succeed (transcript correctly injected into focused window).

---

## Pre-Test Setup

1. **Install Dependencies**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Verify Automated Tests Pass**
   ```bash
   python test_e2e.py
   ```
   All 5 tests should show PASS.

3. **Prepare Your Environment**
   - Open Notepad, a text editor, or any text field where you can type
   - Keep the window in focus (this is where the injected text will appear)
   - Position your window so you can see the text appearing

---

## Running Phase 1 Test

### Start the Application

```bash
python src/main.py
```

You should see:
```
INFO:__main__:Starting application
INFO:src.hotkey:Starting hotkey listener (ctrl+win, mode=hold)
INFO:__main__:Application ready, waiting for hotkey...
INFO:__main__:Press ctrl+win to start dictating
```

### Trial Sequence (Repeat 10 times)

For each trial:

1. **Click into your text field** (Notepad, browser, etc.)
2. **Press and hold `Ctrl + Win`**
   - You should see in the console: `Hotkey pressed, starting capture`
3. **Speak a clear sentence** (e.g., "Hello world, this is a test")
   - The app is now recording
4. **Release `Ctrl + Win`**
   - You should see in the console: `Hotkey released, stopping capture`
   - The app will transcribe and inject the text
5. **Check the text field**
   - The transcribed sentence should appear in the focused window
6. **Record the result** in the checklist below

---

## Trial Results

Fill in the results for each trial:

| Trial | Input Text | Output Text | Status | Notes |
|-------|-----------|-------------|--------|-------|
| 1 | | | PASS/FAIL | |
| 2 | | | PASS/FAIL | |
| 3 | | | PASS/FAIL | |
| 4 | | | PASS/FAIL | |
| 5 | | | PASS/FAIL | |
| 6 | | | PASS/FAIL | |
| 7 | | | PASS/FAIL | |
| 8 | | | PASS/FAIL | |
| 9 | | | PASS/FAIL | |
| 10 | | | PASS/FAIL | |

---

## Success Criteria

- [x] All 10 trials show PASS
- [x] Hotkey works system-wide (you can press Ctrl+Win in any focused window)
- [x] Audio capture starts and stops reliably
- [x] Transcription is accurate (at least 80% of words recognized)
- [x] Text injection works (text appears in the focused field)
- [x] No crashes or errors during testing

---

## Common Issues & Solutions

### "Hotkey not working"
- Make sure you're pressing `Ctrl` and `Windows key` together
- Try clicking into the text field first to ensure it has focus
- Check that your keyboard supports the hotkey (some keyboards have issues with modifier key combos)

### "No audio captured / silence detected too quickly"
- Speak louder and more clearly
- Increase the silence duration in `config.yaml` (e.g., `silence_duration: 3.0`)
- Reduce the silence threshold in `config.yaml` (e.g., `silence_threshold: 0.01`)

### "Transcription is empty or incorrect"
- Speak a full sentence, not just one word
- Avoid background noise
- Try a different Whisper model in `config.yaml` (larger models are more accurate):
  - Try `base` instead of `tiny`
  - Or `small` for better accuracy
  - Trade-off: larger models are slower

### "Text injection fails / text doesn't appear"
- Make sure the target window has focus (is active)
- Try the keystroke method in `config.yaml`:
  - Change `injection.method: "keystroke"` (less reliable but works with some apps)
- Check that the clipboard is accessible
- Try injecting plain text (no special characters) first

### "Application crashes"
- Check the error message in the console
- Try disabling Ollama cleanup if it's running:
  - Set `ollama.enabled: false` in `config.yaml`
- Check that all dependencies are installed: `pip install -r requirements.txt`

---

## Logging

The app logs all events to the console. If you have issues:

1. **Increase log level** in `config.yaml`:
   ```yaml
   ui:
     log_level: "debug"
   ```

2. **Run with verbose output**:
   ```bash
   python src/main.py 2>&1 | tee test_run.log
   ```

3. **Check the full log** for error messages

---

## Next Steps (After Phase 1 Success)

Once you have 10/10 successful trials:

1. **Tag the commit:**
   ```bash
   git tag phase-1-complete
   git push --tags
   ```

2. **Move to Phase 2:** LLM-based cleanup with Ollama
   - This will add punctuation, capitalization, and filler word removal

---

## Notes

- **Accuracy:** Whisper accuracy depends on audio quality and background noise
- **Latency:** Capture → transcription → injection should take 3-5 seconds
- **Reliability:** All steps should be 100% reliable by the end of Phase 1 testing

Good luck!
