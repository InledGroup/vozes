# 🎙️ Vozes: Professional Voice Dictation for Linux

[![Build Debian Packages](https://github.com/InledGroup/vozes/actions/workflows/build-debs.yml/badge.svg)](https://github.com/InledGroup/vozes/actions)
![License: GNU GPLv3](https://img.shields.io/badge/License-GNU%20GPLv3-blue.svg)
![Platform: Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)
![Architecture: AMD64/ARM64](https://img.shields.io/badge/Architecture-AMD64%20%7C%20ARM64-brightgreen.svg)

**Vozes** is a high-performance, privacy-focused voice dictation system for Linux. Powered by a native C++ implementation of OpenAI's Whisper, it allows you to type with your voice anywhere—from professional IDEs to simple text editors—with zero latency and 100% offline processing.

---

## ✨ Key Features

-   **🚀 Blazing Fast:** Powered by `whisper.cpp` for native performance.
-   **🔒 100% Private:** Everything stays on your machine. No cloud, no APIs, no tracking.
-   **⌨️ Global Typing:** Works like a virtual keyboard. Dictate directly into any active window.
-   **🐕 Wake-Word Support:** Start dictating hands-free with "Hey Jarvis" (OpenWakeWord integration).
-   **🛠️ Optimized for Linux:** Native GTK4/Adwaita interface, Udev rules for hotkeys, and seamless system integration.
-   **📦 Multi-Arch:** Native support for both Intel/AMD (x64) and ARM (Raspberry Pi, Apple Silicon/Asahi).

---

## 🛠️ Installation

### 1. Download the latest release
Grab the `.deb` package for your architecture from the releases section.  
> Note that the .deb contained in every release are built in different devices such as Proxmox or Ubuntu and the experience may be different in some architectures.

### 2. Install using APT
```bash
sudo apt install ./vozes_1.5.0_amd64.deb
```
*Note: This will automatically set up a dedicated Python virtual environment and system dependencies to keep your OS clean.*

### Known errors:  

 #### PyAudio:    
 Run this
 ```bash
sudo apt-get install portaudio19-dev python3-dev
 ```


### 3. Permissions (First time only)
To allow the app to listen to global hotkeys and type on your behalf, ensure your user is in the `input` group:
```bash
sudo usermod -aG input $USER
# Log out and log back in for changes to take effect
```

## Requirements:
```bash
PyAudio==0.2.14
numpy>=2.1.0
webrtcvad==2.0.10
onnxruntime>=1.17.0
scipy>=1.13.0
scikit-learn>=1.4.0
tqdm>=4.66.0
requests==2.31.0
evdev==1.7.0
PyGObject==3.48.2
```

---

## 🚀 How to Use

1.  **Launch:** Open "Vozes" from your applications menu.
2.  **Select Model:** Choose between `tiny`, `base`, or `small` depending on your CPU power.
3.  **Dictate:**
    -   **Push-to-Talk:** Set a global hotkey in settings.
    -   **Wake-Word:** Just say *"Hey Jarvis"* and start speaking.
4.  **Automatic Typing:** Your speech will be converted to text and typed instantly at your cursor location.

---

## 🏗️ Building from Source

If you want to build the package yourself:

```bash
# Clone the repo with submodules
git clone --recursive https://github.com/InledGroup/vozes.git
cd vozes

# Build the whisper-cli binary
cd bin/whisper.cpp
mkdir build && cd build
cmake .. -DWHISPER_SDL2=OFF -DWHISPER_ALL_EXTRAS=OFF -DWHISPER_BUILD_EXAMPLES=ON
make -j$(nproc) whisper-cli
cd ../../../

# Create the .deb package
./build_deb.sh
```

---

## 🔧 Requirements

-   **OS:** Ubuntu 22.04+, Debian 12+, or any Debian-based distro.
-   **Python:** 3.10 or higher.
-   **Libraries:** `libgirepository1.0-dev`, `libportaudio2`, `libevdev2`.

---

## 🤝 Contributing

Contributions are welcome! Whether it's a bug report, a new feature, or a translation, feel free to open an Issue or a Pull Request.

---

## 📄 License

Vozes is released under the **GNU GPLv3**. See [LICENSE](LICENSE) for more details.

---

<p align="center">
  Built with ❤️ by JaimeGH.
</p>
