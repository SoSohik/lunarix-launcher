import os
import sys
import time
import hashlib
import json
import urllib.request
import urllib.error
import shutil
from core.modrinth import install_mod_from_modrinth

REPO_OWNER = "SoSohik"
REPO_NAME = "lunarix-client"
GITHUB_API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
GITHUB_TOKEN = ""
USER_AGENT = "LunarixLauncher/1.0"

MC_VERSION = "1.21.11"
VERSION_NAME = f"Lunarix Client {MC_VERSION}"
FABRIC_API_JAR = "fabric-api-0.141.6-1.21.11.jar"
SODIUM_JAR = "sodium-fabric-0.8.15-beta.1+mc1.21.11.jar"
# Managed jars from incompatible versions must not stay in mods/, they crash the game.
STALE_MOD_JARS = {
    "fabric-api-0.161.0+26.2.jar",
    "sodium-fabric-0.9.2+mc26.2.jar",
    "sodium-fabric-0.8.14+mc1.21.11.jar",
    "Lunarix-Client-26.2-1.0.jar",
    "Lunarix-Client-26.2-1.1.jar",
    "Lunarix-Client-26.2-1.2.jar",
}

def get_headers(accept="application/json"):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": accept
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers

def get_sha1(filepath):
    if not os.path.exists(filepath):
        return None
    h = hashlib.sha1()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()

