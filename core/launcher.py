import os
import sys
import glob
import re
import shutil
import ctypes
import zipfile
import urllib.request
import subprocess
import threading
import json

MC_VERSION = "1.21.11"
VERSION_NAME = f"Lunarix Client {MC_VERSION}"

# Мінімальна Java для Minecraft 1.21.x
MIN_JAVA_MAJOR = 21
ADOPTIUM_JRE_URL = (
    "https://api.adoptium.net/v3/binary/latest/21/ga/windows/x64/jre/hotspot/normal/eclipse"
)

_JAVA_PROBE_CACHE = {}


def _probe_java(exe):
    """Повертає (major_version, is_64bit) для java(w).exe."""
    if exe in _JAVA_PROBE_CACHE:
        return _JAVA_PROBE_CACHE[exe]

    probe = exe
    if os.path.basename(exe).lower() == "javaw.exe":
        sibling = os.path.join(os.path.dirname(exe), "java.exe")
        if os.path.isfile(sibling):
            probe = sibling

    info = (0, False)
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        res = subprocess.run(
            [probe, "-XshowSettings:properties", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=15,
            creationflags=flags,
        )
        out = res.stdout or ""
        m_ver = re.search(r"java\.specification\.version\s*=\s*(\d+)", out)
        m_arch = re.search(r"sun\.arch\.data\.model\s*=\s*(\d+)", out)
        major = int(m_ver.group(1)) if m_ver else 0
        is64 = bool(m_arch and m_arch.group(1) == "64")
        info = (major, is64)
    except Exception:
        pass

    _JAVA_PROBE_CACHE[exe] = info
    return info


def _registry_java_homes():
    """JavaHome з реєстру Windows (Oracle/Adoptium/Zulu тощо)."""
    homes = []
    if os.name != "nt":
        return homes
    try:
        import winreg
    except Exception:
        return homes

    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\JDK"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\JRE"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\Java Development Kit"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft\Java Runtime Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\JavaSoft\JDK"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\JavaSoft\JRE"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Eclipse Adoptium\JDK"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Eclipse Foundation\JDK"),
    ]
    for root, sub in keys:
        try:
            with winreg.OpenKey(root, sub) as key:
                subkeys = []
                try:
                    i = 0
                    while True:
                        subkeys.append(winreg.EnumKey(key, i))
                        i += 1
                except OSError:
                    pass
                for name in subkeys:
                    try:
                        with winreg.OpenKey(key, name) as sk:
                            home, _ = winreg.QueryValueEx(sk, "JavaHome")
                            if home:
                                homes.append(home)
                    except OSError:
                        pass
        except OSError:
            pass
    return homes


def _portable_java_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Local"
    )
    return os.path.join(base, "LunarixLauncher", "runtime", "jre21")


def _java_candidates(java_exe=None, game_dir=None):
    candidates = []

    def add(value):
        if not value:
            return
        try:
            value = os.path.expandvars(os.path.expanduser(str(value).strip().strip('"')))
        except Exception:
            return
        if value and value not in candidates:
            candidates.append(value)

    add(java_exe)

    for home in _registry_java_homes():
        add(os.path.join(home, "bin", "javaw.exe"))
        add(os.path.join(home, "bin", "java.exe"))

    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        add(os.path.join(java_home, "bin", "javaw.exe"))
        add(os.path.join(java_home, "bin", "java.exe"))

    try:
        from core.config import detect_java
        add(detect_java())
    except Exception:
        pass

    # Власний завантажений JRE лаунчера
    add(os.path.join(_portable_java_dir(), "bin", "javaw.exe"))

    if game_dir:
        for pattern in (
            os.path.join(game_dir, "runtime", "**", "bin", "javaw.exe"),
            os.path.join(game_dir, "jre", "bin", "javaw.exe"),
            os.path.join(game_dir, "java", "bin", "javaw.exe"),
        ):
            for match in glob.glob(pattern, recursive=True):
                add(match)

    if os.name == "nt":
        patterns = [
            r"C:\Program Files\Java\*\bin\javaw.exe",
            r"C:\Program Files\Eclipse Adoptium\*\bin\javaw.exe",
            r"C:\Program Files\Eclipse Foundation\*\bin\javaw.exe",
            r"C:\Program Files\AdoptOpenJDK\*\bin\javaw.exe",
            r"C:\Program Files\Zulu\*\bin\javaw.exe",
            r"C:\Program Files\Microsoft\jdk*\bin\javaw.exe",
            r"C:\Program Files\Amazon Corretto\*\bin\javaw.exe",
            r"C:\Program Files\BellSoft\*\bin\javaw.exe",
            r"C:\Program Files\Semeru\*\bin\javaw.exe",
            r"C:\Program Files\GraalVM\*\bin\javaw.exe",
            r"C:\Program Files\JetBrains\*\jbr\bin\javaw.exe",
            r"C:\Program Files\Android\Android Studio\jbr\bin\javaw.exe",
            r"C:\Program Files (x86)\Java\*\bin\javaw.exe",
            r"C:\Program Files (x86)\Minecraft Launcher\runtime\**\bin\javaw.exe",
            r"%APPDATA%\.minecraft\runtime\**\bin\javaw.exe",
            r"%APPDATA%\.minecraft\jre\*\bin\javaw.exe",
            r"%APPDATA%\.minecraft\java\*\bin\javaw.exe",
            r"%APPDATA%\.tlauncher\**\bin\javaw.exe",
            r"%APPDATA%\.legacylauncher\**\bin\javaw.exe",
            r"%APPDATA%\legacylauncher\**\bin\javaw.exe",
            r"%LOCALAPPDATA%\Programs\**\jbr\bin\javaw.exe",
        ]
        for pattern in patterns:
            try:
                matches = sorted(glob.glob(os.path.expandvars(pattern), recursive=True), reverse=True)
            except Exception:
                matches = []
            for match in matches:
                add(match)

    for name in ("javaw.exe", "java.exe"):
        try:
            add(shutil.which(name))
        except Exception:
            pass

    return candidates


