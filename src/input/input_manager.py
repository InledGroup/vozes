import evdev
from evdev import UInput, ecodes as e
import threading
import time
import os
import select

class InputManager:
    def __init__(self, hotkey_name="KEY_F12", on_hotkey_press=None):
        self.hotkey_name = hotkey_name
        self.on_hotkey_press = on_hotkey_press
        self._stop_event = threading.Event()
        self._thread = None
        self._devices = []
        
        # Initialize UInput for text injection
        # We need to specify the capabilities we want to use (keyboard keys)
        cap = {
            e.EV_KEY: [getattr(e, key) for key in dir(e) if key.startswith('KEY_')]
        }
        try:
            self.uinput = UInput(cap, name="Vozes-Virtual-Keyboard")
        except Exception as ex:
            print(f"Failed to create UInput device. Check permissions for /dev/uinput: {ex}")
            self.uinput = None

    def start_listening(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listen_loop)
        self._thread.daemon = True
        self._thread.start()

    def stop_listening(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def re_initialize(self):
        """ Re-attempts to open uinput and find keyboard devices. """
        self.stop_listening()
        
        # Re-init UInput
        cap = {
            e.EV_KEY: [getattr(e, key) for key in dir(e) if key.startswith('KEY_')]
        }
        try:
            if self.uinput:
                self.uinput.close()
            self.uinput = UInput(cap, name="Vozes-Virtual-Keyboard")
            print("Successfully re-initialized UInput")
        except Exception as ex:
            print(f"Failed to re-initialize UInput: {ex}")

        self.start_listening()

    def _listen_loop(self):
        while not self._stop_event.is_set():
            # Find all keyboard devices
            try:
                devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
                # Filter for keyboards: must have keys, and we ignore common noise devices
                keyboards = [dev for dev in devices if e.EV_KEY in dev.capabilities()]
                # Basic filter to ignore things that aren't real keyboards if possible
                real_keyboards = [k for k in keyboards if "Power Button" not in k.name and "Sleep Button" not in k.name]
                
                # If we only found noise devices, keep searching for real keyboards
                if not real_keyboards and keyboards:
                    # If we have any keyboard, we use it, but we prefer real ones
                    active_keyboards = keyboards
                else:
                    active_keyboards = real_keyboards
            except Exception as ex:
                print(f"Error scanning devices: {ex}")
                active_keyboards = []
            
            if not active_keyboards:
                print("No suitable keyboard devices found. Retrying in 5 seconds...")
                time.sleep(5)
                continue
            
            # Determine the ecodes value for our hotkey
            hotkey_code = getattr(e, self.hotkey_name, None)
            if not hotkey_code:
                print(f"Invalid hotkey: {self.hotkey_name}")
                return

            print(f"Listening for hotkey {self.hotkey_name} on {len(active_keyboards)} keyboards: {[k.name for k in active_keyboards]}")

            devices_dict = {dev.fd: dev for dev in active_keyboards}
            
            # Loop for reading events from found keyboards
            while not self._stop_event.is_set():
                try:
                    r, w, x = select.select(devices_dict.keys(), [], [], 1.0)
                except Exception:
                    # Select error (likely device disconnected)
                    break

                if not r: # timeout
                    # Periodically check if we have more keyboards now (e.g. permissions fixed)
                    # We only break if we don't have a "real" keyboard yet
                    if len(active_keyboards) < 2: # Very simple heuristic
                         break
                    continue

                device_disconnected = False
                for fd in r:
                    device = devices_dict[fd]
                    try:
                        for event in device.read():
                            if event.type == e.EV_KEY:
                                if event.code == hotkey_code and event.value == 1: # 1 is key down
                                    print(f"Hotkey {self.hotkey_name} detected!")
                                    if self.on_hotkey_press:
                                        self.on_hotkey_press()
                    except OSError:
                        # Device disconnected
                        print(f"Device {device.name} disconnected")
                        del devices_dict[fd]
                        device_disconnected = True
                        break
                
                if device_disconnected:
                    break
            
            # If we exited the inner loop, it will re-scan in the outer loop

    def type_text(self, text):
        """ Inject text as keyboard events. """
        if not self.uinput:
            print("UInput not available. Cannot inject text.")
            return
            
        # Very basic ascii to keycode mapping for typing.
        # Note: A real implementation requires mapping chars to specific keycodes 
        # considering the keyboard layout and handling shifts.
        # For simplicity, we implement a basic version that types space and basic characters.
        
        char_to_keycode = {
            ' ': e.KEY_SPACE, '\n': e.KEY_ENTER,
            '.': e.KEY_DOT, ',': e.KEY_COMMA,
            '?': e.KEY_SLASH, '!': e.KEY_1, # Shift+1 usually
            '-': e.KEY_MINUS,
        }
        
        for char in text:
            # Handle basic keys and lower case a-z
            code = None
            shift = False
            
            if char.islower():
                key_name = f"KEY_{char.upper()}"
                code = getattr(e, key_name, None)
            elif char.isupper():
                key_name = f"KEY_{char}"
                code = getattr(e, key_name, None)
                shift = True
            elif char in char_to_keycode:
                code = char_to_keycode[char]
                if char == '?' or char == '!': # Simple approximation for shift chars
                    shift = True
            elif char.isdigit():
                key_name = f"KEY_{char}"
                code = getattr(e, key_name, None)

            if code:
                try:
                    if shift:
                        self.uinput.write(e.EV_KEY, e.KEY_LEFTSHIFT, 1)
                        self.uinput.syn()
                    
                    self.uinput.write(e.EV_KEY, code, 1) # Key down
                    self.uinput.syn()
                    time.sleep(0.01)
                    self.uinput.write(e.EV_KEY, code, 0) # Key up
                    self.uinput.syn()
                    
                    if shift:
                        self.uinput.write(e.EV_KEY, e.KEY_LEFTSHIFT, 0)
                        self.uinput.syn()
                    time.sleep(0.01)
                except Exception as ex:
                    print(f"Failed to write to uinput: {ex}")
        
        # Add a final space after dictation
        if text:
            self.uinput.write(e.EV_KEY, e.KEY_SPACE, 1)
            self.uinput.write(e.EV_KEY, e.KEY_SPACE, 0)
            self.uinput.syn()
