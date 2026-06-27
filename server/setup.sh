#!/bin/bash
# Wisper GPU Server — One-click setup
# Usage: bash setup.sh [--model medium.en] [--port 8765]

set -e

MODEL="medium.en"
PORT=8765

while [[ $# -gt 0 ]]; do
    case $1 in
        --model) MODEL="$2"; shift 2 ;;
        --port)  PORT="$2";  shift 2 ;;
        -h|--help) echo "Usage: bash setup.sh [--model medium.en] [--port 8765]"; exit 0 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

echo ""
echo "=================================="
echo "  Wisper GPU Server Setup"
echo "  Model: $MODEL | Port: $PORT"
echo "=================================="

# Python
echo -e "\n[1/5] Checking Python..."
PY=$(command -v python3 || command -v python || echo "")
[ -z "$PY" ] && { echo "ERROR: Python not found"; exit 1; }
echo "  Found: $($PY --version)"

# GPU
echo -e "\n[2/5] Checking GPU..."
if command -v nvidia-smi &>/dev/null; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "  WARNING: nvidia-smi not found, CUDA may not work"
fi

# ffmpeg
echo -e "\n[3/5] Checking ffmpeg..."
if ! command -v ffmpeg &>/dev/null; then
    echo "  Installing ffmpeg..."
    sudo apt-get install -y -qq ffmpeg 2>/dev/null || \
    sudo yum install -y ffmpeg 2>/dev/null || \
    echo "  WARNING: Install ffmpeg manually"
fi
echo "  OK"

# Python deps
echo -e "\n[4/5] Installing Python packages..."
$PY -m pip install flask openai-whisper numpy

# PyTorch with CUDA
$PY -c "import torch; assert torch.cuda.is_available()" 2>/dev/null || {
    echo "  Installing PyTorch with CUDA..."
    CUDA_VER=$(nvidia-smi 2>/dev/null | grep -oP 'CUDA Version: \K[0-9]+' || echo "12")
    [ "$CUDA_VER" -ge 12 ] && IDX="cu121" || IDX="cu118"
    $PY -m pip install torch --index-url "https://download.pytorch.org/whl/$IDX"
}

# Verify
echo -e "\n[5/5] Verifying CUDA..."
$PY -c "
import torch
print(f'  CUDA: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'  GPU:  {torch.cuda.get_device_name(0)}')
    print(f'  VRAM: {torch.cuda.get_device_properties(0).total_mem // 1024**2} MB')
"

# Kill existing server
pkill -f whisper_server.py 2>/dev/null || true

# Start
echo ""
echo "=================================="
echo "  Starting server..."
echo "  Model: $MODEL | Port: $PORT"
echo "=================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
$PY "$SCRIPT_DIR/whisper_server.py" --model "$MODEL" --port "$PORT"
