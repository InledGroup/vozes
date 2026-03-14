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
    
    # Check if main exists, if not, try to find where it is
    if [ ! -f "build/bin/main" ]; then
        echo "Searching for built binary..."
        find build -name "main" -type f -executable
    fi
    
    # Download a small model for testing
    bash ./models/download-ggml-model.sh base.en
    cd ../../
else
    echo "whisper.cpp already exists in bin/whisper.cpp"
    # Ensure it's built if not
    if [ ! -f "bin/whisper.cpp/build/bin/main" ] && [ ! -f "bin/whisper.cpp/main" ]; then
        cd bin/whisper.cpp
        cmake -B build
        cmake --build build --config Release
        cd ../../
    fi
fi

# Find the binary
WHISPER_BIN=""
# Search for 'main' (old) or 'whisper-cli' (new)
for b in "build/bin/main" "build/bin/whisper-cli" "main" "whisper-cli"; do
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
