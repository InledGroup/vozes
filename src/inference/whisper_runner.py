import subprocess
import os

class WhisperRunner:
    def __init__(self, bin_path, model_path):
        self.bin_path = bin_path
        self.model_path = model_path

    def transcribe(self, wav_path):
        """
        Runs whisper.cpp native binary and returns the transcribed text.
        """
        if not os.path.exists(self.bin_path):
            raise FileNotFoundError(f"Whisper binary not found at: {self.bin_path}")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found at: {self.model_path}")
            
        command = [
            self.bin_path,
            "-m", self.model_path,
            "-f", wav_path,
            "--output-txt",
            "-nt" # No timestamps
        ]
        
        try:
            print(f"Executing whisper command: {' '.join(command)}")
            # whisper.cpp usually outputs to stdout and also to a file if requested
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            
            # Depending on whisper.cpp version, output might be in stdout or a generated .txt file
            txt_file = f"{wav_path}.txt"
            if os.path.exists(txt_file):
                with open(txt_file, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                os.remove(txt_file)
                return text
            else:
                return self._parse_stdout(result.stdout)
                
        except subprocess.CalledProcessError as e:
            print(f"Whisper process failed with exit code {e.returncode}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            return ""
        except Exception as e:
            print(f"Unexpected error running whisper: {e}")
            return ""

    def _parse_stdout(self, stdout):
        """ Extract text from standard output. """
        lines = []
        for line in stdout.splitlines():
            # Basic parsing to remove timestamps if they are still printed e.g. [00:00:00.000 --> 00:00:05.000] text
            if line.startswith("[") and "-->" in line:
                parts = line.split("]", 1)
                if len(parts) > 1:
                    lines.append(parts[1].strip())
            elif not line.startswith("["):
                 # if there are no timestamps
                 lines.append(line.strip())
        return " ".join(lines).strip()
