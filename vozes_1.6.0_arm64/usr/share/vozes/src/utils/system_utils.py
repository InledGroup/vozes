import subprocess
import os
from pathlib import Path

def apply_udev_rules():
    """
    Applies udev rules using pkexec for privilege escalation.
    """
    rules_content = """# Allow users in 'input' group to read and write to /dev/uinput
KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"

# Allow users in 'input' group to read from /dev/input/event*
SUBSYSTEM=="input", KERNEL=="event*", MODE="0660", GROUP="input"

# Specifically tag Vozes Virtual Keyboard as a keyboard for Wayland compositors
SUBSYSTEM=="input", ATTRS{name}=="Vozes-Virtual-Keyboard", ENV{ID_INPUT}="1", ENV{ID_INPUT_KEYBOARD}="1", TAG+="uaccess"
"""
    
    # We create a temporary script to do all root actions at once
    script_path = "/tmp/vozes_udev_setup.sh"
    real_user = os.environ.get('USER') or os.getlogin()
    
    with open(script_path, "w") as f:
        f.write(f"#!/bin/bash\n")
        f.write(f"echo '{rules_content}' > /etc/udev/rules.d/99-vozes.rules\n")
        f.write(f"udevadm control --reload-rules\n")
        f.write(f"udevadm trigger\n")
        f.write(f"getent group input >/dev/null || groupadd -r input\n")
        f.write(f"usermod -aG input {real_user}\n")
        # Forzar permisos para la sesión actual
        f.write(f"chown {real_user}:input /dev/uinput || true\n")
        f.write(f"chmod 666 /dev/uinput || true\n")
        f.write(f"chmod 666 /dev/input/event* || true\n")
        f.write(f"echo 'Permisos aplicados para {real_user}'\n")
        
    os.chmod(script_path, 0o755)
    
    # Run the script with pkexec
    try:
        subprocess.run(["pkexec", "/bin/bash", script_path], check=True)
        return True, "Reglas aplicadas correctamente. Reinicie sesión para aplicar cambios de grupo."
    except subprocess.CalledProcessError as e:
        return False, f"Error al aplicar reglas: {e}"
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)
