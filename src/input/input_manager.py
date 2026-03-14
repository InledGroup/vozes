import evdev
from evdev import UInput, ecodes
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
        self.uinput = None
        self._setup_uinput()

    def _setup_uinput(self):
        for i in range(3):
            try:
                if self.uinput:
                    try: self.uinput.close()
                    except: pass
                
                # Filtrar solo teclas reales (0-248) para evitar Errno 22
                # KEY_RESERVED=0, KEY_MIN_INTERESTING=1, KEY_MAX=0x2ff
                # Supported keys for a standard keyboard
                supported_keys = [k for k in range(1, 248)]

                cap = {
                    ecodes.EV_KEY: supported_keys,
                    ecodes.EV_REP: 1 # Required by some compositors
                }

                # Using BUS_USB and dummy IDs to look more like a real hardware device
                self.uinput = UInput(cap, name="Vozes-Virtual-Keyboard", 
                                    bustype=ecodes.BUS_USB, 
                                    vendor=0x1234, 
                                    product=0x5678, 
                                    version=1)
                print("Escritura virtual (UInput) inicializada correctamente.")
                return
            except Exception as ex:
                if i < 2:
                    print(f"Reintentando crear UInput ({i+1}/3) - Error: {ex}")
                    time.sleep(0.5)
                else:
                    print(f"Fallo final al crear UInput: {ex}")
                    self.uinput = None

    def start_listening(self):
        self._stop_event.clear()
        if not self._thread or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._listen_loop)
            self._thread.daemon = True
            self._thread.start()

    def stop_listening(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)

    def re_initialize(self):
        print("Reiniciando sistema de entrada...")
        self.stop_listening()
        time.sleep(0.5) 
        self._setup_uinput()
        self.start_listening()

    def _listen_loop(self):
        while not self._stop_event.is_set():
            active_keyboards = []
            try:
                for path in evdev.list_devices():
                    try:
                        dev = evdev.InputDevice(path)
                        if ecodes.EV_KEY in dev.capabilities() and len(dev.capabilities()[ecodes.EV_KEY]) > 20:
                            active_keyboards.append(dev)
                        else:
                            dev.close()
                    except:
                        continue 
            except:
                pass
            
            if not active_keyboards:
                time.sleep(2)
                continue
            
            hotkey_code = getattr(ecodes, self.hotkey_name, ecodes.KEY_F12)
            print(f"Escuchando {self.hotkey_name} en: {[k.name for k in active_keyboards]}")

            devices_dict = {dev.fd: dev for dev in active_keyboards}
            
            while not self._stop_event.is_set():
                try:
                    r, w, x = select.select(devices_dict.keys(), [], [], 1.0)
                    if not r: 
                        continue 

                    for fd in r:
                        device = devices_dict[fd]
                        # Read all available events
                        for event in device.read():
                            if event.type == ecodes.EV_KEY:
                                # Log any key for debugging
                                # print(f"Evento de tecla: {event.code}, valor: {event.value}")
                                if event.code == hotkey_code and event.value == 1:
                                    print(f"¡Tecla {self.hotkey_name} ({hotkey_code}) detectada!")
                                    if self.on_hotkey_press:
                                        self.on_hotkey_press()
                except Exception as loop_ex:

                    break 
            
            for dev in active_keyboards:
                try: dev.close()
                except: pass

    def type_text(self, text):
        if not self.uinput:
            print("Escritura virtual no disponible.")
            return
            
        print(f"Typing text: '{text}'")
        
        # Give a small delay to make sure the hotkey is released 
        time.sleep(0.3)
        
        # Extended character map
        char_map = {
            ' ': ecodes.KEY_SPACE, '\n': ecodes.KEY_ENTER, '.': ecodes.KEY_DOT, 
            ',': ecodes.KEY_COMMA, '-': ecodes.KEY_MINUS, '?': ecodes.KEY_SLASH,
            '!': ecodes.KEY_1, '(': ecodes.KEY_9, ')': ecodes.KEY_0,
            ':': ecodes.KEY_SEMICOLON, ';': ecodes.KEY_SEMICOLON,
            '"': ecodes.KEY_APOSTROPHE, "'": ecodes.KEY_APOSTROPHE,
            '/': ecodes.KEY_SLASH, '\\': ecodes.KEY_BACKSLASH,
            '[': ecodes.KEY_LEFTBRACE, ']': ecodes.KEY_RIGHTBRACE,
            '{': ecodes.KEY_LEFTBRACE, '}': ecodes.KEY_RIGHTBRACE,
            '@': ecodes.KEY_2, '#': ecodes.KEY_3, '$': ecodes.KEY_4,
            '%': ecodes.KEY_5, '^': ecodes.KEY_6, '&': ecodes.KEY_7,
            '*': ecodes.KEY_8, '+': ecodes.KEY_EQUAL, '=': ecodes.KEY_EQUAL,
            '_': ecodes.KEY_MINUS, '<': ecodes.KEY_COMMA, '>': ecodes.KEY_DOT,
        }
        
        # Basic Spanish accent normalization to base characters
        # Handling dead keys via uinput is extremely layout-dependent,
        # so we normalize to ensure the text is at least typed.
        import unicodedata
        def normalize_char(c):
            if ord(c) < 128: return c
            return "".join(x for x in unicodedata.normalize('NFKD', c) if unicodedata.category(x) != 'Mn')

        for char in text:
            # Try original char first
            target = char
            code = None
            shift = False
            
            if target.islower(): code = getattr(ecodes, f"KEY_{target.upper()}", None)
            elif target.isupper(): code = getattr(ecodes, f"KEY_{target}", None); shift = True
            elif target in char_map: 
                code = char_map[target]
                # Common shifted symbols in US layout (which uinput defaults to)
                if target in '?!()@#$%^&*_+{}|:\"<>': shift = True
            elif target.isdigit(): code = getattr(ecodes, f"KEY_{target}", None)
            
            # If not found, try normalized version
            if not code:
                normalized = normalize_char(target)
                if normalized != target:
                    target = normalized
                    if target.islower(): code = getattr(ecodes, f"KEY_{target.upper()}", None)
                    elif target.isupper(): code = getattr(ecodes, f"KEY_{target}", None); shift = True
                    elif target in char_map: code = char_map[target]
                    elif target.isdigit(): code = getattr(ecodes, f"KEY_{target}", None)

            if code:
                try:
                    if shift: self.uinput.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 1)
                    self.uinput.write(ecodes.EV_KEY, code, 1)
                    self.uinput.syn()
                    time.sleep(0.01)
                    self.uinput.write(ecodes.EV_KEY, code, 0)
                    if shift: self.uinput.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 0)
                    self.uinput.syn()
                    time.sleep(0.01)
                except Exception as e:
                    print(f"Error typing char '{char}': {e}")
            else:
                print(f"Char '{char}' (normalized: '{normalize_char(char)}') not found in key map")
        
        # Espacio final para separar dictados
        try:
            self.uinput.write(ecodes.EV_KEY, ecodes.KEY_SPACE, 1)
            self.uinput.write(ecodes.EV_KEY, ecodes.KEY_SPACE, 0)
            self.uinput.syn()
        except:
            pass
