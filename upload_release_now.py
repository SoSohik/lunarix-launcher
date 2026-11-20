import os, json, time, hashlib, base64, urllib.request

TOKEN = ''
OWNER = 'SoSohik'
REPO = 'lunarix-client'
RELEASE_ID = 445467632
EXE_PATH = 'Lunarix Launcher.exe'
UPLOAD_NAME = 'Lunarix.Launcher.exe'

headers = {
    'User-Agent': 'LunarixLauncher/1.0',
    'Authorization': 'Bearer ' + TOKEN,
    'Accept': 'application/vnd.github.v3+json',
}

raw = open(EXE_PATH, 'rb').read()
size = len(raw)
sha1 = hashlib.sha1(raw).hexdigest()
print('exe size', size, 'sha1', sha1)

# 1. delete old launcher asset(s)
assets_url = 'https://api.github.com/repos/%s/%s/releases/%s/assets' % (OWNER, REPO, RELEASE_ID)
assets = json.loads(urllib.request.urlopen(urllib.request.Request(assets_url, headers=headers)).read())
for a in assets:
    if a.get('name') in (UPLOAD_NAME, 'Lunarix Launcher.exe'):
        aid = a['id']
        print('deleting', a['name'], aid)
        del_req = urllib.request.Request(
            'https://api.github.com/repos/%s/%s/releases/assets/%s' % (OWNER, REPO, aid),
            headers=headers, method='DELETE')
        try:
            urllib.request.urlopen(del_req)
            print('  deleted')
        except Exception as e:
            print('  del fail', e)
        time.sleep(1)

# 2. upload new exe
up_url = ('https://uploads.github.com/repos/%s/%s/releases/%s/assets?name=%s'
          % (OWNER, REPO, RELEASE_ID, UPLOAD_NAME))
uh = dict(headers)
uh['Content-Type'] = 'application/octet-stream'
req = urllib.request.Request(up_url, data=raw, headers=uh, method='POST')
asset = json.loads(urllib.request.urlopen(req, timeout=1800).read())
asset_url = asset['url']
print('uploaded asset', asset['id'], asset['size'], asset_url)

# 3. update manifest.json on main
murl = 'https://api.github.com/repos/%s/%s/contents/manifest.json' % (OWNER, REPO)
minfo = json.loads(urllib.request.urlopen(urllib.request.Request(murl, headers=headers)).read())
m = json.loads(base64.b64decode(minfo['content']).decode('utf-8'))

for f in m['files']:
    if f['path'] == 'mods/Lunarix-Client-v1.2.1.jar':
        f['size'] = 139718854
        f['sha1'] = 'c35194e208fbfdcdd883e0a9f0cb7d57e5e49a70'

m['launcher'] = {
    'version': '1.3.1',
    'filename': UPLOAD_NAME,
    'url': asset_url,
    'sha1': sha1,
    'size': size,
}

payload = json.dumps({
    'message': 'Update launcher exe and client jar hashes (v1.3.1)',
    'content': base64.b64encode(json.dumps(m, indent=2, ensure_ascii=False).encode('utf-8')).decode('utf-8'),
    'sha': minfo['sha'],
}).encode('utf-8')
ch = dict(headers)
ch['Content-Type'] = 'application/json'
res = json.loads(urllib.request.urlopen(urllib.request.Request(murl, data=payload, headers=ch, method='PUT')).read())
print('manifest commit', res['commit']['sha'])
print('DONE')
