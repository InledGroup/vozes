import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio
from config import config
from inference.downloader import ModelDownloader, MODELS
from utils.system_utils import apply_udev_rules
import threading
import os

class ModelRow(Adw.ActionRow):
    def __init__(self, model_name, downloader, on_download_complete):
        super().__init__(title=model_name.capitalize())
        self.model_name = model_name
        self.downloader = downloader
        self.on_download_complete = on_download_complete
        
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_valign(Gtk.Align.CENTER)
        self.progress_bar.set_visible(False)
        
        self.status_label = Gtk.Label(label="")
        self.status_label.set_visible(False)
        
        self.download_button = Gtk.Button(icon_name="folder-download-symbolic")
        self.download_button.set_valign(Gtk.Align.CENTER)
        self.download_button.connect("clicked", self.on_download_clicked)
        
        self.check_status()
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.append(self.status_label)
        box.append(self.progress_bar)
        box.append(self.download_button)
        self.add_suffix(box)

    def check_status(self):
        if self.downloader.is_downloaded(self.model_name):
            self.download_button.set_sensitive(True)
            self.download_button.set_icon_name("emblem-ok-symbolic")
            self.set_subtitle("Descargado - Haga clic para usar")
        else:
            self.download_button.set_sensitive(True)
            self.download_button.set_icon_name("folder-download-symbolic")
            self.set_subtitle("No descargado")

    def on_download_clicked(self, button):
        if self.downloader.is_downloaded(self.model_name):
            # Already downloaded, just select it
            dest_path = self.downloader.models_dir / f"ggml-{self.model_name}.bin"
            self.on_download_complete(self.model_name, str(dest_path))
            return

        self.download_button.set_sensitive(False)
        self.progress_bar.set_visible(True)
        self.status_label.set_visible(True)
        
        threading.Thread(target=self.do_download, daemon=True).start()

    def do_download(self):
        try:
            path = self.downloader.download(self.model_name, self.update_progress)
            GLib.idle_add(self.finish_download, path)
        except Exception as e:
            GLib.idle_add(self.handle_error, str(e))

    def update_progress(self, percentage, eta_str, speed_str):
        GLib.idle_add(self._update_ui, percentage, eta_str, speed_str)

    def _update_ui(self, percentage, eta_str, speed_str):
        self.progress_bar.set_fraction(percentage)
        self.status_label.set_text(f"{int(percentage*100)}% - {eta_str} ({speed_str})")

    def finish_download(self, path):
        self.progress_bar.set_visible(False)
        self.status_label.set_text("¡Completado!")
        self.check_status()
        self.on_download_complete(self.model_name, path)

    def handle_error(self, error_msg):
        self.download_button.set_sensitive(True)
        self.progress_bar.set_visible(False)
        self.status_label.set_text(f"Error: {error_msg}")


