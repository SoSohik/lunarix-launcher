import os
import sys
import json
import time
import hashlib
import base64
import urllib.request
import urllib.error

TOKEN = ""
OWNER = "SoSohik"
REPO = "lunarix-client"
RELEASE_ID = 445467632
EXE_PATH = "Lunarix Launcher.exe"

headers = {
    "User-Agent": "LunarixLauncher/1.0",
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

if not os.path.exists(EXE_PATH):
    print(f"Error: {EXE_PATH} not found!")
    sys.exit(1)

file_size = os.path.getsize(EXE_PATH)
with open(EXE_PATH, "rb") as f:
    raw_data = f.read()
file_sha1 = hashlib.sha1(raw_data).hexdigest()

print(f"File: {EXE_PATH}")
print(f"Size: {file_size} bytes")
print(f"SHA1: {file_sha1}")

# 1. Check existing assets in release
assets_url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/{RELEASE_ID}/assets"
req = urllib.request.Request(assets_url, headers=headers)
with urllib.request.urlopen(req) as resp:
    assets = json.loads(resp.read().decode("utf-8"))

for a in assets:
    if a.get("name") in ("Lunarix.Launcher.exe", "Lunarix Launcher.exe"):
        a_id = a.get("id")
        print(f"Deleting old asset: {a.get('name')} (ID: {a_id}) ...")
        del_url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/assets/{a_id}"
        del_req = urllib.request.Request(del_url, headers=headers, method="DELETE")
        try:
            with urllib.request.urlopen(del_req) as del_resp:
                print("  Deleted successfully.")
        except Exception as e:
            print("  Failed to delete:", e)
        time.sleep(1)

# 2. Upload new asset
upload_name = "Lunarix.Launcher.exe"
upload_url = f"https://uploads.github.com/repos/{OWNER}/{REPO}/releases/{RELEASE_ID}/assets?name={upload_name}"
print(f"Uploading new asset {upload_name} ({file_size} bytes) to GitHub release {RELEASE_ID}...")

upload_headers = {
    "User-Agent": "LunarixLauncher/1.0",
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/octet-stream",
    "Content-Length": str(file_size)
}

upload_req = urllib.request.Request(upload_url, data=raw_data, headers=upload_headers, method="POST")
with urllib.request.urlopen(upload_req) as up_resp:
    new_asset = json.loads(up_resp.read().decode("utf-8"))

new_asset_id = new_asset.get("id")
new_asset_url = new_asset.get("url")
print(f"SUCCESS: Uploaded asset ID {new_asset_id}!")
print(f"Asset URL: {new_asset_url}")

# 3. Update manifest.json on main branch
manifest_url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/manifest.json"
req_m = urllib.request.Request(manifest_url, headers=headers)
with urllib.request.urlopen(req_m) as resp_m:
    m_info = json.loads(resp_m.read().decode("utf-8"))
    m_sha = m_info.get("sha")
    m_content_str = base64.b64decode(m_info.get("content")).decode("utf-8")
    manifest = json.loads(m_content_str)

manifest["launcher"] = {
    "version": "1.2.2",
    "filename": upload_name,
    "url": new_asset_url,
    "sha1": file_sha1,
    "size": file_size
}

new_m_json = json.dumps(manifest, indent=2, ensure_ascii=False)
commit_payload = json.dumps({
    "message": "Update launcher to v1.2.2 (Remove incompatible JVM flag, fix Java 21 support)",
    "content": base64.b64encode(new_m_json.encode("utf-8")).decode("utf-8"),
    "sha": m_sha
}).encode("utf-8")

commit_headers = dict(headers)
commit_headers["Content-Type"] = "application/json"

print("Updating manifest.json on GitHub repository...")
commit_req = urllib.request.Request(manifest_url, data=commit_payload, headers=commit_headers, method="PUT")
with urllib.request.urlopen(commit_req) as c_resp:
    res = json.loads(c_resp.read().decode("utf-8"))
    print("SUCCESS: manifest.json updated on GitHub!")
    print("Commit SHA:", res.get("commit", {}).get("sha"))

print("\nALL DONE! Launcher v1.2.2 is uploaded and manifest is live.")
