import subprocess
import os

class WhisperRunner:
    def __init__(self, bin_path, model_path, language="auto"):
        self.bin_path = bin_path
        self.model_path = model_path
        self.language = language

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
            "-nt", # No timestamps
            "-l", self.language
        ]
        
        try:
            print(f"Executing whisper command: {' '.join(command)}")
            # whisper.cpp outputs transcription to stdout
            result = subprocess.run(command, capture_output=True, text=True, check=True)
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
            line = line.strip()
            if not line: continue
            
            # Ignore common whisper.cpp system/debug output
            if any(x in line for x in ["whisper_init", "whisper_full", "system_info", "WARNING", "error"]):
                continue
            
            # Ignore hallucinations or ambient sounds in brackets like [MÚSICA], [LAUGHTER], etc.
            if line.startswith("[") and line.endswith("]") and "-->" not in line:
                continue
            
            # Remove timestamps if present [00:00:00.000 --> 00:00:05.000]
            if line.startswith("[") and "-->" in line:
                parts = line.split("]", 1)
                if len(parts) > 1:
                    line = parts[1].strip()
            
            if line:
                lines.append(line)
        
        return " ".join(lines).strip()
