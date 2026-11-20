import os
import json
import urllib.request
import urllib.parse
from PIL import Image
import io

USER_AGENT = "LunarixLauncher/1.0 (contact@lunarix.client)"

# CurseForge Core Public API Key
CF_API_KEY = "$2a$10$bL4bIL5pUWqfcO7KQtnMReakwtfHbNKh6v1uTpKlzhwoueEJQnPnm"
CF_BASE_URL = "https://api.curseforge.com/v1"

from core.config import get_thumbs_cache_dir

THUMBS_DIR = get_thumbs_cache_dir()

def _make_cf_request(endpoint, params=None):
    """Виконує авторизований запит до CurseForge API."""
    try:
        url = f"{CF_BASE_URL}{endpoint}"
        if params:
            qs = urllib.parse.urlencode(params)
            url = f"{url}?{qs}"
        req = urllib.request.Request(
            url,
            headers={
                "x-api-key": CF_API_KEY,
                "Accept": "application/json",
                "User-Agent": USER_AGENT
            }
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8-sig"))
    except Exception as e:
        print(f"CurseForge request error ({endpoint}): {e}")
        return None

def search_curseforge_mods(query="", limit=8, offset=0, game_version=None):
    """
    Пошук модів на CurseForge (gameId=432, classId=6 - Mods).
    """
    params = {
        "gameId": 432,
        "classId": 6,
        "pageSize": limit,
        "index": offset,
        "sortField": 2, # Popularity / TotalDownloads
        "sortOrder": "desc"
    }
    if query.strip():
        params["searchFilter"] = query.strip()
    if game_version:
        params["gameVersion"] = game_version

    data = _make_cf_request("/mods/search", params)
    if not data:
        return [], 0
    mods = data.get("data", [])
    pagination = data.get("pagination", {})
    total = pagination.get("totalCount", len(mods))
    return mods, total

def search_curseforge_resourcepacks(query="", limit=8, offset=0):
    """
    Пошук ресурспаків на CurseForge (gameId=432, classId=12 - Texture Packs / Resource Packs).
    """
    params = {
        "gameId": 432,
        "classId": 12,
        "pageSize": limit,
        "index": offset,
        "sortField": 2,
        "sortOrder": "desc"
    }
    if query.strip():
        params["searchFilter"] = query.strip()

    data = _make_cf_request("/mods/search", params)
    if not data:
        return [], 0
    packs = data.get("data", [])
    pagination = data.get("pagination", {})
    total = pagination.get("totalCount", len(packs))
    return packs, total

def load_curseforge_icon_pil(icon_url, size=(44, 44)):
    """Завантажує та кешує іконку проекту CurseForge."""
    if not icon_url:
        return None
    try:
        url_hash = str(abs(hash(icon_url)))
        ext = ".png"
        if ".webp" in icon_url.lower():
            ext = ".webp"
        elif ".jpg" in icon_url.lower() or ".jpeg" in icon_url.lower():
            ext = ".jpg"
        local_thumb = os.path.join(THUMBS_DIR, f"cf_{url_hash}{ext}")

        if os.path.exists(local_thumb):
            img = Image.open(local_thumb)
            return img.resize(size, Image.Resampling.LANCZOS)

        req = urllib.request.Request(icon_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw_data = resp.read()
            with open(local_thumb, "wb") as f:
                f.write(raw_data)
            img = Image.open(io.BytesIO(raw_data))
            return img.resize(size, Image.Resampling.LANCZOS)
    except Exception:
        return None

def get_curseforge_best_file(mod_id, file_extension=None):
    """Отримує найкращий/останній файл для проекту з CurseForge."""
    data = _make_cf_request(f"/mods/{mod_id}/files", {"pageSize": 10})
    if not data or "data" not in data or not data["data"]:
        return None

    files = data["data"]
    # Шукаємо файл за потрібним розширенням, наприклад .jar або .zip
    for f in files:
        fname = f.get("fileName", "")
        durl = f.get("downloadUrl")
        if file_extension and not fname.lower().endswith(file_extension.lower()):
            continue
        if durl:
            return {
                "filename": fname,
                "url": durl,
                "size": f.get("fileLength", 0)
            }

    # Якщо прямий downloadUrl відсутній (Edge CDN), генеруємо за стандартною формулою CurseForge
    first = files[0]
    fid = first.get("id")
    fname = first.get("fileName", "file.bin")
    durl = first.get("downloadUrl")
    if not durl and fid:
        part1 = str(fid)[:4]
        part2 = str(fid)[4:]
        durl = f"https://edge.forgecdn.net/files/{part1}/{part2}/{urllib.parse.quote(fname)}"

    return {
        "filename": fname,
        "url": durl,
        "size": first.get("fileLength", 0)
    }

def install_file_from_curseforge(mod_id, target_dir, file_extension=None, progress_cb=None):
    """Завантажує та зберігає файл проекту CurseForge у вказану папку."""
    os.makedirs(target_dir, exist_ok=True)
    finfo = get_curseforge_best_file(mod_id, file_extension=file_extension)
    if not finfo or not finfo.get("url"):
        return False, "Не знайдено доступного файлу для завантаження на CurseForge"

    filename = finfo["filename"]
    target_path = os.path.join(target_dir, filename)
    temp_path = target_path + ".download"

    req = urllib.request.Request(
        finfo["url"],
        headers={
            "User-Agent": USER_AGENT,
            "x-api-key": CF_API_KEY
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp, open(temp_path, "wb") as out_file:
            total_size = int(resp.headers.get("Content-Length", finfo.get("size", 0)))
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
                    progress_cb(pct, f"Завантаження {filename}: {int(pct*100)}%")

        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(temp_path, target_path)
        return True, filename
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False, str(e)
