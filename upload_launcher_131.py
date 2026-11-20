import os
import sys
import json
import time
import hashlib
import base64
import urllib.request

TOKEN = ""
OWNER = "SoSohik"
REPO = "lunarix-client"
RELEASE_ID = 445467632
VERSION = "1.3.1"
EXE_PATH = "Lunarix Launcher.exe"
UPLOAD_NAME = "Lunarix.Launcher.exe"
COMMIT_MSG = f"Update launcher to v{VERSION} (fix self-update: replace exe without .bat/cmd)"

headers = {
    "User-Agent": "LunarixLauncher/1.0",
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

if not os.path.exists(EXE_PATH):
    print(f"Error: {EXE_PATH} not found!")
    sys.exit(1)

file_size = os.path.getsize(EXE_PATH)
with open(EXE_PATH, "rb") as f:
    raw_data = f.read()
file_sha1 = hashlib.sha1(raw_data).hexdigest()

print(f"File: {EXE_PATH}  Size: {file_size}  SHA1: {file_sha1}")

assets_url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/{RELEASE_ID}/assets"
req = urllib.request.Request(assets_url, headers=headers)
with urllib.request.urlopen(req) as resp:
    assets = json.loads(resp.read().decode("utf-8"))

for a in assets:
    if a.get("name") in (UPLOAD_NAME, "Lunarix Launcher.exe"):
        a_id = a.get("id")
        print(f"Deleting old asset: {a.get('name')} (ID: {a_id}) ...")
        del_req = urllib.request.Request(
            f"https://api.github.com/repos/{OWNER}/{REPO}/releases/assets/{a_id}",
            headers=headers, method="DELETE",
        )
        try:
            with urllib.request.urlopen(del_req):
                print("  Deleted.")
        except Exception as e:
            print("  Failed:", e)
        time.sleep(1)

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
with urllib.request.urlopen(up_req, timeout=1800) as up_resp:
    new_asset = json.loads(up_resp.read().decode("utf-8"))

new_asset_url = new_asset.get("url")
print(f"SUCCESS: asset ID {new_asset.get('id')} size {new_asset.get('size')} -> {new_asset_url}")

# Update manifest.json on main
manifest_url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/manifest.json"
req_m = urllib.request.Request(manifest_url, headers=headers)
with urllib.request.urlopen(req_m) as resp_m:
    m_info = json.loads(resp_m.read().decode("utf-8"))
    m_sha = m_info.get("sha")
    manifest = json.loads(base64.b64decode(m_info.get("content")).decode("utf-8"))

manifest["launcher"] = {
    "version": VERSION,
    "filename": UPLOAD_NAME,
    "url": new_asset_url,
    "sha1": file_sha1,
    "size": file_size,
}

payload = json.dumps({
    "message": COMMIT_MSG,
    "content": base64.b64encode(json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")).decode("utf-8"),
    "sha": m_sha,
}).encode("utf-8")

commit_headers = dict(headers)
commit_headers["Content-Type"] = "application/json"
commit_req = urllib.request.Request(manifest_url, data=payload, headers=commit_headers, method="PUT")
with urllib.request.urlopen(commit_req) as c_resp:
    res = json.loads(c_resp.read().decode("utf-8"))
    print("SUCCESS: manifest.json updated, commit:", res.get("commit", {}).get("sha"))

print("ALL DONE!")
