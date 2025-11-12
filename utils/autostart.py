# utils/autostart.py
import sys
import os
import platform

def enable_autostart(app_name: str, script_path: str) -> bool:
    """
    尝试启用开机自启。实现会根据平台写入启动项或给出指示。
    注意：写系统启动项通常需要权限；这里尽量自动化但也提供回退说明。
    Returns True if operation succeeded (best-effort).
    """
    system = platform.system()
    try:
        if system == "Windows":
            # create a shortcut in the Startup folder
            startup = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
            # create a .lnk requires pywin32; as fallback, create a .bat
            bat_path = os.path.join(startup, f"start_{app_name}.bat")
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(f'python "{script_path}"\n')
            return True
        elif system == "Linux":
            # write a .desktop autostart entry
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            desktop_file = os.path.join(autostart_dir, f"{app_name}.desktop")
            with open(desktop_file, "w", encoding="utf-8") as f:
                f.write(f"[Desktop Entry]\nType=Application\nExec=python3 {script_path}\nHidden=false\nNoDisplay=false\nX-GNOME-Autostart-enabled=true\nName={app_name}\n")
            return True
        elif system == "Darwin":
            # macOS: instruct user to create a LaunchAgent plist or use osascript to register
            # Here we return False but user can be instructed to use launchctl / create plist
            return False
        else:
            return False
    except Exception as e:
        print("autostart enable failed:", e)
        return False

def disable_autostart(app_name: str) -> bool:
    # implement reverse actions if desired
    return True
