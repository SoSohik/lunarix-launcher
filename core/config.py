import os
import sys
import json
import shutil
import subprocess

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_data_dir():
    """
    Returns the persistent data directory for Lunarix Launcher.
    Primary target: C:\\Program Files\\lunarix launcher
    If write permissions are not available (non-admin execution), falls back
    seamlessly to C:\\ProgramData\\lunarix launcher or %APPDATA%\\lunarix launcher.
    """
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    primary_dir = os.path.join(program_files, "lunarix launcher")
    try:
        os.makedirs(primary_dir, exist_ok=True)
        test_file = os.path.join(primary_dir, ".perm_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return primary_dir
    except (PermissionError, OSError):
        fallback_dir = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "lunarix launcher")
        try:
            os.makedirs(fallback_dir, exist_ok=True)
            return fallback_dir
        except Exception:
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
            fallback_appdata = os.path.join(appdata, "lunarix launcher")
            os.makedirs(fallback_appdata, exist_ok=True)
            return fallback_appdata

def get_cache_dir():
    d = os.path.join(get_data_dir(), "cache")
    os.makedirs(d, exist_ok=True)
    return d

def get_thumbs_cache_dir():
    d = os.path.join(get_cache_dir(), "thumbs")
    os.makedirs(d, exist_ok=True)
    return d

def get_avatars_cache_dir():
    d = os.path.join(get_cache_dir(), "avatars")
    os.makedirs(d, exist_ok=True)
    return d

CONFIG_FILE = os.path.join(get_data_dir(), "config.json")
OLD_CONFIG_FILE = os.path.join(get_base_dir(), "config.json")

ALTS_FILE = os.path.join(get_data_dir(), "alts.json")
OLD_ALTS_FILE = os.path.join(get_base_dir(), "alts.json")

AUTH_FILE = os.path.join(get_data_dir(), "auth_session.json")
OLD_AUTH_FILE = os.path.join(get_base_dir(), "auth_session.json")

def get_default_desktop():
    onedrive = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
    if os.path.exists(onedrive):
        return onedrive
    return os.path.join(os.path.expanduser("~"), "Desktop")

DEFAULT_GAME_DIR = os.path.join(get_default_desktop(), "lunarix client")

def detect_java():
    candidates = [
        r"C:\Program Files\Java\jdk-21\bin\javaw.exe",
        r"C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\javaw.exe",
        r"C:\Program Files\Zulu\zulu-21-jre\bin\javaw.exe",
        r"C:\Program Files\Java\jdk-25\bin\javaw.exe"
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return "javaw.exe"

DEFAULT_CONFIG = {
    "username": "Player",
    "display_name": "Player",
    "avatar_path": "",
    "share_cosmetics": True,
    "see_other_cosmetics": True,
    "game_dir": DEFAULT_GAME_DIR,
    "ram_gb": 4,
    "java_path": detect_java(),
    "jvm_args": "-XX:+UnlockExperimentalVMOptions -XX:+UseG1GC -XX:G1NewSizePercent=20 -XX:G1ReservePercent=20 -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=32M",
    "width": 1280,
    "height": 720,
    "fullscreen": False,
    "lang": "uk",
    "animated_background": False
}

def load_config():
    # If not yet in new data dir, migrate from old base dir if present
    target_path = CONFIG_FILE
    if not os.path.exists(target_path) and os.path.exists(OLD_CONFIG_FILE):
        try:
            shutil.copy2(OLD_CONFIG_FILE, target_path)
        except Exception:
            target_path = OLD_CONFIG_FILE

    if os.path.exists(target_path):
        try:
            with open(target_path, "rb") as f:
                raw_bytes = f.read()
            if raw_bytes.startswith(b'\xef\xbb\xbf'):
                raw_bytes = raw_bytes[3:]
            data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
            cfg = dict(DEFAULT_CONFIG)
            cfg.update(data)
            return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Failed to save config: {e}")
        return False

def clear_all_launcher_data():
    """
    Clears all saved launcher info, configs, caches, accounts, and session data.
    """
    data_dir = get_data_dir()
    try:
        if os.path.exists(data_dir):
            for item in os.listdir(data_dir):
                item_path = os.path.join(data_dir, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)
                    else:
                        os.remove(item_path)
                except Exception:
                    pass
    except Exception as e:
        print("Clear data dir error:", e)

    # Clean old locations too
    for old_path in [
        OLD_CONFIG_FILE, OLD_ALTS_FILE, OLD_AUTH_FILE,
        os.path.join(get_base_dir(), "assets", "thumbs"),
        os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "lunarix launcher"),
        os.path.join(os.environ.get("APPDATA", ""), "LunarixClient")
    ]:
        try:
            if os.path.isdir(old_path):
                shutil.rmtree(old_path, ignore_errors=True)
            elif os.path.exists(old_path):
                os.remove(old_path)
        except Exception:
            pass

def restart_launcher():
    """
    Relaunches the launcher process and exits current one.
    """
    try:
        if getattr(sys, 'frozen', False):
            subprocess.Popen([sys.executable])
        else:
            python_exe = sys.executable
            main_script = os.path.abspath(sys.argv[0])
            subprocess.Popen([python_exe, main_script] + sys.argv[1:])
    except Exception as e:
        print("Restart error:", e)
    sys.exit(0)

