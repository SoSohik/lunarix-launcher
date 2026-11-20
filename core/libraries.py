import os
import sys
import json
import zipfile
import hashlib
import urllib.request
import urllib.error

MAVEN_REPOS = [
    "https://maven.fabricmc.net/",
    "https://repo.spongepowered.org/maven/",
    "https://libraries.minecraft.net/",
    "https://repo1.maven.org/maven2/",
]

USER_AGENT = "LunarixLauncher/1.0"

# Ці бібліотеки додають сторонні лаунчери (Legacy Launcher / TLauncher) у
# version json. У публічних Maven-репозиторіях їх немає (звідси HTTP 404), і
# грі вони не потрібні — це локальні шіми лаунчера.
SKIP_GROUPS = ("ru.legacylauncher", "ru.tlauncher", "ru.tln4")


def _current_os_names():
    p = sys.platform
    if p.startswith("win"):
        return {"windows"}
    if p == "darwin":
        return {"osx"}
    return {"linux"}


def _rules_allow(rules):
    """Відтворює оцінку rules з version json для поточної ОС."""
    if not rules:
        return True
    allowed = True
    os_names = _current_os_names()
    for rule in rules:
        os_rule = rule.get("os") or {}
        name = os_rule.get("name")
        if name and name not in os_names:
            continue
        allowed = rule.get("action") == "allow"
    return allowed


def _skip_classifier(classifier):
    """Пропускає natives під іншу архітектуру, щоб не тягнути зайве."""
    if not classifier:
        return False
    machine = os.environ.get("PROCESSOR_ARCHITEW6432") or os.environ.get("PROCESSOR_ARCHITECTURE", "")
    is_arm = "ARM64" in machine.upper() or "ARM" in machine.upper()
    is_64 = is_arm or "64" in machine
    cl = classifier.lower()
    if "arm64" in cl and not is_arm:
        return True
    if cl.endswith("-x86") and is_64:
        return True
    if cl.endswith("-arm32") and is_64:
        return True
    return False


def _parse_coord(name):
    parts = name.split(":")
    if len(parts) < 3:
        return None
    group, artifact, version = parts[0], parts[1], parts[2]
    classifier = parts[3] if len(parts) > 3 else None
    ext = parts[4] if len(parts) > 4 else "jar"
    if ext != "jar":
        return None
    return group, artifact, version, classifier


def _lib_paths(group, artifact, version, classifier=None):
    lib_root = os.path.join(
        os.environ.get("APPDATA", ""), ".minecraft", "libraries"
    )
    group_path = os.path.join(lib_root, *group.split("."), artifact)
    base = f"{artifact}-{version}"
    if classifier:
        base += f"-{classifier}"
    return lib_root, group_path, os.path.join(group_path, version, base + ".jar")


def _is_legacy_lib(group):
    """True для бібліотек, які існують лише в локальному репо сторонніх лаунчерів."""
    group = (group or "").lower()
    return any(group == g or group.startswith(g + ".") for g in SKIP_GROUPS)


def _is_valid_jar(path):
    """Файл існує, не порожній і схожий на zip/jar (а не HTML-сторінку помилки)."""
    try:
        if not os.path.exists(path) or os.path.getsize(path) < 4:
            return False
        with open(path, "rb") as f:
            return f.read(2) == b"PK"
    except Exception:
        return False