def get_latest_github_release():
    """Отримує найсвіжіший реліз з GitHub репозиторію."""
    url = f"{GITHUB_API_BASE}/releases/latest"
    req = urllib.request.Request(url, headers=get_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # If /latest 404s, fallback to first in /releases
        try:
            req_all = urllib.request.Request(f"{GITHUB_API_BASE}/releases", headers=get_headers())
            with urllib.request.urlopen(req_all, timeout=10) as resp:
                releases = json.loads(resp.read().decode("utf-8"))
                if releases:
                    return releases[0]
        except Exception:
            pass
    except Exception as e:
        print(f"Error fetching latest release: {e}")
    return None

def fetch_remote_manifest():
    """Отримує актуальний manifest.json напряму через GitHub API."""
    url = f"{GITHUB_API_BASE}/contents/manifest.json"
    req = urllib.request.Request(url, headers=get_headers(accept="application/vnd.github.raw"))
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching manifest: {e}")
    return None

def download_github_asset(asset_url, target_path, progress_cb=None, expected_size=0, accept="application/octet-stream"):
    """Завантажує файл ассету релізу через GitHub API із підтримкою токену."""
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    temp_target = target_path + ".download"
    filename = os.path.basename(target_path)

    req = urllib.request.Request(asset_url, headers=get_headers(accept=accept))
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, open(temp_target, "wb") as out_file:
            total_size = int(resp.headers.get("Content-Length", expected_size))
            downloaded = 0
            block_size = 65536
            while True:
                chunk = resp.read(block_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total_size > 0:
                    pct = min(1.0, downloaded / total_size)
                    progress_cb(pct, f"Завантаження {filename}: {downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB")
        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(temp_target, target_path)
        return True
    except Exception as e:
        if os.path.exists(temp_target):
            os.remove(temp_target)
        raise e

def is_game_installed(game_dir):
    """Перевіряє, чи встановлено клієнт гри та актуальний мод."""
    if not game_dir or not os.path.exists(game_dir):
        return False
    
    # Check version files
    v_dir = os.path.join(game_dir, "versions", VERSION_NAME)
    v_jar = os.path.join(v_dir, f"{VERSION_NAME}.jar")
    v_json = os.path.join(v_dir, f"{VERSION_NAME}.json")
    
    # Check client mods
    mods_dir = os.path.join(game_dir, "mods")
    has_client_jar = False
    if os.path.exists(mods_dir):
        for f in os.listdir(mods_dir):
            if f.lower().startswith("lunarix-client") and f.lower().endswith(".jar"):
                has_client_jar = True
                break

    return os.path.exists(v_jar) and os.path.exists(v_json) and has_client_jar

def install_or_update_game(game_dir, progress_cb=None, log_cb=None):
    """
    Завантажує та оновлює гру виключно до останнього релізу з GitHub:
    1. Перевіряє останній реліз та manifest.json на GitHub
    2. Якщо знайдено нову версію мода Lunarix-Client — видаляє старі та завантажує актуальний реліз
    3. Завантажує бібліотеки версії, assets та необхідні моди (Fabric API, Sodium)
    """
    def log(msg):
        if log_cb:
            log_cb(msg)
        print(msg)

    log("[*] Перевірка оновлень на GitHub (найсвіжіший реліз)...")
    if progress_cb:
        progress_cb(0.05, "Перевірка останнього релізу на GitHub...")

    mods_dir = os.path.join(game_dir, "mods")
    versions_dir = os.path.join(game_dir, "versions", VERSION_NAME)
    os.makedirs(mods_dir, exist_ok=True)
    os.makedirs(versions_dir, exist_ok=True)

    # Drop launcher-managed jars that belong to other Minecraft versions.
    for stale in STALE_MOD_JARS:
        stale_path = os.path.join(mods_dir, stale)
        if os.path.exists(stale_path):
            try:
                os.remove(stale_path)
                log(f"[*] Видалено несумісний мод старої версії: {stale}")
            except Exception:
                pass

    appdata_mc = os.path.join(os.environ.get("APPDATA", ""), ".minecraft")

    # 1. Отримуємо останній реліз з GitHub
    rel = get_latest_github_release()
    tag_name = rel.get("tag_name", "v1.0.0") if rel else "v1.0.0"
    log(f"[*] Знайдено реліз на GitHub: {tag_name}")

    assets_by_name = {}
    if rel:
        for a in rel.get("assets", []):
            assets_by_name[a["name"]] = a

    # 2. Version JSON
    v_json_target = os.path.join(versions_dir, f"{VERSION_NAME}.json")
    need_v_json = not os.path.exists(v_json_target)
    if not need_v_json:
        try:
            with open(v_json_target, "r", encoding="utf-8") as vf:
                vcontent = vf.read()
                if "0.19.3" in vcontent or "0.17.3" in vcontent:
                    need_v_json = True
        except Exception:
            need_v_json = True

    if need_v_json:
        log(f"[*] Завантаження оновленого {VERSION_NAME}.json з GitHub...")
        json_api_url = f"{GITHUB_API_BASE}/contents/versions/Lunarix%20Client%201.21.11/Lunarix%20Client%201.21.11.json"
        try:
            download_github_asset(json_api_url, v_json_target, progress_cb=progress_cb, accept="application/vnd.github.raw")
        except Exception as e:
            print(f"Warning downloading version json from GitHub: {e}")
            local_json = os.path.join(appdata_mc, "versions", f"Fabric {MC_VERSION}", f"Fabric {MC_VERSION}.json")
            if os.path.exists(local_json):
                shutil.copy2(local_json, v_json_target)

    # 3. Version JAR (Minecraft core)
    v_jar_target = os.path.join(versions_dir, f"{VERSION_NAME}.jar")
    v_jar_asset = assets_by_name.get(f"{VERSION_NAME}.jar") or assets_by_name.get("Lunarix.Client.1.21.11.jar")
    need_v_jar = not os.path.exists(v_jar_target) or (v_jar_asset and os.path.getsize(v_jar_target) != v_jar_asset.get("size", 0))
    if need_v_jar:
        if v_jar_asset:
            log(f"[*] Завантаження {VERSION_NAME}.jar з GitHub...")
            download_github_asset(v_jar_asset["url"], v_jar_target, progress_cb=progress_cb, expected_size=v_jar_asset.get("size", 0))
        else:
            local_jar = os.path.join(appdata_mc, "versions", f"Fabric {MC_VERSION}", f"Fabric {MC_VERSION}.jar")
            if os.path.exists(local_jar):
                shutil.copy2(local_jar, v_jar_target)

    # 4. Natives
    natives_target = os.path.join(versions_dir, "natives")
    if not os.path.exists(natives_target) or not os.listdir(natives_target):
        mc_natives = os.path.join(appdata_mc, "versions", f"Fabric {MC_VERSION}", "natives")
        if os.path.exists(mc_natives):
            log("[*] Копіювання natives...")
            shutil.copytree(mc_natives, natives_target, dirs_exist_ok=True)
            for root, dirs, files in os.walk(natives_target):
                if root == natives_target:
                    continue
                for f in files:
                    if f.endswith(".dll"):
                        shutil.copy2(os.path.join(root, f), os.path.join(natives_target, f))

    # 4.5. Бібліотеки Minecraft/Fabric — докачуємо з Maven, щоб гра
    # запускалась без TLauncher/офіційного лаунчера (MixinBootstrap тощо)
    libs_ok = True
    try:
        from core.libraries import ensure_libraries
        libs_ok = ensure_libraries(v_json_target, natives_dir=natives_target, log_cb=log, progress_cb=progress_cb)
    except Exception as e:
        libs_ok = False
        log(f"[!] Помилка перевірки бібліотек: {e}")

    # 5. Core Client Mod: Завантаження останнього Lunarix-Client jar виключно з релізу GitHub
    if progress_cb:
        progress_cb(0.3, f"Перевірка версії клієнта ({tag_name})...")

    target_mod_name = None
    target_mod_asset = None
    if rel:
        for a_name, a_data in assets_by_name.items():
            if a_name.lower().startswith("lunarix-client") and a_name.endswith(".jar"):
                target_mod_name = a_name
                target_mod_asset = a_data
                break

    if not target_mod_name:
        target_mod_name = "Lunarix-Client-1.21.11-1.0.jar"

    target_mod_path = os.path.join(mods_dir, target_mod_name)

    # Видаляємо застарілі версії клієнта, якщо встановлюється нова
    for f in os.listdir(mods_dir):
        if f.lower().startswith("lunarix-client") and f.lower().endswith(".jar") and f != target_mod_name:
            log(f"[*] Видалення застарілої версії клієнта: {f}")
            try:
                os.remove(os.path.join(mods_dir, f))
            except Exception:
                pass

    need_mod_download = False
    if not os.path.exists(target_mod_path):
        need_mod_download = True
    elif target_mod_asset and target_mod_asset.get("size", 0) > 0:
        if os.path.getsize(target_mod_path) != target_mod_asset["size"]:
            need_mod_download = True

    if need_mod_download:
        if target_mod_asset:
            log(f"[*] Завантаження останньої версії Lunarix Client ({target_mod_name}) напряму з GitHub релізу...")
            download_github_asset(target_mod_asset["url"], target_mod_path, progress_cb=progress_cb, expected_size=target_mod_asset.get("size", 0))
            log(f"[✓] {target_mod_name} успішно завантажено з GitHub!")
        else:
            local_mod = os.path.join(appdata_mc, "mods", "Lunarix-Client-1.21.11-1.0.jar")
            if os.path.exists(local_mod):
                shutil.copy2(local_mod, target_mod_path)

    # 6. Fabric API
    if progress_cb:
        progress_cb(0.6, "Перевірка Fabric API...")
    fapi_target = os.path.join(mods_dir, FABRIC_API_JAR)
    fapi_asset = assets_by_name.get(FABRIC_API_JAR)
    need_fapi = not os.path.exists(fapi_target) or (fapi_asset and os.path.getsize(fapi_target) != fapi_asset.get("size", 0))
    if need_fapi:
        if fapi_asset:
            log("[*] Завантаження Fabric API з GitHub релізу...")
            download_github_asset(fapi_asset["url"], fapi_target, progress_cb=progress_cb, expected_size=fapi_asset.get("size", 0))
        else:
            local_fapi = os.path.join(appdata_mc, "mods", FABRIC_API_JAR)
            if os.path.exists(local_fapi):
                shutil.copy2(local_fapi, fapi_target)

    # 7. Sodium (GitHub Release або Modrinth)
    if progress_cb:
        progress_cb(0.8, "Перевірка Sodium...")
    sodium_target = os.path.join(mods_dir, SODIUM_JAR)
    sodium_asset = assets_by_name.get(SODIUM_JAR) or assets_by_name.get("sodium-fabric-0.8.15-beta.1.mc1.21.11.jar")
    need_sodium = not os.path.exists(sodium_target) or (sodium_asset and os.path.getsize(sodium_target) != sodium_asset.get("size", 0))
    if need_sodium:
        if sodium_asset:
            log("[*] Завантаження Sodium з GitHub релізу...")
            download_github_asset(sodium_asset["url"], sodium_target, progress_cb=progress_cb, expected_size=sodium_asset.get("size", 0))
        else:
            local_sodium = os.path.join(appdata_mc, "mods", SODIUM_JAR)
            if os.path.exists(local_sodium):
                shutil.copy2(local_sodium, sodium_target)
            else:
                install_mod_from_modrinth("sodium", mods_dir, progress_cb=progress_cb, game_version=MC_VERSION)

    if progress_cb:
        progress_cb(1.0, "Останній реліз готовий до запуску!")
    if libs_ok:
        log(f"[✓] Всі файли останнього релізу ({tag_name}) успішно підготовлені!")
    else:
        log(f"[!] Реліз {tag_name} підготовлено, але частину бібліотек не завантажено — "
            "гра може не запуститися. Перевірте інтернет або перевстановіть клієнт.")
    return libs_ok

LAUNCHER_VERSION = "1.3.4"

def is_newer_version(remote, current):
    """Перевіряє, чи віддалена версія новіша за поточну."""
    try:
        def parse(v):
            clean = str(v).lower().lstrip("v").strip()
            return [int(x) for x in clean.split(".") if x.isdigit()]
        r_parts = parse(remote)
        c_parts = parse(current)
        return r_parts > c_parts
    except Exception:
        return False

def check_launcher_update(current_version=LAUNCHER_VERSION):
    """
    Перевіряє наявність новішої версії самого лаунчера через manifest.json або GitHub Releases.
    Повертає (has_update: bool, update_info: dict) ТІЛЬКИ якщо знайдено вищу версію.
    """
    try:
        manifest = fetch_remote_manifest()
        launcher_info = manifest.get("launcher") if manifest else None

        if launcher_info:
            remote_version = launcher_info.get("version", "")
            if remote_version and is_newer_version(remote_version, current_version):
                return True, launcher_info

        rel = get_latest_github_release()
        if rel:
            tag_name = rel.get("tag_name", "")
            if is_newer_version(tag_name, current_version):
                for asset in rel.get("assets", []):
                    if asset.get("name") in ("Lunarix Launcher.exe", "Lunarix.Launcher.exe"):
                        return True, {
                            "version": tag_name,
                            "url": asset.get("url"),
                            "size": asset.get("size", 0),
                            "filename": "Lunarix Launcher.exe"
                        }
    except Exception as e:
        print(f"[Launcher Update Check] Error: {e}")
    return False, None

def check_client_update(game_dir):
    """
    Проверяет, есть ли обновление Lunarix Client для установленной игры.
    Сравнивает локальный mods/Lunarix-Client*.jar с manifest.json на GitHub
    (по sha1) или, если манифест недоступен, с размером jar-асета последнего релиза.
    Возвращает (has_update: bool, update_info: dict).
    """
    try:
        if not game_dir or not os.path.isdir(game_dir):
            return False, None

        mods_dir = os.path.join(game_dir, "mods")
        local_jar = None
        if os.path.isdir(mods_dir):
            for f in os.listdir(mods_dir):
                fl = f.lower()
                if fl.startswith("lunarix-client") and fl.endswith(".jar"):
                    local_jar = os.path.join(mods_dir, f)
                    break

        if local_jar is None and not is_game_installed(game_dir):
            return False, None

        expected_sha1 = None
        expected_size = 0
        remote_version = ""

        manifest = fetch_remote_manifest()
        if manifest:
            remote_version = str(manifest.get("client_version", "") or "")
            for item in manifest.get("files", []):
                p = item.get("path", "")
                base = os.path.basename(p).lower()
                if p.startswith("mods/") and base.startswith("lunarix-client") and base.endswith(".jar"):
                    expected_sha1 = (item.get("sha1") or "").lower() or None
                    try:
                        expected_size = int(item.get("size") or 0)
                    except Exception:
                        expected_size = 0
                    break

        if not expected_sha1 and not expected_size:
            rel = get_latest_github_release()
            if not rel:
                return False, None
            remote_version = rel.get("tag_name", "") or remote_version
            for a in rel.get("assets", []):
                n = a.get("name", "")
                if n.lower().startswith("lunarix-client") and n.endswith(".jar"):
                    expected_size = int(a.get("size") or 0)
                    break

        if expected_sha1 is None and expected_size == 0:
            return False, None

        if local_jar is None:
            return True, {"version": remote_version or "new", "size": expected_size}

        if expected_sha1:
            if get_sha1(local_jar) != expected_sha1:
                return True, {
                    "version": remote_version or "new",
                    "size": expected_size,
                    "local_size": os.path.getsize(local_jar),
                }
            return False, None

        if expected_size and os.path.getsize(local_jar) != expected_size:
            return True, {
                "version": remote_version or "new",
                "size": expected_size,
                "local_size": os.path.getsize(local_jar),
            }
        return False, None
    except Exception as e:
        print(f"[Client Update Check] Error: {e}")
        return False, None

def apply_launcher_update(update_info, progress_cb=None):
    """
    Завантажує новий Lunarix Launcher.exe, замінює поточний файл і перезапускає лаунчер.
    """
    import subprocess
    is_frozen = getattr(sys, 'frozen', False)
    current_exe = sys.executable if is_frozen else os.path.join(os.getcwd(), "Lunarix Launcher.exe")
    exe_dir = os.path.dirname(current_exe)
    new_exe = os.path.join(exe_dir, "Lunarix Launcher.exe.new")

    asset_url = update_info.get("url")
    expected_size = update_info.get("size", 0)

    if not asset_url:
        rel = get_latest_github_release()
        if rel:
            for asset in rel.get("assets", []):
                if asset.get("name") == "Lunarix Launcher.exe":
                    asset_url = asset.get("url")
                    expected_size = asset.get("size", 0)
                    break

    if not asset_url:
        raise ValueError("Не знайдено посилання на оновлення лаунчера.")

    if progress_cb:
        progress_cb(0.1, "Завантаження оновлення лаунчера...")

    download_github_asset(asset_url, new_exe, progress_cb=progress_cb, expected_size=expected_size)

    expected_sha1 = update_info.get("sha1")
    if expected_sha1:
        dl_sha1 = get_sha1(new_exe)
        if dl_sha1 and dl_sha1.lower() != expected_sha1.lower():
            if os.path.exists(new_exe):
                os.remove(new_exe)
            raise ValueError("Помилка цілісності файлу оновлення (SHA-1 mismatch)")

    if progress_cb:
        progress_cb(1.0, "Оновлення встановлено. Перезапуск...")

    target_exe = current_exe
    if not is_frozen:
        target_exe = os.path.join(exe_dir, "Lunarix Launcher.exe")

    # Самооновлення без .bat і без cmd.
    # Windows дозволяє ПЕРЕЙМЕНУВАТИ запущений .exe, але не перезаписувати його.
    # Тому: старий exe -> .old, потім .new -> exe, запуск нового, вихід зі старого.
    # Це прибирає залежність від кодування консолі та кирилиці в шляху.
    old_exe = target_exe + ".old"
    log_path = os.path.join(exe_dir, "lunarix_update.log")

    def _ulog(msg):
        try:
            with open(log_path, "a", encoding="utf-8", errors="replace") as lf:
                lf.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
        except Exception:
            pass

    _ulog("update start")
    _ulog(f"target={target_exe}")
    _ulog(f"new={new_exe}")

    if not os.path.exists(new_exe):
        _ulog("FAILED: downloaded update file is missing")
        raise RuntimeError("Файл оновлення не знайдено після завантаження.")

    # 1. Відсуваємо старий exe в .old (з повторними спробами)
    if os.path.exists(target_exe):
        try:
            if os.path.exists(old_exe):
                os.remove(old_exe)
        except OSError as e:
            _ulog(f"warn: cannot remove stale .old: {e}")

        moved = False
        last_err = None
        for _ in range(20):
            try:
                os.replace(target_exe, old_exe)
                moved = True
                break
            except OSError as e:
                last_err = e
                time.sleep(0.25)
        if not moved:
            _ulog(f"FAILED: cannot rename old exe: {last_err}")
            raise RuntimeError(f"Не вдалося замінити файл лаунчера: {last_err}")

    # 2. Ставимо новий exe на місце старого
    try:
        os.replace(new_exe, target_exe)
    except OSError as e:
        _ulog(f"FAILED: cannot place new exe: {e}")
        try:
            if os.path.exists(old_exe) and not os.path.exists(target_exe):
                os.replace(old_exe, target_exe)
                _ulog("restored old exe")
        except OSError as re_err:
            _ulog(f"restore failed: {re_err}")
        raise RuntimeError(f"Не вдалося встановити оновлення: {e}")

    _ulog("update applied, launching new exe")

    # 3. Запускаємо оновлений лаунчер і завершуємо поточний процес
    try:
        subprocess.Popen(
            [target_exe],
            cwd=exe_dir,
            creationflags=0x00000008  # DETACHED_PROCESS
        )
    except Exception as e:
        _ulog(f"FAILED: cannot launch new exe: {e}")
        try:
            if os.path.exists(old_exe):
                os.replace(old_exe, target_exe)
                _ulog("restored old exe after launch failure")
                subprocess.Popen([target_exe], cwd=exe_dir, creationflags=0x00000008)
        except Exception:
            pass
        raise RuntimeError(f"Не вдалося запустити оновлений лаунчер: {e}")

    time.sleep(0.3)
    os._exit(0)


def cleanup_launcher_update_leftovers():
    """Прибирає .old/.new/.bat, що лишилися після самооновлення."""
    try:
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.getcwd()
        for name in ("Lunarix Launcher.exe.old",
                     "Lunarix Launcher.exe.new",
                     "_lunarix_updater.bat"):
            path = os.path.join(base, name)
            # Старий процес міг ще не встигнути завершитись - пробуємо кілька разів.
            for _ in range(6):
                try:
                    if not os.path.exists(path):
                        break
                    os.remove(path)
                    break
                except OSError:
                    time.sleep(0.3)
    except Exception:
        pass