class VozesWindow(Adw.ApplicationWindow):
    def __init__(self, app_controller=None, **kwargs):
        super().__init__(**kwargs)
        self.app_controller = app_controller
        self.set_title("Vozes")
        self.set_default_size(800, 600)
        
        self.downloader = ModelDownloader(config.get("models_dir"))
        
        # Navigation Split View (Sidebar + Content)
        self.split_view = Adw.NavigationSplitView()
        self.set_content(self.split_view)
        
        # Sidebar
        sidebar_page = Adw.NavigationPage(title="Menú")
        self.split_view.set_sidebar(sidebar_page)
        
        sidebar_toolbar = Adw.ToolbarView()
        sidebar_page.set_child(sidebar_toolbar)
        
        sidebar_header = Adw.HeaderBar()
        sidebar_toolbar.add_top_bar(sidebar_header)
        
        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.add_css_class("navigation-sidebar")
        self.sidebar_list.connect("row-selected", self.on_sidebar_row_selected)
        sidebar_toolbar.set_content(self.sidebar_list)
        
        self.add_sidebar_row("Inicio", "go-home-symbolic")
        self.add_sidebar_row("General", "preferences-system-symbolic")
        self.add_sidebar_row("Modelos", "folder-download-symbolic")
        self.add_sidebar_row("Sistema", "system-run-symbolic")
        
        # Content Pages
        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        content_page = Adw.NavigationPage(title="Vozes")
        content_page.set_child(self.content_stack)
        self.split_view.set_content(content_page)
        
        self.init_home_page()
        self.init_onboarding_page() # New onboarding page
        self.init_general_page()
        self.init_models_page()
        self.init_system_page()
        
        # Check if setup is needed
        setup_needed = False
        if not config.get("model_path"):
            setup_needed = True
        
        # Check uinput permissions
        if not os.access("/dev/uinput", os.W_OK):
            setup_needed = True

        if setup_needed:
            self.sidebar_list.select_row(self.sidebar_list.get_row_at_index(2)) # Onboarding
            self.content_stack.set_visible_child_name("Asistente")
            
            # If permissions are OK but model is missing, skip to step 2
            if os.access("/dev/uinput", os.W_OK):
                self.onboarding_stack.set_visible_child_name("step2")
        else:
            self.sidebar_list.select_row(self.sidebar_list.get_row_at_index(0))
            self.content_stack.set_visible_child_name("Inicio")

    def add_sidebar_row(self, title, icon_name):
        row = Adw.ActionRow(title=title)
        row.add_prefix(Gtk.Image(icon_name=icon_name))
        row.set_activatable(True)
        self.sidebar_list.append(row)

    def on_sidebar_row_selected(self, listbox, row):
        if row:
            title = row.get_title()
            # Map "Asistente" row to stack child
            if title == "Configuración Guiada":
                self.content_stack.set_visible_child_name("Asistente")
            else:
                self.content_stack.set_visible_child_name(title)

    def init_onboarding_page(self):
        self.onboarding_stack = Gtk.Stack()
        self.onboarding_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        # Slide 1: Permissions
        step1 = Adw.StatusPage(title="Paso 1: Permisos de Hardware",
                              description="Vozes necesita acceder a su teclado y crear un dispositivo de escritura virtual.")
        step1.set_icon_name("system-run-symbolic")
        
        btn_fix = Gtk.Button(label="Configurar con pkexec")
        btn_fix.add_css_class("suggested-action")
        btn_fix.set_halign(Gtk.Align.CENTER)
        btn_fix.connect("clicked", self.on_onboarding_fix_permissions)
        
        step1_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        step1_box.append(btn_fix)
        step1.set_child(step1_box)
        self.onboarding_stack.add_titled(step1, "step1", "Permisos")
        
        # Slide 2: Model
        step2 = Adw.StatusPage(title="Paso 2: Descargar Modelo",
                              description="Seleccione el modelo de inteligencia artificial para el reconocimiento de voz.")
        step2.set_icon_name("folder-download-symbolic")
        
        model_list = Gtk.ListBox()
        model_list.add_css_class("boxed-list")
        model_list.set_margin_start(50)
        model_list.set_margin_end(50)
        
        for m_name in MODELS.keys():
            row = ModelRow(m_name, self.downloader, self.on_onboarding_model_downloaded)
            model_list.append(row)
            
        step2.set_child(model_list)
        self.onboarding_stack.add_titled(step2, "step2", "Modelo")
        
        # Slide 3: Ready
        step3 = Adw.StatusPage(title="¡Todo listo!",
                              description="Vozes está configurado y funcionando en segundo plano.")
        step3.set_icon_name("emblem-ok-symbolic")
        
        btn_finish = Gtk.Button(label="Empezar a usar")
        btn_finish.add_css_class("suggested-action")
        btn_finish.set_halign(Gtk.Align.CENTER)
        btn_finish.connect("clicked", lambda b: self.content_stack.set_visible_child_name("Inicio"))
        step3.set_child(btn_finish)
        self.onboarding_stack.add_titled(step3, "step3", "Finalizar")
        
        self.content_stack.add_titled(self.onboarding_stack, "Asistente", "Configuración Guiada")
        self.add_sidebar_row("Configuración Guiada", "view-list-bullet-symbolic")

    def on_onboarding_fix_permissions(self, btn):
        print("Starting permission fix with pkexec...")
        success, msg = apply_udev_rules()
        if success:
            print("Permissions script executed successfully.")
            # Verify if /dev/uinput is now writable
            if os.access("/dev/uinput", os.W_OK):
                print("Permissions verified: /dev/uinput is writable.")
                # Re-init input in controller
                if self.app_controller:
                    self.app_controller.reinit_input()
                self.onboarding_stack.set_visible_child_name("step2")
            else:
                print("CRITICAL: Permissions script reported success but /dev/uinput is STILL NOT writable.")
                self.show_error_dialog("Error: No se pudo obtener acceso a /dev/uinput incluso tras el asistente. Intente ejecutar: sudo chmod 666 /dev/uinput")
        else:
            print(f"Permission fix failed: {msg}")
            self.show_error_dialog(f"Error al configurar permisos: {msg}")

    def show_error_dialog(self, msg):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Error",
            body=msg
        )
        dialog.add_response("ok", "Aceptar")
        dialog.set_default_response("ok")
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()

    def on_onboarding_model_downloaded(self, name, path):
        self.on_model_downloaded(name, path)
        self.onboarding_stack.set_visible_child_name("step3")

    def init_home_page(self):
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title="Bienvenido a Vozes")
        page.add(group)
        
        welcome_row = Adw.ActionRow(title="Guía de inicio rápido")
        welcome_row.set_subtitle("Siga estos pasos para empezar a dictar")
        group.add(welcome_row)
        
        steps = [
            ("1. Configurar Permisos", "Vaya a la sección 'Sistema' y pulse 'Aplicar con pkexec'. Esto permite capturar su teclado.", "system-run-symbolic"),
            ("2. Descargar un Modelo", "Vaya a 'Modelos' y descargue el modelo 'Base'. Se seleccionará automáticamente al terminar.", "folder-download-symbolic"),
            ("3. ¡Empiece a Dictar!", "Diga 'Hey Jarvis' o presione la tecla F12 (configurable en General) para empezar.", "audio-input-microphone-symbolic"),
        ]
        
        for title, sub, icon in steps:
            r = Adw.ActionRow(title=title, subtitle=sub)
            r.add_prefix(Gtk.Image(icon_name=icon))
            group.add(r)
            
        self.content_stack.add_titled(page, "Inicio", "Inicio")

    def init_general_page(self):
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title="Configuración de Inferencia")
        page.add(group)
        
        self.bin_row = Adw.EntryRow(title="Ruta Binario whisper.cpp")
        self.bin_row.set_text(config.get("whisper_bin_path", ""))
        self.bin_row.connect("changed", lambda r: config.set("whisper_bin_path", r.get_text()))
        group.add(self.bin_row)
        
        self.model_row = Adw.EntryRow(title="Ruta del Modelo (.bin)")
        self.model_row.set_text(config.get("model_path", ""))
        self.model_row.connect("changed", lambda r: config.set("model_path", r.get_text()))
        group.add(self.model_row)
        
        # Language Selection
        languages = {
            "es": "Español",
            "en": "English",
            "fr": "Français",
            "de": "Deutsch",
            "it": "Italiano",
            "pt": "Português",
            "auto": "Auto-detectar"
        }
        
        self.lang_row = Adw.ComboRow(title="Idioma de dictado")
        model = Gtk.StringList()
        lang_keys = list(languages.keys())
        for lang_name in languages.values():
            model.append(lang_name)
        self.lang_row.set_model(model)
        
        current_lang = config.get("language", "es")
        if current_lang in lang_keys:
            self.lang_row.set_selected(lang_keys.index(current_lang))
            
        self.lang_row.connect("notify::selected", self.on_language_changed, lang_keys)
        group.add(self.lang_row)
        
        group2 = Adw.PreferencesGroup(title="Entrada y Atajos")
        page.add(group2)
        
        self.manual_row = Adw.SwitchRow(title="Control Manual (Pulsar para parar)")
        self.manual_row.set_subtitle("Si está activo, debe volver a pulsar la tecla para terminar de dictar")
        self.manual_row.set_active(config.get("manual_mode", True))
        self.manual_row.connect("notify::active", self.on_manual_mode_changed)
        group2.add(self.manual_row)
        
        self.hotkey_row = Adw.EntryRow(title="Hotkey (código evdev)")
        self.hotkey_row.set_text(config.get("hotkey", "KEY_F12"))
        self.hotkey_row.connect("changed", lambda r: config.set("hotkey", r.get_text()))
        group2.add(self.hotkey_row)
        
        self.content_stack.add_titled(page, "General", "General")

    def on_language_changed(self, combo, pspec, lang_keys):
        selected_idx = combo.get_selected()
        lang_code = lang_keys[selected_idx]
        config.set("language", lang_code)
        print(f"Language changed to: {lang_code}")

    def on_manual_mode_changed(self, switch, pspec):
        is_active = switch.get_active()
        config.set("manual_mode", is_active)
        if self.app_controller and self.app_controller.audio:
            self.app_controller.audio.manual_mode = is_active
        print(f"Manual mode changed to: {is_active}")

    def init_models_page(self):
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title="Descargar Modelos")
        page.add(group)
        
        for m_name in MODELS.keys():
            row = ModelRow(m_name, self.downloader, self.on_model_downloaded)
            group.add(row)
            
        self.content_stack.add_titled(page, "Modelos", "Modelos")

    def on_model_downloaded(self, name, path):
        # Automatically set the downloaded model path
        self.model_row.set_text(path)
        config.set("model_path", path)

    def init_system_page(self):
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title="Permisos y Hardware")
        page.add(group)
        
        row = Adw.ActionRow(title="Configurar permisos udev", 
                            subtitle="Permite acceso a entrada de teclado y dispositivos virtuales sin root")
        
        btn = Gtk.Button(label="Aplicar con pkexec")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", self.on_apply_udev_clicked)
        row.add_suffix(btn)
        group.add(row)
        
        self.content_stack.add_titled(page, "Sistema", "Sistema")

    def on_apply_udev_clicked(self, btn):
        success, msg = apply_udev_rules()
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Resultado de udev",
            body=msg
        )
        dialog.add_response("ok", "Aceptar")
        dialog.set_default_response("ok")
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()


