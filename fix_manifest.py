import json
import base64
import urllib.request

TOKEN = ""
OWNER = "SoSohik"
REPO = "lunarix-client"
VERSION = "1.2.3"
ASSET_URL = "https://api.github.com/repos/SoSohik/lunarix-client/releases/assets/752527124"
SHA1 = "a1b0c1b1ea739c848061d33954ec215e4e5a365b"
SIZE = 77873454

headers = {
    "User-Agent": "LunarixLauncher/1.0",
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

manifest_url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/manifest.json"
req_m = urllib.request.Request(manifest_url, headers=headers)
with urllib.request.urlopen(req_m) as resp_m:
    m_info = json.loads(resp_m.read().decode("utf-8"))
    m_sha = m_info.get("sha")
    raw = base64.b64decode(m_info.get("content"))
    manifest = json.loads(raw.decode("utf-8-sig"))

manifest["launcher"] = {
    "version": VERSION,
    "filename": "Lunarix.Launcher.exe",
    "url": ASSET_URL,
    "sha1": SHA1,
    "size": SIZE,
}

payload = json.dumps({
    "message": f"Update launcher to v{VERSION} (auto-download Minecraft/Fabric libraries)",
    "content": base64.b64encode(json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")).decode("utf-8"),
    "sha": m_sha,
}).encode("utf-8")

commit_headers = dict(headers)
commit_headers["Content-Type"] = "application/json"
commit_req = urllib.request.Request(manifest_url, data=payload, headers=commit_headers, method="PUT")
with urllib.request.urlopen(commit_req) as c_resp:
    res = json.loads(c_resp.read().decode("utf-8"))
    print("SUCCESS: manifest.json updated, commit:", res.get("commit", {}).get("sha"))
