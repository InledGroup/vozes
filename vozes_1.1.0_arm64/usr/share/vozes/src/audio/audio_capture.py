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
        self.manual_mode = False
        self.callback_on_wake = callback_on_wake
        self.callback_on_silence = callback_on_silence
        self.frames = []
        
        # Initialize VAD
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(2) # Less aggressive than 3
        
        # Initialize OpenWakeWord (using default pre-trained models)
        import openwakeword
        from openwakeword.model import Model
        
        # In 0.6.0 models might not be downloaded by default or accessed differently
        try:
            # Try to get the model path, if it fails we might need to download it
            # Using the recommended way for 0.6.0 if available, or fallback to manual path
            import os
            base_dir = os.path.dirname(openwakeword.__file__)
            jarvis_path = os.path.join(base_dir, "resources", "models", "hey_jarvis.onnx")
            
            if not os.path.exists(jarvis_path):
                # Try .tflite as well
                jarvis_path_tflite = os.path.join(base_dir, "resources", "models", "hey_jarvis.tflite")
                if os.path.exists(jarvis_path_tflite):
                    jarvis_path = jarvis_path_tflite
                else:
                    print("Downloading openWakeWord models...")
                    from openwakeword.utils import download_models
                    download_models()
            
            self.oww_model = Model(wakeword_model_paths=[jarvis_path])
        except Exception as e:
            print(f"Error initializing OpenWakeWord: {e}")
            # Last resort: let it try to find models itself
            self.oww_model = Model(wakeword_models=["hey_jarvis"])
            
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
        # 2.0 seconds of silence to stop
        max_silence_frames = int(self.RATE / self.CHUNK * 2.0)
        # Max recording duration: 30 seconds
        max_recording_frames = int(self.RATE / self.CHUNK * 30)
        recording_count = 0
        
        while not self._stop_event.is_set():
            try:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
            except Exception as e:
                print(f"Audio read error: {e}")
                continue

            if self.is_recording:
                self.frames.append(data)
                recording_count += 1
                
                # Also listen for wake word during recording to allow "stop by voice"
                audio_data = np.frombuffer(data, dtype=np.int16)
                prediction = self.oww_model.predict(audio_data)
                stop_by_voice = False
                for mdl, score in prediction.items():
                    if score > 0.45: # Slightly higher threshold when recording to avoid false stops
                        print(f"Wake word detected during recording! Stopping... Model: {mdl}, Score: {score}")
                        stop_by_voice = True
                        break
                
                # Check for silence using VAD
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
                    
                if recording_count % 20 == 0:
                    print(f"Recording... {recording_count} frames, silence_frames: {silence_frames}/{max_silence_frames} (Manual: {self.manual_mode})")

                # Force stop if silence detected, wake word detected, or too long
                should_stop = stop_by_voice or (not self.manual_mode and silence_frames > max_silence_frames) or (recording_count > max_recording_frames)
                
                if should_stop:
                    if recording_count > max_recording_frames:
                        print("Max duration reached. Stopping.")
                    elif stop_by_voice:
                        print("Stopped by voice command.")
                    else:
                        print(f"Silence detected ({silence_frames} frames). Stopping.")
                        
                    self.is_recording = False
                    if self.callback_on_silence:
                        self.callback_on_silence("/tmp/vozes_record.wav")
            else:
                recording_count = 0
                silence_frames = 0
                # Listen for wake word
                audio_data = np.frombuffer(data, dtype=np.int16)
                prediction = self.oww_model.predict(audio_data)
                # Check if any wakeword score > threshold
                for mdl, score in prediction.items():
                    if score > 0.4: # Slightly lower threshold for Jarvis
                        print(f"Wake word detected! Model: {mdl}, Score: {score}")
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
