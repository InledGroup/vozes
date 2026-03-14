import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    "whisper_bin_path": "",
    "model_path": "",
    "wake_word_sensitivity": 0.5,
    "hotkey": "KEY_F12",
    "models_dir": str(Path.home() / ".local" / "share" / "vozes" / "models"),
}

class ConfigManager:
    def __init__(self):
        config_dir = Path.home() / ".config" / "vozes"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = config_dir / "config.json"
        self.config = self._load_config()
        
        # Auto-detect local binary if not set
        if not self.config.get("whisper_bin_path"):
            project_root = Path(__file__).parent.parent
            search_paths = [
                project_root / "bin" / "whisper.cpp" / "build" / "bin" / "main",
                project_root / "bin" / "whisper.cpp" / "build" / "bin" / "whisper-cli",
                project_root / "bin" / "whisper.cpp" / "main",
                project_root / "bin" / "whisper.cpp" / "whisper-cli",
                Path.cwd() / "bin" / "whisper.cpp" / "build" / "bin" / "main",
                Path.cwd() / "bin" / "whisper.cpp" / "build" / "bin" / "whisper-cli",
                Path.cwd() / "bin" / "whisper.cpp" / "main",
                Path.cwd() / "bin" / "whisper.cpp" / "whisper-cli",
                Path("/usr/bin/whisper-cli"),
                Path("/usr/bin/whisper-main"),
                Path("/usr/local/bin/whisper-cli")
            ]
            for p in search_paths:
                if p.exists():
                    self.config["whisper_bin_path"] = str(p)
                    self._save_config(self.config)
                    break

        # Auto-detect default model if not set
        if not self.config.get("model_path"):
            models_dir = Path(self.config["models_dir"])
            for model_file in models_dir.glob("ggml-*.bin"):
                self.config["model_path"] = str(model_file)
                self._save_config(self.config)
                break

        # Ensure models dir exists
        models_dir = Path(self.config["models_dir"])
        models_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge defaults for missing keys
                    merged = DEFAULT_CONFIG.copy()
                    merged.update(data)
                    return merged
            except Exception as e:
                print(f"Error loading config: {e}")
                return DEFAULT_CONFIG.copy()
        else:
            self._save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

    def _save_config(self, config_data):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self._save_config(self.config)

# Singleton
config = ConfigManager()
