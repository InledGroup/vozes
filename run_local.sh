#!/bin/bash
set -e

# Setup Python VENV
echo "Setting up Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv --system-site-packages
fi

source .venv/bin/activate

echo "Installing requirements..."
pip install -r requirements.txt

# Install openwakeword without deps to avoid tflite-runtime issue on Python 3.13 / aarch64
# openwakeword can use onnxruntime (which is in requirements.txt)
echo "Installing openwakeword (special handling for Python 3.13/aarch64)..."
pip install openwakeword==0.6.0 --no-deps

# Download and compile whisper.cpp
if [ ! -d "bin/whisper.cpp" ]; then
    echo "Downloading and compiling whisper.cpp..."
    mkdir -p bin
    cd bin
    git clone https://github.com/ggerganov/whisper.cpp.git
    cd whisper.cpp
    # Build with cmake (as Makefile expects it)
    cmake -B build
    cmake --build build --config Release -j$(nproc)
    
    # Check if whisper-cli exists, if not, try to find where it is
    if [ ! -f "build/bin/whisper-cli" ]; then
        echo "Searching for built binary..."
        find build -name "whisper-cli" -type f -executable
    fi
    
    # Download a small model for testing
    bash ./models/download-ggml-model.sh base.en
    cd ../../
else
    echo "whisper.cpp already exists in bin/whisper.cpp"
    # Ensure it's built if not
    if [ ! -f "bin/whisper.cpp/build/bin/whisper-cli" ] && [ ! -f "bin/whisper.cpp/whisper-cli" ]; then
        cd bin/whisper.cpp
        cmake -B build
        cmake --build build --config Release
        cd ../../
    fi
fi

# Find the binary
WHISPER_BIN=""
# Search for 'whisper-cli' (new) or 'main' (old)
for b in "build/bin/whisper-cli" "build/bin/main" "whisper-cli" "main"; do
    if [ -f "bin/whisper.cpp/$b" ]; then
        WHISPER_BIN="$(pwd)/bin/whisper.cpp/$b"
        break
    fi
done

if [ -z "$WHISPER_BIN" ]; then
    echo "WARNING: Could not find whisper.cpp binary (main or whisper-cli) after build. Check compilation logs."
fi

MODEL_PATH="$(pwd)/bin/whisper.cpp/models/ggml-base.en.bin"

echo "Please ensure you have configured Vozes to use:"
echo "Whisper Bin: $WHISPER_BIN"
echo "Model Path: $MODEL_PATH"
echo "Starting Vozes..."

export PYTHONPATH=src
python src/main.py
