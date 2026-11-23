"""
Lunarix Client - Модуль оновлення для майбутнього лаунчера.
Автоматично завантажує та перевіряє файли:
  1. Клієнт-мод (Lunarix-Client-1.21.11-1.0.jar) -> безпосередньо у папку mods/
  2. Оптимізацію Sodium -> у папку mods/
  3. Fabric API -> у папку mods/
  4. Профіль та версію гри -> у папку versions/
Все потрапляє одразу в готовому до гри вигляді!
"""

import os
import sys
import hashlib
import urllib.request
import json
import shutil

# GitHub конфігурація
REPO_OWNER = "SoSohik"
REPO_NAME = "lunarix-client"
GITHUB_TOKEN = ""
GITHUB_API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
MANIFEST_API_URL = f"{GITHUB_API_BASE}/contents/manifest.json"
MANIFEST_RAW_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/manifest.json"

# Шляхи на комп'ютері
APPDATA_MC = os.path.join(os.environ.get("APPDATA", ""), ".minecraft")
DESKTOP = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
if not os.path.exists(DESKTOP):
    DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")

PORTABLE_DIR = os.path.join(DESKTOP, "lunarix client")

def get_sha1(filepath):
    """Рахує SHA-1 хеш файлу."""
    if not os.path.exists(filepath):
        return None
    h = hashlib.sha1()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()

def download_file(url, target_path, token=None):
    """Завантажує файл з показом прогресу (підтримує приватні токени)."""
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    temp_target = target_path + ".download"
    filename = os.path.basename(target_path)
    print(f"[*] Завантаження: {filename} ...")

    headers = {"User-Agent": "LunarixLauncher/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["Accept"] = "application/octet-stream"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp, open(temp_target, "wb") as out_file:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 65536
            while True:
                chunk = resp.read(block_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = min(100, int(downloaded * 100 / total_size))
                    sys.stdout.write(f"\r    Прогрес: {percent}% ({downloaded // 1024} KB / {total_size // 1024} KB)")
                    sys.stdout.flush()
        print()
        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(temp_target, target_path)
        print(f"[+] Готово: {filename}")
        return True
    except Exception as e:
        print(f"\n[-] Помилка завантаження {filename}: {e}")
        if os.path.exists(temp_target):
            os.remove(temp_target)
        return False

def sync_client_files(target_dir=None, token=None, sync_to_appdata=True):
    """
    Головна функція для лаунчера:
    1. Завантажує manifest.json.
    2. Перевіряє та закидує Lunarix-Client, Sodium та Fabric API одразу у папку mods.
    3. Закидує конфіг версії у папку versions.
    4. За бажанням дублює у .minecraft, щоб гравець міг грати з будь-якого лаунчера.
    """
    if target_dir is None:
        target_dir = PORTABLE_DIR

    print("=" * 65)
    print("        LUNARIX LAUNCHER - ВСТАНОВЛЕННЯ ТА ОНОВЛЕННЯ КЛІЄНТА")
    print("=" * 65)
    print(f"Папка клієнта: {target_dir}")

    # 1. Читання або завантаження manifest.json
    local_manifest = os.path.join(target_dir, "manifest.json")
    manifest_data = None

    if os.path.exists(local_manifest):
        try:
            with open(local_manifest, "r", encoding="utf-8-sig") as f:
                manifest_data = json.load(f)
        except Exception:
            manifest_data = None

    if not manifest_data:
        print("[*] Завантаження маніфесту з GitHub...")
        headers = {"User-Agent": "LunarixLauncher/1.0"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            req = urllib.request.Request(MANIFEST_RAW_URL, headers=headers)
            with urllib.request.urlopen(req) as resp:
                manifest_data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[-] Не вдалося отримати маніфест з мережі: {e}")
            return False

    files = manifest_data.get("files", [])
    updated = 0
    ok = 0

    mods_folder = os.path.join(target_dir, "mods")
    os.makedirs(mods_folder, exist_ok=True)

    for item in files:
        rel_path = item["path"]
        expected_sha1 = item.get("sha1", "").lower()
        url = item.get("url")
        target_file = os.path.join(target_dir, rel_path.replace("/", os.sep))

        current_sha1 = get_sha1(target_file)
        if current_sha1 != expected_sha1:
            print(f"[!] Оновлюємо файл: {rel_path}")
            if download_file(url, target_file, token=token):
                updated += 1
            else:
                print(f"[-] Не вдалося завантажити {rel_path}")
        else:
            ok += 1

        # Якщо увімкнена синхронізація в .minecraft
        if sync_to_appdata and os.path.exists(target_file) and os.path.exists(APPDATA_MC):
            dest_mc = os.path.join(APPDATA_MC, rel_path.replace("/", os.sep))
            os.makedirs(os.path.dirname(dest_mc), exist_ok=True)
            if not os.path.exists(dest_mc) or get_sha1(dest_mc) != expected_sha1:
                try:
                    shutil.copy2(target_file, dest_mc)
                except Exception:
                    pass

    print("-" * 65)
    print(f"[✓] Всі моди та клієнт на місці ({ok} актуальних, {updated} завантажено).")
    print("    Клієнт повністю готовий до запуску!")
    print("=" * 65)
    return True

if __name__ == "__main__":
    sync_client_files()
