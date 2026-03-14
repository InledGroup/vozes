import locale
import os
from config import config

TRANSLATIONS = {
    "es": {
        "app_title": "Vozes",
        "ready": "Listo",
        "downloaded_click_to_use": "Descargado - Haga clic para usar",
        "not_downloaded": "No descargado",
        "completed": "¡Completado!",
        "error": "Error: {error_msg}",
        "menu": "Menú",
        "guided_setup": "Configuración Guiada",
        "step1_title": "Paso 1: Permisos de Hardware",
        "btn_fix_udev": "Configurar con pkexec",
        "permissions": "Permisos",
        "step2_title": "Paso 2: Descargar Modelo",
        "model": "Modelo",
        "step3_title": "¡Todo listo!",
        "btn_start": "Empezar a usar",
        "finish": "Finalizar",
        "assistant": "Asistente",
        "welcome_title": "Bienvenido a Vozes",
        "quick_guide": "Guía de inicio rápido",
        "quick_guide_sub": "Siga estos pasos para empezar a dictar",
        "home": "Inicio",
        "inference_config": "Configuración de Inferencia",
        "whisper_bin_path": "Ruta Binario whisper.cpp",
        "model_path": "Ruta del Modelo (.bin)",
        "dictation_lang": "Idioma de dictado",
        "input_shortcuts": "Entrada y Atajos",
        "manual_control": "Control Manual (Pulsar para parar)",
        "manual_control_sub": "Si está activo, debe volver a pulsar la tecla para terminar de dictar",
        "hotkey_label": "Hotkey (código evdev)",
        "general": "General",
        "download_models": "Descargar Modelos",
        "models": "Modelos",
        "sys_permissions": "Permisos y Hardware",
        "udev_rules_title": "Configurar permisos udev",
        "udev_rules_sub": "Permite acceso a entrada de teclado y dispositivos virtuales sin root",
        "btn_apply": "Aplicar con pkexec",
        "system": "Sistema",
        "status_ready": "Listo para dictar",
        "status_recording": "Grabando...",
        "status_transcribing": "Transcribiendo...",
        "step_udev_desc": "Configurar permisos de sistema para el teclado virtual",
        "step_model_desc": "Descargar un modelo de lenguaje para el reconocimiento",
        "step_hotkey_desc": "Configurar la tecla para activar el dictado (F12 por defecto)",
    },
    "en": {
        "app_title": "Vozes",
        "ready": "Ready",
        "downloaded_click_to_use": "Downloaded - Click to use",
        "not_downloaded": "Not downloaded",
        "completed": "Completed!",
        "error": "Error: {error_msg}",
        "menu": "Menu",
        "guided_setup": "Guided Setup",
        "step1_title": "Step 1: Hardware Permissions",
        "btn_fix_udev": "Configure with pkexec",
        "permissions": "Permissions",
        "step2_title": "Step 2: Download Model",
        "model": "Model",
        "step3_title": "All set!",
        "btn_start": "Start using",
        "finish": "Finish",
        "assistant": "Assistant",
        "welcome_title": "Welcome to Vozes",
        "quick_guide": "Quick start guide",
        "quick_guide_sub": "Follow these steps to start dictating",
        "home": "Home",
        "inference_config": "Inference Configuration",
        "whisper_bin_path": "whisper.cpp Binary Path",
        "model_path": "Model Path (.bin)",
        "dictation_lang": "Dictation Language",
        "input_shortcuts": "Input & Shortcuts",
        "manual_control": "Manual Control (Push to stop)",
        "manual_control_sub": "If active, you must press the key again to stop dictating",
        "hotkey_label": "Hotkey (evdev code)",
        "general": "General",
        "download_models": "Download Models",
        "models": "Models",
        "sys_permissions": "Permissions & Hardware",
        "udev_rules_title": "Configure udev rules",
        "udev_rules_sub": "Allows access to keyboard input and virtual devices without root",
        "btn_apply": "Apply with pkexec",
        "system": "System",
        "status_ready": "Ready to dictate",
        "status_recording": "Recording...",
        "status_transcribing": "Transcribing...",
        "step_udev_desc": "Configure system permissions for the virtual keyboard",
        "step_model_desc": "Download a language model for recognition",
        "step_hotkey_desc": "Configure the key to activate dictation (F12 by default)",
    }
}

def get_system_lang():
    try:
        lang = locale.getdefaultlocale()[0]
        if lang:
            return lang.split('_')[0]
    except:
        pass
    return "en"

# Current language from config or system
_lang = config.get("app_language")
if not _lang:
    _lang = get_system_lang()
    if _lang not in TRANSLATIONS:
        _lang = "en"

def _(key, **kwargs):
    lang = config.get("app_language", _lang)
    if lang not in TRANSLATIONS:
        lang = "en"
    
    text = TRANSLATIONS[lang].get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text
