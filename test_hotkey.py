"""Test script to debug hotkey detection."""

import logging
from pynput import keyboard

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def on_press(key):
    """Log when a key is pressed."""
    try:
        if hasattr(key, 'char'):
            logger.info(f"Key pressed: {key.char}")
        else:
            logger.info(f"Key pressed: {key}")
    except:
        logger.info(f"Key pressed: {key}")

def on_release(key):
    """Log when a key is released."""
    try:
        if hasattr(key, 'char'):
            logger.info(f"Key released: {key.char}")
        else:
            logger.info(f"Key released: {key}")
    except:
        logger.info(f"Key released: {key}")

    if key == keyboard.Key.esc:
        return False

print("Press keys (Ctrl+Win especially). Press ESC to exit.")
print(f"Available keys: ctrl={keyboard.Key.ctrl}, cmd={keyboard.Key.cmd}")

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
