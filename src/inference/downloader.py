import requests
import os
import time
from pathlib import Path

MODELS = {
    "tiny": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
    "base": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
    "small": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
    "medium": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin",
}

class ModelDownloader:
    def __init__(self, models_dir):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def download(self, model_name, progress_callback):
        """
        Downloads a model and calls progress_callback(percentage, eta_str, speed_str)
        """
        if model_name not in MODELS:
            raise ValueError(f"Unknown model: {model_name}")

        url = MODELS[model_name]
        dest_path = self.models_dir / f"ggml-{model_name}.bin"
        
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        start_time = time.time()
        downloaded = 0
        
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Calculate stats
                    percentage = (downloaded / total_size) if total_size > 0 else 0
                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0
                    remaining = total_size - downloaded
                    eta = remaining / speed if speed > 0 else 0
                    
                    eta_str = self._format_time(eta)
                    speed_str = self._format_speed(speed)
                    
                    progress_callback(percentage, eta_str, speed_str)
        
        return str(dest_path)

    def _format_time(self, seconds):
        if seconds < 60:
            return f"{int(seconds)}s"
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"

    def _format_speed(self, bytes_per_sec):
        if bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"

    def is_downloaded(self, model_name):
        dest_path = self.models_dir / f"ggml-{model_name}.bin"
        return dest_path.exists()