def _pick_best_java(java_exe=None, game_dir=None, log_cb=None):
    """Обирає 64-бітну Java 21+, інакше будь-яку 64-бітну (з попередженням)."""
    best = None       # (score, path, major, is64)
    fallback64 = None
    for candidate in _java_candidates(java_exe, game_dir):
        if not os.path.isfile(candidate):
            continue
        major, is64 = _probe_java(candidate)
        if not major:
            continue
        # Пріоритет: Java 21 (цільова для MC 1.21.x), далі найближчі новіші,
        # потім старіші 64-бітні.
        if is64 and major == MIN_JAVA_MAJOR:
            score = 10000
        elif is64 and major > MIN_JAVA_MAJOR:
            score = 5000 - (major - MIN_JAVA_MAJOR)
        elif is64:
            score = major
        else:
            score = 0
        if is64 and major >= MIN_JAVA_MAJOR:
            if best is None or score > best[0]:
                best = (score, candidate, major, is64)
        elif is64 and major >= 17:
            if fallback64 is None or score > fallback64[0]:
                fallback64 = (score, candidate, major, is64)
        if len(_JAVA_PROBE_CACHE) > 40:
            break

    chosen = best or fallback64
    if not chosen:
        return None

    score, path, major, is64 = chosen
    if log_cb:
        log_cb(f"[*] Java: {path} (v{major}, {'64-bit' if is64 else '32-bit'})")
        if major < MIN_JAVA_MAJOR:
            log_cb(f"[!] Знайдено Java {major}, а для Minecraft {MC_VERSION} "
                   f"потрібна Java {MIN_JAVA_MAJOR}+. Буде завантажено сумісну JRE.")
            return None
    return path


def ensure_portable_java(log):
    """Завантажує портативну JRE 21 x64 (Temurin), якщо на ПК немає придатної Java."""
    target = _portable_java_dir()
    java_exe = os.path.join(target, "bin", "javaw.exe")
    if os.path.isfile(java_exe):
        return java_exe
    if os.name != "nt":
        return None

    log("[*] Придатної Java 21 (64-bit) не знайдено — завантажую автоматично...")
    parent = os.path.dirname(target)
    try:
        os.makedirs(parent, exist_ok=True)
    except Exception as exc:
        log(f"[!] Не вдалося створити папку для Java: {exc}")
        return None

    zip_path = target + ".zip"
    temp_dir = target + ".tmp"

    def cleanup():
        for path in (zip_path,):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        shutil.rmtree(temp_dir, ignore_errors=True)

    cleanup()
    try:
        req = urllib.request.Request(ADOPTIUM_JRE_URL, headers={"User-Agent": "LunarixLauncher/1.0"})
        with urllib.request.urlopen(req, timeout=180) as resp, open(zip_path, "wb") as out:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            last_pct = -10
            while True:
                chunk = resp.read(262144)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    if pct >= last_pct + 10:
                        last_pct = pct
                        log(f"[*] Завантаження Java: {pct}%")
        log("[*] Розпакування Java...")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(temp_dir)

        jre_root = None
        for root, dirs, files in os.walk(temp_dir):
            if os.path.basename(root).lower() == "bin" and "javaw.exe" in files:
                jre_root = os.path.dirname(root)
                break
        if not jre_root:
            raise RuntimeError("в архіві JRE немає bin\\javaw.exe")

        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(jre_root, target, dirs_exist_ok=True)
        _JAVA_PROBE_CACHE.pop(java_exe, None)
        if os.path.isfile(java_exe):
            log(f"[✓] Java 21 встановлено: {target}")
            return java_exe
        raise RuntimeError("після розпакування не знайдено javaw.exe")
    except Exception as exc:
        log(f"[!] Не вдалося автоматично завантажити Java: {exc}")
        log("[!] Встановіть Java 21 (64-bit) вручну: https://adoptium.net/temurin/releases/")
        return None
    finally:
        cleanup()


