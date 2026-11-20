# -*- coding: utf-8 -*-
"""Оновлює Lunarix-Client-v1.2.1.jar у ТОМУ Ж релізі v1.0.0 + manifest.json."""
import os, sys, json, time, hashlib, base64, urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "")
OWNER = "SoSohik"
REPO = "lunarix-client"
RELEASE_ID = 445467632
EXE_PATH = r"C:\Users\Адмін\OneDrive\Desktop\lunarix client\mods\Lunarix-Client-v1.2.1.jar"
UPLOAD_NAME = "Lunarix-Client-v1.2.1.jar"

headers = {
    "User-Agent": "LunarixLauncher/1.0",
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

file_size = os.path.getsize(EXE_PATH)
raw_data = open(EXE_PATH, "rb").read()
file_sha1 = hashlib.sha1(raw_data).hexdigest()
print(f"File: {EXE_PATH}\nSize: {file_size}  SHA1: {file_sha1}")

# 1. Видаляємо старий jar-асет
assets_url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/{RELEASE_ID}/assets"
req = urllib.request.Request(assets_url, headers=headers)
with urllib.request.urlopen(req, timeout=60) as resp:
    assets = json.loads(resp.read().decode("utf-8"))

for a in assets:
    if a.get("name") == UPLOAD_NAME:
        a_id = a.get("id")
        print(f"Deleting old asset: {a.get('name')} (ID: {a_id}) ...")
        del_req = urllib.request.Request(
            f"https://api.github.com/repos/{OWNER}/{REPO}/releases/assets/{a_id}",
            headers=headers, method="DELETE",
        )
        try:
            with urllib.request.urlopen(del_req, timeout=60):
                print("  Deleted.")
        except Exception as e:
            print("  Failed:", e)
        time.sleep(1)

# 2. Завантажуємо новий jar
upload_url = (
    f"https://uploads.github.com/repos/{OWNER}/{REPO}"
    f"/releases/{RELEASE_ID}/assets?name={UPLOAD_NAME}"
)
print(f"Uploading {UPLOAD_NAME} ({file_size} bytes)...")
upload_headers = {
    "User-Agent": "LunarixLauncher/1.0",
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/octet-stream",
    "Content-Length": str(file_size),
}
up_req = urllib.request.Request(upload_url, data=raw_data, headers=upload_headers, method="POST")
with urllib.request.urlopen(up_req, timeout=3600) as up_resp:
    new_asset = json.loads(up_resp.read().decode("utf-8"))

new_asset_url = new_asset.get("url")
print(f"SUCCESS: asset ID {new_asset.get('id')} size {new_asset.get('size')} -> {new_asset_url}")

# 3. Оновлюємо manifest.json: size + sha1 (+ url на новий asset)
manifest_url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/manifest.json"
req_m = urllib.request.Request(manifest_url, headers=headers)
with urllib.request.urlopen(req_m, timeout=60) as resp_m:
    m_info = json.loads(resp_m.read().decode("utf-8"))
    m_sha = m_info.get("sha")
    manifest = json.loads(base64.b64decode(m_info.get("content")).decode("utf-8"))

for item in manifest.get("files", []):
    if item.get("path") == f"mods/{UPLOAD_NAME}":
        item["size"] = file_size
        item["sha1"] = file_sha1
        item["url"] = f"https://github.com/{OWNER}/{REPO}/releases/download/v1.0.0/{UPLOAD_NAME}"

payload = json.dumps({
    "message": "Update Lunarix-Client jar (resource pack bypass)",
    "content": base64.b64encode(
        json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
    ).decode("utf-8"),
    "sha": m_sha,
}).encode("utf-8")

commit_headers = dict(headers)
commit_headers["Content-Type"] = "application/json"
commit_req = urllib.request.Request(manifest_url, data=payload, headers=commit_headers, method="PUT")
with urllib.request.urlopen(commit_req, timeout=60) as c_resp:
    res = json.loads(c_resp.read().decode("utf-8"))
    print("SUCCESS: manifest.json updated, commit:", res.get("commit", {}).get("sha"))

print("ALL DONE!")
