import sys
import threading
import os
import time
import traceback
import numpy as np

# Force software rendering and disable GPU acceleration for GTK/Mesa
os.environ["GSK_RENDERER"] = "cairo"
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
os.environ["GDK_BACKEND"] = "wayland,x11"

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import GLib

from config import config
from audio.audio_capture import AudioController
from inference.whisper_runner import WhisperRunner
from input.input_manager import InputManager
from gui.app import VozesApp
from utils.i18n import _

class VozesController:
    def __init__(self):
        self.app = VozesApp(app_controller=self, application_id="org.vozes.Vozes.Dev")
        
        self.audio = AudioController(
            callback_on_wake=self.on_wake_word,
            callback_on_silence=self.on_silence_detected
        )
        self.audio.manual_mode = config.get("manual_mode", True)
        
        # Load configs
        self.whisper_bin = config.get("whisper_bin_path", "")
        self.model_path = config.get("model_path", "")
        self.hotkey = config.get("hotkey", "KEY_F12")
        
        self.input_manager = InputManager(
            hotkey_name=self.hotkey,
            on_hotkey_press=self.on_hotkey,
            on_hotkey_release=self.on_hotkey_release
        )
        
    def run(self):
        # Start input listener
        self.input_manager.start_listening()
        
        # Start audio listening
        self.audio.start_passive_listening()
        
        # Run GTK app
        self.app.run(None)
        
        # Cleanup on exit
        self.audio.cleanup()
        self.input_manager.stop_listening()

    def reinit_input(self):
        # Refresh hotkey from config
        self.input_manager.hotkey_name = config.get("hotkey", "KEY_F12")
        self.input_manager.re_initialize()

    def update_gui_status(self, text, auto_hide=False):
        # GTK UI updates must run on the main thread
        GLib.idle_add(self.app.update_status, text, auto_hide)

    def on_wake_word(self):
        print("Wake word callback")
        self.update_gui_status("Escuchando...")
        threading.Thread(target=self._realtime_transcription_loop, daemon=True).start()

    def start_dictation(self):
        self.audio.start_recording()
        self.update_gui_status("Escuchando...")
        threading.Thread(target=self._realtime_transcription_loop, daemon=True).start()

    def on_hotkey(self):
        print("Hotkey detected in VozesController!")
        if not self.audio.is_recording:
            self.start_dictation()
        else:
            # Manual stop via second tap
            self.stop_dictation()

    def on_hotkey_release(self, duration):
        print(f"Hotkey release detected in VozesController, duration: {duration:.2f}s")
        if self.audio.is_recording and duration > 0.35:
            print("Treating release as stop-recording (push-to-talk)...")
            self.stop_dictation()

    def stop_dictation(self):
        self.audio.is_recording = False
        self.on_silence_detected("/tmp/vozes_record.wav")

    def _realtime_transcription_loop(self):
        print("Starting real-time transcription loop...")
        last_transcription_time = time.time()
        
        while self.audio.is_recording:
            # 1. Animación de volumen (SiriWave amplitude)
            last_chunk = self.audio.frames[-1] if self.audio.frames else b""
            if last_chunk:
                try:
                    data = np.frombuffer(last_chunk, dtype=np.int16).astype(np.float32)
                    if len(data) > 0:
                        # Restar la media para eliminar cualquier offset DC
                        data = data - np.mean(data)
                        peak = np.max(np.abs(data))
                        # Normalizar el pico a amplitud (0.35 a 1.8) con alta sensibilidad
                        amplitude = min(1.8, max(0.35, peak / 2000.0))
                        GLib.idle_add(self.app.set_overlay_amplitude, amplitude)
                except Exception as e:
                    print(f"Error calculating amplitude: {e}")

            # 2. Transcripción parcial en tiempo real cada 0.8 segundos
            now = time.time()
            if now - last_transcription_time >= 0.8:
                last_transcription_time = now
                if len(self.audio.frames) > 10:
                    try:
                        self.audio.save_wav("/tmp/vozes_partial.wav")
                        bin_path = config.get("whisper_bin_path", "")
                        model_path = config.get("model_path", "")
                        language = config.get("language", "es")
                        
                        if bin_path and model_path:
                            runner = WhisperRunner(bin_path, model_path, language=language)
                            text = runner.transcribe("/tmp/vozes_partial.wav")
                            if text:
                                print(f"Real-time: {text}")
                                self.update_gui_status(text)
                    except Exception as err:
                        print(f"Error transcribing in real-time loop: {err}")
            
            time.sleep(0.08)

    def on_silence_detected(self, wav_path):
        print("Silence detected, processing audio...")
        self.update_gui_status(_("status_transcribing"))
        
        self.audio.save_wav(wav_path)
        
        # Reload configs in case they changed in GUI
        bin_path = config.get("whisper_bin_path", "")
        model_path = config.get("model_path", "")
        language = config.get("language", "es")
        
        if not bin_path or not model_path:
            self.update_gui_status("Error: Configure rutas en ajustes", auto_hide=True)
            return

        runner = WhisperRunner(bin_path, model_path, language=language)
        
        # Run inference in a background thread to not block UI/Audio
        def run_inference():
            text = runner.transcribe(wav_path)
            if text:
                print(f"Transcribed: {text}")
                # Hide status first so focus returns to the previous app
                self.update_gui_status(None)
                # Wait a tiny bit for the window manager to process the focus switch
                time.sleep(0.1)
                self.input_manager.type_text(text)
                self.update_gui_status("Transcribed", auto_hide=True)
            else:
                self.update_gui_status("Error de transcripción", auto_hide=True)
                
            # Restart passive listening after dictation
            # The audio controller continues its loop listening for wake word
            
        threading.Thread(target=run_inference, daemon=True).start()

if __name__ == "__main__":
    try:
        controller = VozesController()
        controller.run()
    except Exception:
        print("\nFATAL ERROR DETECTED:")
        traceback.print_exc()
        sys.exit(1)
