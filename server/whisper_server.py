"""
Whisper GPU Transcription Server

Deploy this on your GPU machine (16GB VRAM).
It accepts audio via HTTP and returns transcribed text.

Setup on GPU machine:
    pip install flask openai-whisper torch numpy
    python whisper_server.py --model medium.en --port 8765

The server loads the Whisper model into GPU memory once,
then handles requests instantly.
"""

import argparse
import io
import logging
import tempfile
import time

import numpy as np
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
model = None


def load_model(model_name: str, device: str = "cuda"):
    """Load Whisper model into GPU memory."""
    global model
    import whisper
    logger.info(f"Loading Whisper model '{model_name}' on {device}...")
    model = whisper.load_model(model_name, device=device)
    logger.info("Model loaded and ready.")


@app.route("/transcribe", methods=["POST"])
def transcribe():
    """
    Accept audio and return transcribed text.

    Expects either:
    - A .wav file upload (multipart form, field name "audio")
    - Raw float32 PCM bytes in the body (set Content-Type: application/octet-stream)
      with query param ?sample_rate=16000
    """
    start = time.time()

    try:
        if "audio" in request.files:
            # Handle file upload (.wav)
            audio_file = request.files["audio"]
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                audio_file.save(tmp.name)
                result = model.transcribe(tmp.name, language="en", verbose=False)
        else:
            # Handle raw float32 PCM bytes
            raw_bytes = request.get_data()
            audio_data = np.frombuffer(raw_bytes, dtype=np.float32)

            # Normalize if needed
            max_val = np.max(np.abs(audio_data))
            if max_val > 1.0:
                audio_data = audio_data / max_val

            result = model.transcribe(audio_data, language="en", verbose=False)

        text = result.get("text", "").strip()
        elapsed = time.time() - start
        logger.info(f"Transcribed in {elapsed:.2f}s: {text[:80]}...")

        return jsonify({"text": text, "time": round(elapsed, 3)})

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "model_loaded": model is not None})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Whisper GPU Transcription Server")
    parser.add_argument("--model", default="medium.en", help="Whisper model name (tiny, base, small, medium, large)")
    parser.add_argument("--device", default="cuda", help="Device: cuda or cpu")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=8765, help="Port")
    args = parser.parse_args()

    load_model(args.model, args.device)
    app.run(host=args.host, port=args.port, threaded=True)