def _total_ram_gb():
    if os.name != "nt":
        return 0.0
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(stat)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return stat.ullTotalPhys / (1024 ** 3)
    except Exception:
        pass
    return 0.0


def get_classpath_entries(game_dir, log_cb=None):
    """Отримує всі шляхи бібліотек та ядра клієнта для -cp аргументу Java."""
    appdata_mc = os.path.join(os.environ.get("APPDATA", ""), ".minecraft")
    lib_dir = os.path.join(appdata_mc, "libraries")
    version_json_path = os.path.join(game_dir, "versions", VERSION_NAME, f"{VERSION_NAME}.json")
    if not os.path.exists(version_json_path):
        version_json_path = os.path.join(appdata_mc, "versions", f"Fabric {MC_VERSION}", f"Fabric {MC_VERSION}.json")

    cp_entries = []
    missing = []
    try:
        from core.libraries import _is_legacy_lib
    except Exception:
        def _is_legacy_lib(group):
            return False
    if os.path.exists(version_json_path):
        try:
            with open(version_json_path, "rb") as f:
                raw_bytes = f.read()
            if raw_bytes.startswith(b'\xef\xbb\xbf'):
                raw_bytes = raw_bytes[3:]
            v_data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
            for lib in v_data.get("libraries", []):
                if not isinstance(lib, dict):
                    continue
                name = lib.get("name", "")
                parts = name.split(":")
                if len(parts) < 3:
                    continue
                if _is_legacy_lib(parts[0]):
                    # локальний шім Legacy/TLauncher — не потрібен і не існує в Maven
                    continue
                group = parts[0].replace(".", os.sep)
                artifact, version = parts[1], parts[2]
                classifier = parts[3] if len(parts) > 3 else None
                # natives класифікатори йдуть у -Djava.library.path, не в classpath
                if classifier and "natives-" in classifier:
                    continue

                full_p = None
                downloads = lib.get("downloads")
                artifact_info = downloads.get("artifact") if isinstance(downloads, dict) else None
                if isinstance(artifact_info, dict) and artifact_info.get("path"):
                    full_p = os.path.join(lib_dir, artifact_info["path"].replace("/", os.sep))
                if not full_p:
                    jar_name = f"{artifact}-{version}" + (f"-{classifier}" if classifier else "") + ".jar"
                    full_p = os.path.join(lib_dir, group, artifact, version, jar_name)

                if os.path.exists(full_p) and os.path.getsize(full_p) > 0:
                    cp_entries.append(full_p)
                else:
                    missing.append(full_p)
        except Exception as e:
            print(f"Warning reading version json: {e}")

    if missing and log_cb:
        log_cb(f"[!] У classpath бракує {len(missing)} бібліотек(и), напр.: "
               f"{os.path.basename(missing[0])}")

    client_jar = os.path.join(game_dir, "versions", VERSION_NAME, f"{VERSION_NAME}.jar")
    if os.path.exists(client_jar):
        cp_entries.append(client_jar)
    else:
        mc_jar = os.path.join(appdata_mc, "versions", f"Fabric {MC_VERSION}", f"Fabric {MC_VERSION}.jar")
        if os.path.exists(mc_jar):
            cp_entries.append(mc_jar)

    return ";".join(cp_entries)