def _sha1_of(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest().lower()


def _download(url, target, log_cb=None, expected_size=0, sha1=None):
    """Завантажує jar у target. Перевіряє розмір/контрольну суму/zip-заголовок."""
    os.makedirs(os.path.dirname(target), exist_ok=True)
    temp = target + ".download"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, open(temp, "wb") as out:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out.write(chunk)
        size = os.path.getsize(temp)
        if expected_size and size != int(expected_size):
            raise ValueError(f"розмір {size} != очікуваного {expected_size}")
        if sha1 and _sha1_of(temp) != str(sha1).lower():
            raise ValueError("невірна контрольна сума SHA1")
        if target.lower().endswith(".jar") and not _is_valid_jar(temp):
            raise ValueError("файл не є валідним jar")
        if os.path.exists(target):
            os.remove(target)
        os.rename(temp, target)
        return True
    except Exception as e:
        if os.path.exists(temp):
            try:
                os.remove(temp)
            except Exception:
                pass
        if log_cb:
            log_cb(f"[!] Не вдалося завантажити {os.path.basename(target)}: {e}")
        return False


def _fetch_lib(group, artifact, version, classifier, target_path, log_cb=None,
               repo_urls=None, expected_size=0, sha1=None):
    """Пробує завантажити jar з репозиторіїв самої бібліотеки, потім зі стандартних."""
    fname = f"{artifact}-{version}" + (f"-{classifier}" if classifier else "") + ".jar"
    repos = []
    for repo in list(repo_urls or []) + MAVEN_REPOS:
        if not repo or not isinstance(repo, str):
            continue
        repo = repo.strip().rstrip("/") + "/"
        if not repo.startswith(("http://", "https://")):
            continue
        if repo not in repos:
            repos.append(repo)

    rel = group.replace(".", "/") + f"/{artifact}/{version}/{fname}"
    for repo in repos:
        if _download(repo + rel, target_path, log_cb=None,
                     expected_size=expected_size, sha1=sha1):
            return True

    if log_cb:
        log_cb(f"[!] Не вдалося завантажити {fname}: немає в жодному репозиторії (404)")
    return False



def ensure_libraries(version_json_path, natives_dir=None, log_cb=None, progress_cb=None):
    """
    Перевіряє всі libraries з version json і докачує відсутні jar-файли
    в %APPDATA%/.minecraft/libraries. Також розпаковує natives-* jar
    у natives_dir. Повертає True, якщо критичні бібліотеки на місці.
    """
    def log(msg):
        if log_cb:
            log_cb(msg)
        print(msg)

    if not version_json_path or not os.path.exists(version_json_path):
        return False

    try:
        with open(version_json_path, "rb") as f:
            raw = f.read()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        vdata = json.loads(raw.decode("utf-8", errors="replace"))
    except Exception as e:
        log(f"[!] Помилка читання version json: {e}")
        return False

    libs = vdata.get("libraries", [])
    missing = []
    native_jars = []

    for lib in libs:
        name = lib.get("name") if isinstance(lib, dict) else None
        if not name:
            continue
        coord = _parse_coord(name)
        if not coord:
            continue
        group, artifact, version, classifier = coord
        if _is_legacy_lib(group):
            # Локальний шім стороннього лаунчера — у Maven його немає, грі не потрібен.
            continue
        if not _rules_allow(lib.get("rules")):
            continue
        if _skip_classifier(classifier):
            continue

        _, _, jar_path = _lib_paths(group, artifact, version, classifier)
        if _is_valid_jar(jar_path):
            if classifier and "natives-" in classifier:
                native_jars.append(jar_path)
            continue

        missing.append((lib, group, artifact, version, classifier, jar_path))
        if classifier and "natives-" in classifier:
            native_jars.append(jar_path)

    if not missing:
        _extract_natives(native_jars, natives_dir, log)
        return True

    total = len(missing)
    log(f"[*] Бібліотеки: потрібно завантажити {total} файлів...")
    failed = []
    for i, (lib, group, artifact, version, classifier, jar_path) in enumerate(missing):
        fname = f"{artifact}-{version}" + (f"-{classifier}" if classifier else "") + ".jar"
        if progress_cb:
            progress_cb(0.0, f"Бібліотеки: {fname} ({i + 1}/{total})")

        downloads = lib.get("downloads") if isinstance(lib, dict) else None
        artifact_info = downloads.get("artifact") if isinstance(downloads, dict) else None
        if not isinstance(artifact_info, dict):
            artifact_info = {}
        direct_url = artifact_info.get("url")
        sha1 = artifact_info.get("sha1")
        size = artifact_info.get("size") or 0

        repo_urls = []
        lib_url = lib.get("url") if isinstance(lib, dict) else None
        if isinstance(lib_url, str) and lib_url.startswith(("http://", "https://")):
            repo_urls.append(lib_url)

        ok = False
        if isinstance(direct_url, str) and direct_url.startswith(("http://", "https://")):
            ok = _download(direct_url, jar_path, log_cb=None,
                           expected_size=size, sha1=sha1)
        if not ok:
            ok = _fetch_lib(group, artifact, version, classifier, jar_path,
                            log_cb=log, repo_urls=repo_urls,
                            expected_size=size, sha1=sha1)

        if ok:
            log(f"[+] Завантажено: {fname}")
        else:
            failed.append(fname)
            log(f"[-] Не вдалося завантажити: {fname}")

    _extract_natives(native_jars, natives_dir, log)

    if failed:
        log(f"[!] Не вдалося завантажити {len(failed)} бібліотек(и): {', '.join(failed[:5])}")
        return False
    return True


def _extract_natives(jar_paths, natives_dir, log):
    """Розпаковує natives-*.jar у natives_dir (як це робить vanilla launcher)."""
    if not natives_dir:
        return
    os.makedirs(natives_dir, exist_ok=True)
    for jar in jar_paths:
        if not os.path.exists(jar):
            continue
        try:
            with zipfile.ZipFile(jar) as zf:
                for info in zf.infolist():
                    if info.is_dir() or info.filename.startswith("META-INF"):
                        continue
                    dest = os.path.join(natives_dir, info.filename.replace("/", os.sep))
                    if os.path.exists(dest) and os.path.getsize(dest) == info.file_size:
                        continue
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with zf.open(info) as src, open(dest, "wb") as out:
                        while True:
                            chunk = src.read(65536)
                            if not chunk:
                                break
                            out.write(chunk)
        except Exception as e:
            log(f"[!] Помилка розпакування natives {os.path.basename(jar)}: {e}")
