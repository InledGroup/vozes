import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Adw, GLib, Gio, Gdk
from config import config
from inference.downloader import ModelDownloader, MODELS
from utils.system_utils import apply_udev_rules
from utils.i18n import _
import threading
import os
from pathlib import Path

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
            self.set_subtitle(_("downloaded_click_to_use"))
        else:
            self.download_button.set_sensitive(True)
            self.download_button.set_icon_name("folder-download-symbolic")
            self.set_subtitle(_("not_downloaded"))

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
        self.status_label.set_text(_("completed"))
        self.check_status()
        self.on_download_complete(self.model_name, path)

    def handle_error(self, error_msg):
        self.download_button.set_sensitive(True)
        self.progress_bar.set_visible(False)
        self.status_label.set_text(_("error", error_msg=error_msg))


class VozesWindow(Adw.ApplicationWindow):
    def __init__(self, app_controller=None, **kwargs):
        super().__init__(**kwargs)
        self.app_controller = app_controller
        self.set_title(_("app_title"))
        self.set_default_size(800, 600)
        
        self.downloader = ModelDownloader(config.get("models_dir"))
        
        # Navigation Split View (Sidebar + Content)
        self.split_view = Adw.NavigationSplitView()
        self.set_content(self.split_view)
        
        # Sidebar
        sidebar_page = Adw.NavigationPage(title=_("menu"))
        self.split_view.set_sidebar(sidebar_page)
        
        sidebar_toolbar = Adw.ToolbarView()
        sidebar_page.set_child(sidebar_toolbar)
        
        sidebar_header = Adw.HeaderBar()
        sidebar_toolbar.add_top_bar(sidebar_header)
        
        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.add_css_class("navigation-sidebar")
        self.sidebar_list.connect("row-selected", self.on_sidebar_row_selected)
        sidebar_toolbar.set_content(self.sidebar_list)
        
        self.add_sidebar_row(_("home"), "go-home-symbolic", "home")
        self.add_sidebar_row(_("general"), "preferences-system-symbolic", "general")
        self.add_sidebar_row(_("models"), "folder-download-symbolic", "models")
        self.add_sidebar_row(_("system"), "system-run-symbolic", "system")
        
        # Content Pages
        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        content_page = Adw.NavigationPage(title=_("app_title"))
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
            self.content_stack.set_visible_child_name(_("assistant"))
            
            # If permissions are OK but model is missing, skip to step 2
            if os.access("/dev/uinput", os.W_OK):
                self.onboarding_stack.set_visible_child_name("step2")
        else:
            self.sidebar_list.select_row(self.sidebar_list.get_row_at_index(0))
            self.content_stack.set_visible_child_name(_("home"))

    def add_sidebar_row(self, title, icon_name, name=None):
        row = Adw.ActionRow(title=title)
        row.add_prefix(Gtk.Image(icon_name=icon_name))
        row.set_activatable(True)
        row._internal_name = name or title
        self.sidebar_list.append(row)

    def on_sidebar_row_selected(self, listbox, row):
        if row:
            self.content_stack.set_visible_child_name(row._internal_name)

    def init_onboarding_page(self):
        self.onboarding_stack = Gtk.Stack()
        self.onboarding_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        # Slide 1: Permissions
        step1 = Adw.StatusPage(title=_("step1_title"),
                              description=_("step_udev_desc"))
        step1.set_icon_name("system-run-symbolic")
        
        btn_fix = Gtk.Button(label=_("btn_fix_udev"))
        btn_fix.add_css_class("suggested-action")
        btn_fix.set_halign(Gtk.Align.CENTER)
        btn_fix.connect("clicked", self.on_onboarding_fix_permissions)
        
        step1_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        step1_box.append(btn_fix)
        step1.set_child(step1_box)
        self.onboarding_stack.add_titled(step1, "step1", _("permissions"))
        
        # Slide 2: Model
        step2 = Adw.StatusPage(title=_("step2_title"),
                              description=_("step_model_desc"))
        step2.set_icon_name("folder-download-symbolic")
        
        model_list = Gtk.ListBox()
        model_list.add_css_class("boxed-list")
        model_list.set_margin_start(50)
        model_list.set_margin_end(50)
        
        for m_name in MODELS.keys():
            row = ModelRow(m_name, self.downloader, self.on_onboarding_model_downloaded)
            model_list.append(row)
            
        step2.set_child(model_list)
        self.onboarding_stack.add_titled(step2, "step2", _("model"))
        
        # Slide 3: Ready
        step3 = Adw.StatusPage(title=_("step3_title"),
                              description=_("finish"))
        
        # Try to load custom logo
        # Path detection relative to this file: src/gui/app.py
        root_dir = Path(__file__).parent.parent.parent
        logo_paths = [
            root_dir / "vozes.png", # Root in dev mode
            root_dir / "data" / "vozes.png", # data/ in dev mode
            Path("/usr/share/vozes/data/vozes.png"), # Installed path
        ]
        
        logo_shown = False
        for p in logo_paths:
            if p and p.exists():
                try:
                    texture = Gdk.Texture.new_from_filename(str(p))
                    if texture:
                        step3.set_paintable(texture)
                        logo_shown = True
                        break
                except Exception as e:
                    print(f"Error loading logo from {p}: {e}")
            elif not p:
                continue
        
        if not logo_shown:
            step3.set_icon_name("emblem-ok-symbolic")
        
        btn_finish = Gtk.Button(label=_("btn_start"))
        btn_finish.add_css_class("suggested-action")
        btn_finish.set_halign(Gtk.Align.CENTER)
        btn_finish.connect("clicked", lambda b: self.content_stack.set_visible_child_name("home"))
        step3.set_child(btn_finish)
        self.onboarding_stack.add_titled(step3, "step3", _("finish"))
        
        self.content_stack.add_titled(self.onboarding_stack, "assistant", _("guided_setup"))
        self.add_sidebar_row(_("guided_setup"), "view-list-bullet-symbolic", "assistant")

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
        group = Adw.PreferencesGroup(title=_("welcome_title"))
        page.add(group)
        
        welcome_row = Adw.ActionRow(title=_("quick_guide"))
        welcome_row.set_subtitle(_("quick_guide_sub"))
        group.add(welcome_row)
        
        steps = [
            ("1. " + _("permissions"), _("step_udev_desc"), "system-run-symbolic"),
            ("2. " + _("model"), _("step_model_desc"), "folder-download-symbolic"),
            ("3. " + _("ready"), _("step_hotkey_desc"), "audio-input-microphone-symbolic"),
        ]
        
        for title, sub, icon in steps:
            r = Adw.ActionRow(title=title, subtitle=sub)
            r.add_prefix(Gtk.Image(icon_name=icon))
            group.add(r)
            
        self.content_stack.add_titled(page, "home", _("home"))

    def init_general_page(self):
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title=_("inference_config"))
        page.add(group)
        
        self.bin_row = Adw.EntryRow(title=_("whisper_bin_path"))
        self.bin_row.set_text(config.get("whisper_bin_path", ""))
        self.bin_row.connect("changed", lambda r: config.set("whisper_bin_path", r.get_text()))
        group.add(self.bin_row)
        
        self.model_row = Adw.EntryRow(title=_("model_path"))
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
        
        self.lang_row = Adw.ComboRow(title=_("dictation_lang"))
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
        
        # Application Language Selection
        app_languages = {
            "es": "Español",
            "en": "English",
            "auto": "Auto-detectar"
        }
        
        self.app_lang_row = Adw.ComboRow(title="Idioma de la aplicación / App Language")
        app_model = Gtk.StringList()
        app_lang_keys = list(app_languages.keys())
        for lang_name in app_languages.values():
            app_model.append(lang_name)
        self.app_lang_row.set_model(app_model)
        
        current_app_lang = config.get("app_language") or "auto"
        if current_app_lang in app_lang_keys:
            self.app_lang_row.set_selected(app_lang_keys.index(current_app_lang))
            
        self.app_lang_row.connect("notify::selected", self.on_app_language_changed, app_lang_keys)
        group.add(self.app_lang_row)
        
        group2 = Adw.PreferencesGroup(title=_("input_shortcuts"))
        page.add(group2)
        
        self.manual_row = Adw.SwitchRow(title=_("manual_control"))
        self.manual_row.set_subtitle(_("manual_control_sub"))
        self.manual_row.set_active(config.get("manual_mode", True))
        self.manual_row.connect("notify::active", self.on_manual_mode_changed)
        group2.add(self.manual_row)
        
        self.hotkey_row = Adw.EntryRow(title=_("hotkey_label"))
        self.hotkey_row.set_text(config.get("hotkey", "KEY_F12"))
        self.hotkey_row.connect("changed", lambda r: config.set("hotkey", r.get_text()))
        group2.add(self.hotkey_row)
        
        self.content_stack.add_titled(page, "general", _("general"))

    def on_language_changed(self, combo, pspec, lang_keys):
        selected_idx = combo.get_selected()
        lang_code = lang_keys[selected_idx]
        config.set("language", lang_code)
        print(f"Language changed to: {lang_code}")

    def on_app_language_changed(self, combo, pspec, lang_keys):
        selected_idx = combo.get_selected()
        lang_code = lang_keys[selected_idx]
        if lang_code == "auto":
            config.set("app_language", None)
        else:
            config.set("app_language", lang_code)
        print(f"App language changed to: {lang_code}. Restart needed for full effect.")
        # Note: In a real app we would probably use gettext and reload the UI,
        # but for this simple dictionary approach, a restart is easiest.
        # Alternatively, we could manually update all labels here.

    def on_manual_mode_changed(self, switch, pspec):
        is_active = switch.get_active()
        config.set("manual_mode", is_active)
        if self.app_controller and self.app_controller.audio:
            self.app_controller.audio.manual_mode = is_active
        print(f"Manual mode changed to: {is_active}")

    def init_models_page(self):
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title=_("download_models"))
        page.add(group)
        
        for m_name in MODELS.keys():
            row = ModelRow(m_name, self.downloader, self.on_model_downloaded)
            group.add(row)
            
        self.content_stack.add_titled(page, "models", _("models"))

    def on_model_downloaded(self, name, path):
        # Automatically set the downloaded model path
        self.model_row.set_text(path)
        config.set("model_path", path)

    def init_system_page(self):
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title=_("sys_permissions"))
        page.add(group)
        
        row = Adw.ActionRow(title=_("udev_rules_title"), 
                            subtitle=_("udev_rules_sub"))
        
        btn = Gtk.Button(label=_("btn_apply"))
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", self.on_apply_udev_clicked)
        row.add_suffix(btn)
        group.add(row)
        
        self.content_stack.add_titled(page, "system", _("system"))

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
        self.set_can_focus(False)
        self.set_focusable(False)
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
        # Default ID if not provided
        app_id = kwargs.pop('application_id', 'org.vozes.Vozes')
        super().__init__(application_id=app_id, **kwargs)
        self.app_controller = app_controller
        self.overlay = None
        self.main_window = None
        
    def do_activate(self):
        print("Activating Vozes GUI...")
        if not self.main_window:
            print("Creating main window...")
            self.main_window = VozesWindow(application=self, app_controller=self.app_controller)
        print("Presenting main window...")
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