def launch_minecraft(cfg, log_cb=None, on_exit_cb=None, on_start_cb=None):
    """Запускає Minecraft 1.21.11 з клієнтом Lunarix та всіма модами."""
    def log(msg):
        if log_cb:
            log_cb(msg)
        print(msg)

    game_dir = (cfg.get("game_dir") or "").strip()
    if not game_dir:
        log("[-] Не вказано папку гри (game_dir). Відкрийте налаштування та виберіть теку клієнта.")
        return False
    try:
        os.makedirs(game_dir, exist_ok=True)
    except Exception as e:
        log(f"[-] Не вдалося створити/відкрити папку гри '{game_dir}': {e}")
        return False

    requested_java = str(cfg.get("java_path") or "").strip()
    java_exe = _pick_best_java(requested_java, game_dir=game_dir, log_cb=log)
    if not java_exe:
        java_exe = ensure_portable_java(log)
    if not java_exe:
        log("[-] Java 21 (64-bit) не знайдено і не вдалося завантажити автоматично.")
        log("[-] Встановіть Java 21 вручну: https://adoptium.net/temurin/releases/")
        return False
    if requested_java and os.path.normcase(os.path.abspath(requested_java)) != os.path.normcase(os.path.abspath(java_exe)):
        log(f"[*] Використовую Java: {java_exe}")
    cfg["java_path"] = java_exe

    try:
        ram_gb = max(1, int(cfg.get("ram_gb", 4)))
    except Exception:
        ram_gb = 4

    total_ram = _total_ram_gb()
    if total_ram:
        safe_max = max(2, int(total_ram - 1.5))
        if ram_gb > safe_max:
            log(f"[!] {ram_gb} GB RAM завелико для цього ПК ({total_ram:.1f} GB) — "
                f"встановлю {safe_max} GB")
            ram_gb = safe_max
    # The account username stays the in-game nickname; the display name is a
    # separate, editable label shown in the launcher and cosmetics HUD.
    username = (cfg.get("username") or "Player").strip() or "Player"
    jvm_extra = cfg.get("jvm_args", "").strip()

    try:
        from core.profile import export_profile, display_name
        export_profile(cfg)
        display_name_value = display_name(cfg)
    except Exception as exc:
        print(f"Warning: could not export launcher profile: {exc}")
        display_name_value = username

    avatar_file = ""
    try:
        from core.profile import avatar_path
        avatar_file = avatar_path(cfg) or ""
    except Exception:
        pass

    appdata_mc = os.path.join(os.environ.get("APPDATA", ""), ".minecraft")
    assets_dir = os.path.join(appdata_mc, "assets")

    natives_dir = os.path.join(game_dir, "versions", VERSION_NAME, "natives")
    if not os.path.exists(natives_dir):
        natives_dir = os.path.join(appdata_mc, "versions", f"Fabric {MC_VERSION}", "natives")
    try:
        os.makedirs(natives_dir, exist_ok=True)
        for sub in ("lwjgl", "jna", "netty"):
            os.makedirs(os.path.join(natives_dir, sub), exist_ok=True)
    except Exception as e:
        log(f"[!] Не вдалося створити папку natives '{natives_dir}': {e}")

    # Flatten DLLs into root natives directory if not already done
    if os.path.exists(natives_dir):
        for root, dirs, files in os.walk(natives_dir):
            if root == natives_dir:
                continue
            for f in files:
                if f.endswith(".dll"):
                    dst = os.path.join(natives_dir, f)
                    if not os.path.exists(dst):
                        try:
                            shutil.copy2(os.path.join(root, f), dst)
                        except Exception:
                            pass

    natives_paths = [natives_dir, os.path.join(natives_dir, "lwjgl"), os.path.join(natives_dir, "jna")]
    nat_str = ";".join([p for p in natives_paths if os.path.exists(p)])

    # Гарантуємо, що всі бібліотеки (fabric-loader, sponge-mixin, lwjgl тощо)
    # присутні в .minecraft/libraries — інакше KnotClient падає з
    # NoClassDefFoundError: org/spongepowered/asm/launch/MixinBootstrap
    try:
        from core.libraries import ensure_libraries
        vjson_path = os.path.join(game_dir, "versions", VERSION_NAME, f"{VERSION_NAME}.json")
        if not os.path.exists(vjson_path):
            vjson_path = os.path.join(appdata_mc, "versions", f"Fabric {MC_VERSION}", f"Fabric {MC_VERSION}.json")
        ensure_libraries(vjson_path, natives_dir=natives_dir, log_cb=log)
    except Exception as e:
        log(f"[!] Перевірка бібліотек: {e}")

    cp_string = get_classpath_entries(game_dir, log_cb=log)
    if not cp_string:
        log("[-] Не знайдено жодної бібліотеки для classpath. Перевстановіть клієнт.")
        return False

    cmd = [
        java_exe,
        f"-Xmx{ram_gb}G",
        f"-Xms{min(ram_gb, 2)}G",
        "-Xss1M",
        "--enable-native-access=ALL-UNNAMED",
        f"-Djava.library.path={nat_str}",
        f"-Dorg.lwjgl.librarypath={nat_str}",
        f"-Djna.tmpdir={os.path.join(natives_dir, 'jna')}",
        f"-Dorg.lwjgl.system.SharedLibraryExtractPath={os.path.join(natives_dir, 'lwjgl')}",
        f"-Dio.netty.native.workdir={os.path.join(natives_dir, 'netty')}",
        "-Dminecraft.launcher.brand=lunarix",
        "-Dminecraft.launcher.version=1.0.0",
        f"-Dlunarix.username={username}",
        f"-Dlunarix.displayName={display_name_value}",
        f"-Dlunarix.avatar={avatar_file}",
        f"-Dlunarix.profile={os.path.join(game_dir or '', 'lunarix', 'profile')}",
        f"-Dlunarix.shareCosmetics={'true' if cfg.get('share_cosmetics', True) else 'false'}",
        f"-Dlunarix.seeOtherCosmetics={'true' if cfg.get('see_other_cosmetics', True) else 'false'}",
        "-DFabricMcEmu= net.minecraft.client.main.Main ",
        "-Dfile.encoding=UTF-8",
        "-Dstdout.encoding=UTF-8",
        "-Dstderr.encoding=UTF-8",
    ]

    if jvm_extra:
        cmd.extend(jvm_extra.split())

    # Read assetIndex id dynamically from version json or fallback to 29 (for 1.21.11)
    asset_index_val = "29"
    version_json_path = os.path.join(game_dir, "versions", VERSION_NAME, f"{VERSION_NAME}.json")
    if os.path.exists(version_json_path):
        try:
            with open(version_json_path, "r", encoding="utf-8") as vj:
                vj_data = json.load(vj)
                ai = vj_data.get("assetIndex", {})
                if isinstance(ai, dict) and "id" in ai:
                    asset_index_val = str(ai["id"])
                elif "assets" in vj_data:
                    asset_index_val = str(vj_data["assets"])
        except Exception:
            pass

    cmd.extend([
        "-cp", cp_string,
        "net.fabricmc.loader.impl.launch.knot.KnotClient",
        "--username", username,
        "--version", VERSION_NAME,
        "--gameDir", game_dir,
        "--assetsDir", assets_dir,
        "--assetIndex", asset_index_val,
        "--uuid", "00000000-0000-0000-0000-000000000000",
        "--accessToken", "0",
        "--versionType", "release",
        "--width", str(cfg.get("width", 1280)),
        "--height", str(cfg.get("height", 720))
    ])

    if cfg.get("fullscreen"):
        cmd.append("--fullscreen")

    log(f"[*] Запуск гри: {username} (RAM: {ram_gb} GB)")

    def run_proc():
        # Heartbeat thread for online presence
        game_active = True
        current_activity = {"status": "in_game", "activity": "У грі (Запуск)", "server": ""}

        def presence_heartbeat():
            while game_active:
                try:
                    from core.cloud_configs import update_player_presence
                    update_player_presence(
                        username=username,
                        status=current_activity["status"],
                        activity=current_activity["activity"],
                        server=current_activity["server"]
                    )
                except Exception:
                    pass
                # Send heartbeat every 45 seconds
                for _ in range(45):
                    if not game_active:
                        break
                    import time
                    time.sleep(1)

        hb_thread = threading.Thread(target=presence_heartbeat, daemon=True)
        hb_thread.start()

        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.Popen(
                cmd,
                cwd=game_dir,
                startupinfo=startupinfo
            )
            log(f"[✓] Процес запущено (PID: {proc.pid})")
            if on_start_cb:
                try:
                    on_start_cb(proc)
                except TypeError:
                    on_start_cb()
            proc.wait()
            log(f"[*] Гра завершилась з кодом {proc.returncode}")
        except FileNotFoundError:
            log(f"[-] Не знайдено файл для запуску: {java_exe}. Перевірте шлях до Java у налаштуваннях.")
        except PermissionError:
            log(f"[-] Немає дозволу на запуск: {java_exe}. Спробуйте запустити лаунчер від імені адміністратора.")
        except Exception as e:
            log(f"[-] Помилка під час запуску: {e}")
        finally:
            game_active = False
            try:
                from core.cloud_configs import update_player_presence
                update_player_presence(username=username, status="online", activity="У лаунчері", server="")
            except Exception:
                pass
            if on_exit_cb:
                on_exit_cb()

    t = threading.Thread(target=run_proc, daemon=True)
    t.start()
    return True