class OverlayWindow(Gtk.Window):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Vozes Status")
        self.set_decorated(False)
        self.set_default_size(200, 50)
        
        self.label = Gtk.Label(label="Ready")
        self.label.set_margin_top(10)
        self.label.set_margin_bottom(10)
        self.label.set_margin_start(20)
        self.label.set_margin_end(20)
        
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            window {
                background-color: rgba(0, 0, 0, 0.7);
                border-radius: 10px;
                color: white;
                font-weight: bold;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), 
            css_provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.set_child(self.label)

    def set_status(self, text):
        self.label.set_text(text)


class VozesApp(Adw.Application):
    def __init__(self, app_controller=None, **kwargs):
        super().__init__(application_id='org.vozes.Vozes', **kwargs)
        self.app_controller = app_controller
        self.overlay = None
        self.main_window = None
        
    def do_activate(self):
        if not self.main_window:
            self.main_window = VozesWindow(application=self, app_controller=self.app_controller)
        self.main_window.present()

    def show_overlay(self, status):
        if not self.overlay:
            self.overlay = OverlayWindow(application=self)
        self.overlay.set_status(status)
        self.overlay.present()
        
    def hide_overlay(self):
        if self.overlay:
            self.overlay.close()
            self.overlay = None

    def update_status(self, status_text, auto_hide=False):
        if status_text:
            self.show_overlay(status_text)
        else:
            self.hide_overlay()
            
        if auto_hide and status_text:
            GLib.timeout_add(2000, self.hide_overlay)
