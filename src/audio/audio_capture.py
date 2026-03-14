import pyaudio
import wave
import numpy as np
import webrtcvad
import openwakeword
from openwakeword.model import Model
import threading
import time

class AudioController:
    def __init__(self, callback_on_wake=None, callback_on_silence=None):
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1280 # 80ms chunks for VAD
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self.is_listening_for_wake = False
        self.callback_on_wake = callback_on_wake
        self.callback_on_silence = callback_on_silence
        self.frames = []
        
        # Initialize VAD
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(2) # Less aggressive than 3
        
        # Initialize OpenWakeWord (using default pre-trained models)
        # In version 0.4.0, the parameter is 'wakeword_model_paths'
        import openwakeword
        jarvis_path = openwakeword.models["hey_jarvis"]["model_path"]
        self.oww_model = Model(wakeword_model_paths=[jarvis_path])
        self._thread = None
        self._stop_event = threading.Event()

    def start_passive_listening(self):
        print("Starting passive audio listening...")
        self._stop_event.clear()
        self.is_listening_for_wake = True
        try:
            self.stream = self.audio.open(format=self.FORMAT, channels=self.CHANNELS,
                                          rate=self.RATE, input=True,
                                          frames_per_buffer=self.CHUNK)
            print("Audio stream opened successfully.")
        except Exception as e:
            print(f"Failed to open audio stream: {e}")
            return

        self._thread = threading.Thread(target=self._listen_loop)
        self._thread.daemon = True
        self._thread.start()
        print("Passive listening thread started.")

    def stop_passive_listening(self):
        self._stop_event.set()
        self.is_listening_for_wake = False
        if self._thread:
            self._thread.join()
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def _listen_loop(self):
        silence_frames = 0
        max_silence_frames = int(self.RATE / self.CHUNK * 2.5) # 2.5 seconds of silence
        
        while not self._stop_event.is_set():
            try:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
            except Exception as e:
                print(f"Audio read error: {e}")
                continue

            if self.is_recording:
                self.frames.append(data)
                # Check for silence using VAD
                # webrtcvad expects 10, 20, or 30 ms chunks
                # We have 80ms chunk, split it for VAD
                is_speech = False
                frame_length = int(self.RATE * 0.02) # 20ms
                for i in range(0, len(data), frame_length * 2):
                    chunk20ms = data[i:i+frame_length*2]
                    if len(chunk20ms) == frame_length * 2:
                        if self.vad.is_speech(chunk20ms, self.RATE):
                            is_speech = True
                            break
                
                if not is_speech:
                    silence_frames += 1
                else:
                    silence_frames = 0
                    
                if silence_frames > max_silence_frames:
                    # Silence detected, stop recording and trigger callback
                    self.is_recording = False
                    if self.callback_on_silence:
                        self.callback_on_silence("/tmp/vozes_record.wav")
            else:
                # Listen for wake word
                audio_data = np.frombuffer(data, dtype=np.int16)
                prediction = self.oww_model.predict(audio_data)
                # Check if any wakeword score > threshold (e.g., 0.5)
                for mdl in self.oww_model.models.keys():
                    if prediction[mdl] > 0.5:
                        print("Wake word detected!")
                        self.start_recording()
                        if self.callback_on_wake:
                            self.callback_on_wake()
                        break

    def start_recording(self):
        print("Recording started...")
        self.is_recording = True
        self.frames = []

    def save_wav(self, filename):
        duration = (len(self.frames) * self.CHUNK) / self.RATE
        print(f"Saving WAV to {filename} ({len(self.frames)} frames, {duration:.2f}s)")
        if len(self.frames) == 0:
            print("WARNING: No audio frames to save!")
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        print("WAV file saved.")
        
    def cleanup(self):
        self.stop_passive_listening()
        self.audio.terminate()
