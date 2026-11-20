import os
import json
import urllib.request
import urllib.parse
from PIL import Image
import io

USER_AGENT = "LunarixLauncher/1.0 (contact@lunarix.client)"

from core.config import get_thumbs_cache_dir

THUMBS_DIR = get_thumbs_cache_dir()

def search_modrinth_mods(query="", limit=8, offset=0, game_version="1.21.11"):
    """Шукає моди для Fabric 1.21.11 з підтримкою пагінації (offset/limit)."""
    try:
        q = urllib.parse.quote(query.strip()) if query.strip() else ""
        url = (
            f"https://api.modrinth.com/v2/search?query={q}"
            f"&facets=[[%22categories:fabric%22],[%22versions:{game_version}%22],[%22project_type:mod%22]]"
            f"&limit={limit}&offset={offset}&index=downloads"
        )
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8-sig"))
            return data.get("hits", []), data.get("total_hits", 0)
    except Exception as e:
        print(f"Modrinth search error: {e}")
        return [], 0

def search_modrinth_resourcepacks(query="", limit=8, offset=0):
    """Шукає ресурспаки на Modrinth з підтримкою пагінації."""
    try:
        q = urllib.parse.quote(query.strip()) if query.strip() else ""
        url = (
            f"https://api.modrinth.com/v2/search?query={q}"
            f"&facets=[[%22project_type:resourcepack%22]]"
            f"&limit={limit}&offset={offset}&index=downloads"
        )
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8-sig"))
            return data.get("hits", []), data.get("total_hits", 0)
    except Exception as e:
        print(f"Modrinth RP search error: {e}")
        return [], 0

def load_mod_icon_pil(icon_url, size=(44, 44)):
    """Завантажує та кешує іконку проекту як об'єкт PIL Image."""
    if not icon_url:
        return None
    try:
        url_hash = str(abs(hash(icon_url)))
        ext = ".webp" if ".webp" in icon_url.lower() else ".png"
        local_thumb = os.path.join(THUMBS_DIR, f"{url_hash}{ext}")

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

def get_mod_download_info(project_id_or_slug, game_version="1.21.11"):
    """Отримує посилання на завантаження файлу моду для Fabric 1.21.11."""
    try:
        slug = urllib.parse.quote(project_id_or_slug)
        url = f"https://api.modrinth.com/v2/project/{slug}/version?game_versions=[%22{game_version}%22]&loaders=[%22fabric%22]"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            versions = json.loads(resp.read().decode("utf-8-sig"))
            if versions and len(versions) > 0:
                files = versions[0].get("files", [])
                for f in files:
                    if f.get("filename", "").endswith(".jar"):
                        return {
                            "filename": f.get("filename"),
                            "url": f.get("url"),
                            "size": f.get("size"),
                            "sha1": f.get("hashes", {}).get("sha1")
                        }
    except Exception as e:
        print(f"Modrinth version error: {e}")
    return None

def get_resourcepack_download_info(project_id_or_slug):
    """Отримує файл для ресурспаку з Modrinth."""
    try:
        slug = urllib.parse.quote(project_id_or_slug)
        url = f"https://api.modrinth.com/v2/project/{slug}/version"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            versions = json.loads(resp.read().decode("utf-8-sig"))
            if versions and len(versions) > 0:
                files = versions[0].get("files", [])
                for f in files:
                    fname = f.get("filename", "")
                    if fname.endswith(".zip") or fname.endswith(".jar"):
                        return {
                            "filename": fname,
                            "url": f.get("url"),
                            "size": f.get("size"),
                            "sha1": f.get("hashes", {}).get("sha1")
                        }
                if files:
                    return {
                        "filename": files[0].get("filename", "pack.zip"),
                        "url": files[0].get("url"),
                        "size": files[0].get("size")
                    }
    except Exception as e:
        print(f"Modrinth RP download info error: {e}")
    return None

def install_mod_from_modrinth(project_id_or_slug, mods_dir, progress_cb=None, game_version="1.21.11"):
    """Завантажує та встановлює мод з Modrinth прямо у папку mods/."""
    os.makedirs(mods_dir, exist_ok=True)
    info = get_mod_download_info(project_id_or_slug, game_version=game_version)
    if not info:
        return False, f"Не знайдено файлу для Fabric {game_version}"

    target_path = os.path.join(mods_dir, info["filename"])
    temp_path = target_path + ".download"

    req = urllib.request.Request(info["url"], headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp, open(temp_path, "wb") as out_file:
            total_size = int(resp.headers.get("Content-Length", info.get("size", 0)))
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
                    progress_cb(pct, f"Завантаження {info['filename']}: {int(pct*100)}%")

        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(temp_path, target_path)
        return True, info["filename"]
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, str(e)

def install_resourcepack_from_modrinth(project_id_or_slug, rp_dir, progress_cb=None):
    """Завантажує та встановлює ресурспак з Modrinth прямо у resourcepacks/."""
    os.makedirs(rp_dir, exist_ok=True)
    info = get_resourcepack_download_info(project_id_or_slug)
    if not info:
        return False, "Не знайдено файлу ресурспаку на Modrinth"

    target_path = os.path.join(rp_dir, info["filename"])
    temp_path = target_path + ".download"

    req = urllib.request.Request(info["url"], headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp, open(temp_path, "wb") as out_file:
            total_size = int(resp.headers.get("Content-Length", info.get("size", 0)))
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
                    progress_cb(pct, f"Завантаження {info['filename']}: {int(pct*100)}%")

        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(temp_path, target_path)
        return True, info["filename"]
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, str(e)
