import os
import sys
import json
import time
import random
import string
import hashlib
import threading
import urllib.request
import urllib.error
import urllib.parse
from core.config import get_data_dir, get_cache_dir

ADMIN_NOTIFICATION_EMAIL = "pasternakmarkian@gmail.com"

SUPABASE_URL = "https://bgbglvqfrfswopxukdga.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJnYmdsdnFmcmZzd29weHVrZGdhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTQ2MDEzNjQsImV4cCI6MjExMDE3NzM2NH0.rbIiDPtOzyYtt8ytX2BGJJOX8-Ds1Yy-tEMTvF9SsEk"

def get_base_dir():
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_appdata_dir():
    return get_data_dir()

AUTH_FILE = os.path.join(get_data_dir(), "auth_session.json")
APPDATA_AUTH_FILE = os.path.join(get_data_dir(), "auth_session.json")

_OTP_CACHE_FILE = os.path.join(get_data_dir(), "pending_otps.json")
_USER_EMAILS_FILE = os.path.join(get_data_dir(), "user_emails.json")
_HWID_ACCOUNTS_FILE = os.path.join(get_data_dir(), "hwid_accounts.json")

def fix_mojibake_text(text):
    """
    Виявляє та виправляє кирилицю, яка була некоректно збережена через змішування кодувань UTF-8 та Windows-1251.
    Наприклад, рядок 'РџСЂРёРІРµС‚' автоматично відновлюється у 'Привет'.
    """
    if not isinstance(text, str):
        return text
    if any(c in text for c in ("Р", "С", "Ð", "Ñ", "â", "Ã")):
        try:
            repaired = text.encode("cp1251").decode("utf-8")
            return repaired
        except Exception:
            try:
                repaired = text.encode("latin-1").decode("utf-8")
                return repaired
            except Exception:
                pass
    return text

def sanitize_config_encoding(obj):
    """
    Рекурсивно проходить словники та списки конфігурації й виправляє кодування
    кирилиці у всіх ключах та текстових значеннях.
    """
    if isinstance(obj, dict):
        return {fix_mojibake_text(k): sanitize_config_encoding(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_config_encoding(x) for x in obj]
    elif isinstance(obj, str):
        return fix_mojibake_text(obj)
    return obj

def load_json_file_safe(file_path):
    """
    Безпечно відкриває JSON файл, визначаючи кодування (utf-8-sig, utf-8, cp1251, latin-1),
    виправляючи пошкоджену кирилицю, та повертає (True, data) або (False, error).
    """
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
    except Exception as e:
        return False, f"Не вдалося відкрити файл: {e}"

    for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            text = raw.decode(enc)
            try:
                fixed_text = text.encode("cp1251").decode("utf-8")
                data = json.loads(fixed_text)
                return True, sanitize_config_encoding(data)
            except Exception:
                pass
            data = json.loads(text)
            return True, sanitize_config_encoding(data)
        except Exception:
            continue
    return False, "Не вдалося розпізнати або прочитати JSON конфіг"

def _load_pending_otps():
    try:
        if os.path.exists(_OTP_CACHE_FILE):
            with open(_OTP_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_pending_otps(otps):
    try:
        with open(_OTP_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(otps, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _load_user_emails():
    try:
        if os.path.exists(_USER_EMAILS_FILE):
            with open(_USER_EMAILS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_user_email(username, email):
    try:
        data = _load_user_emails()
        u = (username or "").strip().lower()
        e = (email or "").strip().lower()
        if u and e:
            data[u] = email.strip()
            data[e] = username.strip()
            with open(_USER_EMAILS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _get_local_hwid_count(hwid):
    try:
        if os.path.exists(_HWID_ACCOUNTS_FILE):
            with open(_HWID_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return len(data.get(hwid, []))
    except Exception:
        pass
    return 0

def _record_local_hwid(hwid, username):
    try:
        data = {}
        if os.path.exists(_HWID_ACCOUNTS_FILE):
            with open(_HWID_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        users = data.get(hwid, [])
        if username not in users:
            users.append(username)
        data[hwid] = users
        with open(_HWID_ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def load_auth():
    """Loads saved login session if exists (checks both app dir and persistent AppData)."""
    for path in (AUTH_FILE, APPDATA_AUTH_FILE):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("username"):
                        return data
            except Exception:
                pass
    return None

def save_auth(username, password=None, password_hash=None):
    """Saves auth session persistently across restarts to both directories."""
    clean_user = (username or "").strip()
    if not clean_user:
        return
    if password and not password_hash:
        password_hash = hash_password(password)

    session_data = {
        "username": clean_user,
        "password_hash": password_hash or "",
        "saved_at": time.time(),
        "remember_me": True
    }
    for path in (AUTH_FILE, APPDATA_AUTH_FILE):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save auth to {path}:", e)

def clear_auth():
    """Clears auth session from all storage locations."""
    for path in (AUTH_FILE, APPDATA_AUTH_FILE):
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

def verify_account_valid(username, password_hash=None):
    """
    Питає сервер Supabase:
    1. Чи існує ще такий акаунт у базі даних accounts?
    2. Якщо передано хеш пароля — чи він не змінився на сервері?
    Повертає (True, account_dict) або (False, error_reason).
    """
    clean_user = (username or "").strip()
    if not clean_user or clean_user == "Player":
        return False, "Некоректний юзернейм"

    url = f"{SUPABASE_URL}/rest/v1/accounts?username=eq.{urllib.parse.quote(clean_user)}&select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data or len(data) == 0:
                return False, f"Акаунт «{clean_user}» більше не існує на сервері (можливо, видалено або перейменовано)!"
            acc = data[0]
            if password_hash and acc.get("password"):
                if acc.get("password") != password_hash:
                    return False, "Пароль акаунту було змінено на сервері! Будь ласка, увійдіть повторно."
            return True, acc
    except urllib.error.URLError as e:
        print("Warning: Network error checking account:", e)
        return False, f"Не вдалося з'єднатися із сервером авторизації (перевірте підключення до інтернету)"
    except Exception as e:
        return False, str(e)

def update_user_password(username, new_password):
    """Оновлює пароль акаунта напряму в таблиці accounts."""
    clean_user = (username or "").strip()
    if not clean_user:
        return False, "Некоректний юзернейм!"
    if len(new_password) < 4:
        return False, "Пароль має містити щонайменше 4 символи!"

    pwd_hash = hash_password(new_password)
    url = f"{SUPABASE_URL}/rest/v1/accounts?username=eq.{urllib.parse.quote(clean_user)}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = json.dumps({"password": pwd_hash}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
        with urllib.request.urlopen(req, timeout=8) as resp:
            # Оновлюємо також збережену сесію, якщо це поточний користувач
            saved = load_auth()
            if saved and saved.get("username", "").lower() == clean_user.lower():
                save_auth(clean_user, password=new_password)
            return True, "Пароль успішно змінено!"
    except Exception as e:
        return False, f"Помилка оновлення паролю: {e}"

def find_account_by_identifier(identifier):
    """
    Знаходить акаунт та прив'язану пошту за нікнеймом або email.
    Повертає (username, email) або (None, None).
    """
    clean_id = (identifier or "").strip()
    if not clean_id:
        return None, None

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    # 1. Спробуємо знайти прив'язану пошту за нікнеймом
    email = get_account_email(clean_id)
    if email:
        return clean_id, email

    # 2. Перевіримо в таблиці accounts за username
    try:
        url = f"{SUPABASE_URL}/rest/v1/accounts?username=eq.{urllib.parse.quote(clean_id)}&select=*"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and len(data) > 0:
                uname = data[0].get("username")
                email = data[0].get("email") or get_account_email(uname)
                return uname, email
    except Exception:
        pass

    # 3. Перевіримо в таблиці accounts за email (якщо колонка email існує)
    try:
        url = f"{SUPABASE_URL}/rest/v1/accounts?email=eq.{urllib.parse.quote(clean_id.lower())}&select=*"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and len(data) > 0:
                return data[0].get("username"), clean_id.lower()
    except Exception:
        pass

    # 4. Перевіримо в метаданих cloud_configs
    try:
        url = f"{SUPABASE_URL}/rest/v1/cloud_configs?name=eq.account_metadata&select=content"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data:
                c = item.get("content") or {}
                if isinstance(c, dict):
                    if c.get("email", "").lower() == clean_id.lower():
                        return c.get("username"), clean_id.lower()
                    if c.get("username", "").lower() == clean_id.lower():
                        return c.get("username"), c.get("email")
    except Exception:
        pass

    # 5. Спробуємо знайти нікнейм за email в локальній базі користувачів
    emails_map = _load_user_emails()
    matched_user = emails_map.get(clean_id.lower())
    if matched_user:
        return matched_user, clean_id

    if "@" in clean_id:
        return clean_id.split("@")[0], clean_id
    return clean_id, None

# ══════════════════════════════════════════════════════════════════════════════
#  Accounts (Pure Nickname + Password, No Email Required)
# ══════════════════════════════════════════════════════════════════════════════
def sign_in_nickname(username, password):
    clean_user = username.strip()
    pwd_hash = hash_password(password)
    url = f"{SUPABASE_URL}/rest/v1/accounts?username=eq.{urllib.parse.quote(clean_user)}&select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data or len(data) == 0:
                return False, "Користувача з таким нікнеймом не знайдено"
            account = data[0]
            if account.get("password") == pwd_hash:
                return True, clean_user
            return False, "Невірний пароль!"
    except Exception as e:
        return False, str(e)

def sign_up_nickname(username, password):
    clean_user = username.strip()
    if len(clean_user) < 3:
        return False, "Нікнейм має бути не менше 3 символів"
    if len(password) < 4:
        return False, "Пароль має бути не менше 4 символів"

    # Check if exists
    url_check = f"{SUPABASE_URL}/rest/v1/accounts?username=eq.{urllib.parse.quote(clean_user)}&select=username"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url_check, headers=headers), timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and len(data) > 0:
                return False, "Цей нікнейм вже зайнятий!"
    except Exception as e:
        return False, str(e)

    # Insert new account
    url_insert = f"{SUPABASE_URL}/rest/v1/accounts"
    payload = json.dumps({
        "username": clean_user,
        "password": hash_password(password)
    }).encode("utf-8")
    insert_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    try:
        req = urllib.request.Request(url_insert, data=payload, headers=insert_headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return True, clean_user
    except Exception as e:
        return False, str(e)


# ══════════════════════════════════════════════════════════════════════════════
#  Cloud Configs (Share Code, Publish, List, Download)
# ══════════════════════════════════════════════════════════════════════════════
def generate_share_code(length=6):
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))

def list_cloud_configs():
    url = f"{SUPABASE_URL}/rest/v1/cloud_configs?select=*&order=created_at.desc"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # Фільтруємо будь-яке сміття, залишаємо виключно ігрові конфіги гравців
            game_configs = []
            for item in data:
                if item.get("name") in ("verification_code", "account_metadata", "rename_request", "global_chat", "player_status", "resourcepack"):
                    continue
                if str(item.get("id", "")).startswith(("CODE_", "ACC_", "REN_", "CHAT_", "STATUS_", "RP_")):
                    continue
                sanitized_item = {
                    "id": item.get("id"),
                    "name": fix_mojibake_text(item.get("name", "Config")),
                    "author": fix_mojibake_text(item.get("author", "Unknown")),
                    "description": fix_mojibake_text(item.get("description", "")),
                    "downloads": item.get("downloads", 0),
                    "content": sanitize_config_encoding(item.get("content", {})),
                    "created_at": item.get("created_at")
                }
                game_configs.append(sanitized_item)
            return True, game_configs
    except Exception as e:
        return False, []

def get_cloud_config_by_id(config_id):
    clean_id = config_id.strip().upper()
    url = f"{SUPABASE_URL}/rest/v1/cloud_configs?id=eq.{urllib.parse.quote(clean_id)}&select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and len(data) > 0:
                raw_item = data[0]
                sanitized_item = {
                    "id": raw_item.get("id"),
                    "name": fix_mojibake_text(raw_item.get("name", "Config")),
                    "author": fix_mojibake_text(raw_item.get("author", "Unknown")),
                    "description": fix_mojibake_text(raw_item.get("description", "")),
                    "downloads": raw_item.get("downloads", 0),
                    "content": sanitize_config_encoding(raw_item.get("content", {})),
                    "created_at": raw_item.get("created_at")
                }
                # Increment download counter
                try:
                    inc_url = f"{SUPABASE_URL}/rest/v1/cloud_configs?id=eq.{urllib.parse.quote(clean_id)}"
                    inc_payload = json.dumps({"downloads": raw_item.get("downloads", 0) + 1}).encode("utf-8")
                    inc_headers = {
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json"
                    }
                    urllib.request.urlopen(urllib.request.Request(inc_url, data=inc_payload, headers=inc_headers, method="PATCH"), timeout=5)
                except Exception:
                    pass
                return True, sanitized_item
            return False, "Конфіг з таким кодом не знайдено"
    except Exception as e:
        return False, str(e)

def publish_cloud_config(name, author, content_dict, description=""):
    share_id = generate_share_code(6)
    url = f"{SUPABASE_URL}/rest/v1/cloud_configs"

    if isinstance(content_dict, str):
        try:
            content_dict = json.loads(content_dict)
        except Exception:
            pass

    sanitized_content = sanitize_config_encoding(content_dict)
    clean_name = fix_mojibake_text(name.strip())
    clean_author = fix_mojibake_text(author.strip())
    clean_desc = fix_mojibake_text(description.strip())

    payload = json.dumps({
        "id": share_id,
        "name": clean_name,
        "author": clean_author,
        "description": clean_desc,
        "content": sanitized_content,
        "downloads": 0
    }, ensure_ascii=False).encode("utf-8")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json; charset=utf-8"
    }
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return True, share_id
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode("utf-8"))
            return False, str(err)
        except Exception:
            return False, f"HTTP Error {e.code}"
    except Exception as e:
        return False, str(e)


# ══════════════════════════════════════════════════════════════════════════════
#  Social Network & Friendship System (All Registered Users, Requests, Friends)
# ══════════════════════════════════════════════════════════════════════════════
def list_all_registered_users():
    """Повертає список усіх зареєстрованих акаунтів софту."""
    url = f"{SUPABASE_URL}/rest/v1/accounts?select=username,created_at&order=created_at.desc"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [d["username"] for d in data if d.get("username")]
    except Exception as e:
        print("Error fetching accounts:", e)
        return []

def list_accepted_friends(username):
    """Повертає список підтверджених друзів (де статус 'accepted')."""
    clean_u = username.strip()
    # Friend if sender == me or receiver == me with status 'accepted'
    url = f"{SUPABASE_URL}/rest/v1/friend_requests?status=eq.accepted&or=(sender.eq.{urllib.parse.quote(clean_u)},receiver.eq.{urllib.parse.quote(clean_u)})&select=sender,receiver"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            friends = set()
            for r in data:
                s = r.get("sender")
                rec = r.get("receiver")
                if s and s.lower() != clean_u.lower():
                    friends.add(s)
                elif rec and rec.lower() != clean_u.lower():
                    friends.add(rec)
            return list(friends)
    except Exception as e:
        print("Error fetching accepted friends:", e)
        return []

def list_pending_incoming_requests(username):
    """Повертає вхідні заявки, надіслані користувачу."""
    clean_u = username.strip()
    url = f"{SUPABASE_URL}/rest/v1/friend_requests?receiver=eq.{urllib.parse.quote(clean_u)}&status=eq.pending&select=id,sender,created_at"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print("Error fetching incoming requests:", e)
        return []

def list_pending_outgoing_requests(username):
    """Повертає вихідні заявки, які надіслав користувач."""
    clean_u = username.strip()
    url = f"{SUPABASE_URL}/rest/v1/friend_requests?sender=eq.{urllib.parse.quote(clean_u)}&status=eq.pending&select=id,receiver,created_at"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print("Error fetching outgoing requests:", e)
        return []

def send_friend_request(sender, receiver):
    clean_s = sender.strip()
    clean_r = receiver.strip()
    if not clean_s or not clean_r:
        return False, "Нікнейм не може бути порожнім"
    if clean_s.lower() == clean_r.lower():
        return False, "Не можна надіслати заявку самому собі"

    # Check if request or friendship already exists in either direction
    url_check = f"{SUPABASE_URL}/rest/v1/friend_requests?or=(and(sender.eq.{urllib.parse.quote(clean_s)},receiver.eq.{urllib.parse.quote(clean_r)}),and(sender.eq.{urllib.parse.quote(clean_r)},receiver.eq.{urllib.parse.quote(clean_s)}))&select=id,status"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url_check, headers=headers), timeout=8) as resp:
            existing = json.loads(resp.read().decode("utf-8"))
            if existing:
                status = existing[0].get("status")
                if status == "accepted":
                    return False, "Ви вже є друзями!"
                return False, "Заявку в друзі вже надіслано!"
    except Exception:
        pass

    url_insert = f"{SUPABASE_URL}/rest/v1/friend_requests"
    headers_post = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = json.dumps({"sender": clean_s, "receiver": clean_r, "status": "pending"}).encode("utf-8")
    try:
        req = urllib.request.Request(url_insert, data=payload, headers=headers_post, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return True, clean_r
    except Exception as e:
        return False, str(e)

def accept_friend_request(request_id):
    url = f"{SUPABASE_URL}/rest/v1/friend_requests?id=eq.{request_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = json.dumps({"status": "accepted"}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return True, "Прийнято"
    except Exception as e:
        return False, str(e)

def decline_or_cancel_request(request_id):
    url = f"{SUPABASE_URL}/rest/v1/friend_requests?id=eq.{request_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        req = urllib.request.Request(url, headers=headers, method="DELETE")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return True, "Видалено"
    except Exception as e:
        return False, str(e)

def remove_friendship(user_a, user_b):
    clean_a = user_a.strip()
    clean_b = user_b.strip()
    url = f"{SUPABASE_URL}/rest/v1/friend_requests?or=(and(sender.eq.{urllib.parse.quote(clean_a)},receiver.eq.{urllib.parse.quote(clean_b)}),and(sender.eq.{urllib.parse.quote(clean_b)},receiver.eq.{urllib.parse.quote(clean_a)}))"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        req = urllib.request.Request(url, headers=headers, method="DELETE")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return True, "Дружбу розірвано"
    except Exception as e:
        return False, str(e)


# ══════════════════════════════════════════════════════════════════════════════
#  HWID & Email Registration (Max 3 Accounts per HWID + Email Verification)
# ══════════════════════════════════════════════════════════════════════════════
def get_hwid():
    parts = []
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
        guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        parts.append(str(guid).strip())
    except Exception:
        pass
    try:
        import subprocess
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystemProduct).UUID"],
            text=True
        ).strip()
        if out:
            parts.append(out)
    except Exception:
        pass
    if not parts:
        import platform
        parts.append(platform.node())
    return hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()[:24]

def get_hwid_registered_count(hwid):
    """
    Рахує, скільки акаунтів вже зареєстровано на цей HWID:
    1. Перевіряє таблицю accounts (якщо колонка hwid існує).
    2. Перевіряє хмарні записи account_metadata.
    3. Перевіряє локальні збережені дані.
    """
    users = set()
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    # 1. Перевірка таблиці accounts за hwid
    try:
        url = f"{SUPABASE_URL}/rest/v1/accounts?hwid=eq.{urllib.parse.quote(hwid)}&select=username"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data:
                if item.get("username"):
                    users.add(item["username"].lower())
    except Exception:
        pass

    # 2. Перевірка account_metadata в cloud_configs
    try:
        url = f"{SUPABASE_URL}/rest/v1/cloud_configs?name=eq.account_metadata&select=content"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data:
                c = item.get("content") or {}
                if isinstance(c, dict) and c.get("hwid") == hwid and c.get("username"):
                    users.add(c["username"].lower())
    except Exception:
        pass

    # 3. Перевірка локальних даних
    try:
        if os.path.exists(_HWID_ACCOUNTS_FILE):
            with open(_HWID_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                for u in d.get(hwid, []):
                    users.add(u.lower())
    except Exception:
        pass

    return len(users)

def _send_otp_email(clean_email, clean_user, code, action="код"):
    """
    Надсилає 6-значний код підтвердження на електронну пошту.
    """
    def _worker():
        print(f"\n=======================================================")
        print(f"🔑 [LUNARIX SECURITY CODE] Код: {code} для {clean_user} ({clean_email})")
        print(f"   Дія: {action} | Час: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"=======================================================\n")

        # 1. Відправка через FormSubmit (доставляє на email, включно з pasternakmarkian@gmail.com)
        try:
            url = f"https://formsubmit.co/ajax/{clean_email}"
            payload = {
                "name": "Lunarix Client Security",
                "_subject": f"🔑 Ваш код підтвердження LUNARIX: {code}",
                "_captcha": "false",
                "_template": "box",
                "Користувач": clean_user,
                "Дія": action,
                "КОД_ПІДТВЕРДЖЕННЯ": code,
                "Повідомлення": f"Ваш 6-значний код підтвердження: {code}. Введіть його у вікні лаунчера. Нікому не передавайте цей код!"
            }
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LunarixLauncher/1.0",
                    "Referer": "https://lunarix.client/"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except Exception as e:
            print("FormSubmit OTP delivery notice:", e)

        # 2. Якщо в config.json вказано власні налаштування SMTP
        try:
            from core.config import load_config
            cfg = load_config()
            s_host = cfg.get("smtp_host", os.getenv("SMTP_HOST", ""))
            s_port = int(cfg.get("smtp_port", os.getenv("SMTP_PORT", 587)))
            s_user = cfg.get("smtp_user", os.getenv("SMTP_USER", ""))
            s_pass = cfg.get("smtp_pass", os.getenv("SMTP_PASS", ""))
            if s_user and s_pass and s_host:
                import smtplib
                from email.message import EmailMessage
                msg = EmailMessage()
                msg.set_content(f"Вітаємо, {clean_user}!\n\nВаш 6-значний код підтвердження LUNARIX: {code}\nДія: {action}\n\nНікому не повідомляйте цей код!")
                msg["Subject"] = f"🔑 Код підтвердження LUNARIX: {code}"
                msg["From"] = s_user
                msg["To"] = clean_email
                with smtplib.SMTP(s_host, s_port, timeout=10) as srv:
                    srv.starttls()
                    srv.login(s_user, s_pass)
                    srv.send_message(msg)
        except Exception as e:
            print("SMTP delivery notice:", e)

    threading.Thread(target=_worker, daemon=True).start()

def send_email_verification_code(email, username, action="register"):
    """
    Генерує 6-значний код підтвердження, зберігає локально та надсилає користувачу.
    НЕ зберігає в хмарні конфіги Supabase!
    """
    clean_email = (email or "").strip().lower()
    clean_user = (username or "").strip()
    code = f"{random.randint(100000, 999999)}"

    # Зберігаємо код підтвердження в локальному сховищі на 15 хв
    now = time.time()
    otps = _load_pending_otps()
    otps = {k: v for k, v in otps.items() if v.get("expires", 0) > now}
    entry = {
        "code": code,
        "email": clean_email,
        "username": clean_user,
        "action": action,
        "expires": now + 900
    }
    if clean_email:
        otps[f"{clean_email}:{action}"] = entry
    if clean_user:
        otps[f"{clean_user.lower()}:{action}"] = entry
    _save_pending_otps(otps)

    action_labels = {
        "register": "Реєстрація акаунта",
        "reset_password": "Відновлення / зміна паролю",
        "delete": "Видалення акаунта"
    }
    _send_otp_email(clean_email, clean_user, code, action=action_labels.get(action, action))
    return True, code

def verify_email_code(email, username, input_code, action="register"):
    clean_email = (email or "").strip().lower()
    clean_user = (username or "").strip().lower()
    clean_code = (input_code or "").strip()

    if not clean_code or len(clean_code) < 4:
        return False, "Введіть 6-значний код підтвердження!"

    now = time.time()
    otps = _load_pending_otps()

    candidates = []
    if clean_email:
        candidates.append(f"{clean_email}:{action}")
    if clean_user:
        candidates.append(f"{clean_user}:{action}")

    for key in candidates:
        item = otps.get(key)
        if item:
            if item.get("expires", 0) < now:
                return False, "Час дії коду вичерпано. Надішліть новий код!"
            if str(item.get("code")).strip() == clean_code:
                # Видаляємо використаний код
                otps.pop(key, None)
                _save_pending_otps(otps)
                return True, "Код підтверджено"

    return False, "Невірний або застарілий код підтвердження!"

def register_with_email_and_hwid(username, email, password, code):
    clean_user = username.strip()
    clean_email = email.strip().lower()
    hwid = get_hwid()

    if len(clean_user) < 3:
        return False, "Нікнейм має містити щонайменше 3 символи!"
    if len(password) < 4:
        return False, "Пароль має містити щонайменше 4 символи!"
    if "@" not in clean_email or "." not in clean_email:
        return False, "Введіть дійсну адресу електронної пошти!"

    # HWID registration limit check (max 3 accounts)
    count = get_hwid_registered_count(hwid)
    if count >= 3:
        return False, "На цей комп'ютер (HWID) вже досягнуто максимальний ліміт (максимум 3 акаунти)!"

    # Check if username exists
    url_check = f"{SUPABASE_URL}/rest/v1/accounts?username=eq.{urllib.parse.quote(clean_user)}&select=username"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url_check, headers=headers), timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and len(data) > 0:
                return False, "Цей нікнейм вже зайнятий іншим користувачем!"
    except Exception as e:
        return False, str(e)

    # Verify code
    ok, msg = verify_email_code(clean_email, clean_user, code, action="register")
    if not ok:
        return False, msg

    # Create account in accounts table
    url_insert = f"{SUPABASE_URL}/rest/v1/accounts"
    insert_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    # Спроба 1: Зберігаємо напряму в таблицю accounts з прив'язкою email та hwid
    payload_full = {
        "username": clean_user,
        "password": hash_password(password),
        "email": clean_email,
        "hwid": hwid
    }
    inserted = False
    try:
        req = urllib.request.Request(url_insert, data=json.dumps(payload_full).encode("utf-8"), headers=insert_headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            inserted = True
    except urllib.error.HTTPError as e:
        # Якщо в таблиці accounts ще не створені стовпці email/hwid, записуємо базові поля
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        if "does not exist" in err_body or e.code == 400:
            payload_basic = {
                "username": clean_user,
                "password": hash_password(password)
            }
            try:
                req_basic = urllib.request.Request(url_insert, data=json.dumps(payload_basic).encode("utf-8"), headers=insert_headers, method="POST")
                with urllib.request.urlopen(req_basic, timeout=8) as resp:
                    inserted = True
            except Exception as e2:
                return False, f"Помилка створення акаунта: {e2}"
        else:
            return False, f"Помилка створення акаунта: {err_body or e}"
    except Exception as e:
        return False, f"Помилка створення акаунта: {e}"

    # Зберігаємо метадані прив'язки email та hwid у хмарну таблицю (для синхронізації між пристроями)
    try:
        meta_url = f"{SUPABASE_URL}/rest/v1/cloud_configs"
        meta_payload = {
            "id": f"ACC_{clean_user.upper()}",
            "name": "account_metadata",
            "author": clean_user,
            "description": f"Metadata for {clean_user}",
            "content": {
                "username": clean_user,
                "email": clean_email,
                "hwid": hwid,
                "registered_at": time.time()
            },
            "downloads": 0
        }
        req_meta = urllib.request.Request(meta_url, data=json.dumps(meta_payload).encode("utf-8"), headers=insert_headers, method="POST")
        urllib.request.urlopen(req_meta, timeout=5)
    except Exception:
        pass

    # Зберігаємо email та прив'язку HWID локально у директорію даних лаунчера
    _save_user_email(clean_user, clean_email)
    _record_local_hwid(hwid, clean_user)

    return True, clean_user


# ══════════════════════════════════════════════════════════════════════════════
#  Profile: Admin Rename Requests & Self Account Deletion
# ══════════════════════════════════════════════════════════════════════════════
def _send_admin_rename_email(current_username, requested_username, reason, req_id):
    """
    Надсилає сповіщення на пошту адміністратора про новий запит на зміну нікнейма.
    Виконується у фоновому потоці (не блокує інтерфейс).
    """
    def _worker():
        try:
            url = f"https://formsubmit.co/ajax/{ADMIN_NOTIFICATION_EMAIL}"
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            payload = {
                "name": "Lunarix Launcher",
                "_subject": f"🔔 [Lunarix] Запит на зміну нікнейма: {current_username} ➔ {requested_username}",
                "_captcha": "false",
                "_template": "table",
                "Поточний юзернейм": current_username,
                "Бажаний новий юзернейм": requested_username,
                "Причина зміни": reason.strip() if reason and reason.strip() else "(Причина не вказана)",
                "ID заявки": req_id,
                "Дата та час подання": now_str,
                "Статус": "В очікуванні розгляду (pending)"
            }
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LunarixLauncher/1.0",
                    "Referer": "https://lunarix.client/"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except Exception as e:
            print("Failed to send admin notification email:", e)

    threading.Thread(target=_worker, daemon=True).start()

def request_username_rename(username, new_username, reason=""):
    clean_user = username.strip()
    clean_new = new_username.strip()
    if len(clean_new) < 3:
        return False, "Новий нікнейм має містити щонайменше 3 символи!"
    if clean_new.lower() == clean_user.lower():
        return False, "Новий нікнейм збігається з поточним!"

    url_check = f"{SUPABASE_URL}/rest/v1/accounts?username=eq.{urllib.parse.quote(clean_new)}&select=username"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url_check, headers=headers), timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and len(data) > 0:
                return False, f"Нікнейм «{clean_new}» вже зайнятий іншим користувачем!"
    except Exception as e:
        return False, str(e)

    req_id = f"REN_{clean_user}_{int(time.time())}"
    # Надсилаємо сповіщення на пошту адміністратора напряму
    _send_admin_rename_email(clean_user, clean_new, reason, req_id)
    return True, "Запит на зміну нікнейма успішно надіслано адміністратору!"

def get_pending_rename_request(username):
    return None

def get_account_email(username):
    """
    Знаходить прив'язану до акаунта електронну пошту:
    1. Перевіряє таблицю accounts (якщо колонка email існує).
    2. Перевіряє хмарні метадані account_metadata.
    3. Перевіряє локальні збережені дані.
    """
    clean_user = (username or "").strip()
    if not clean_user:
        return None

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    # 1. Таблиця accounts
    try:
        url = f"{SUPABASE_URL}/rest/v1/accounts?username=eq.{urllib.parse.quote(clean_user)}&select=email"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and data[0].get("email"):
                return data[0].get("email").strip().lower()
    except Exception:
        pass

    # 2. Хмарні метадані в cloud_configs
    try:
        acc_id = f"ACC_{clean_user.upper()}"
        url = f"{SUPABASE_URL}/rest/v1/cloud_configs?id=eq.{urllib.parse.quote(acc_id)}&select=content"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data[0].get("content"), dict):
                email = data[0]["content"].get("email")
                if email:
                    return email.strip().lower()
    except Exception:
        pass

    # 3. Локальне сховище user_emails.json
    return _load_user_emails().get(clean_user.lower())

def request_account_deletion_code(username):
    clean_user = username.strip()
    email = get_account_email(clean_user)
    if not email:
        return False, "До цього акаунту не знайдено прив'язаної електронної пошти!"
    return send_email_verification_code(email, clean_user, action="delete")

def confirm_account_deletion(username, input_code):
    clean_user = username.strip()
    email = get_account_email(clean_user)
    if not email:
        return False, "До цього акаунту не знайдено прив'язаної електронної пошти!"
    ok, msg = verify_email_code(email, clean_user, input_code, action="delete")
    if not ok:
        return False, msg

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    # Delete from accounts table
    try:
        del_acc_url = f"{SUPABASE_URL}/rest/v1/accounts?username=eq.{urllib.parse.quote(clean_user)}"
        urllib.request.urlopen(urllib.request.Request(del_acc_url, headers=headers, method="DELETE"), timeout=8)
    except Exception as e:
        return False, f"Помилка видалення акаунта: {e}"

    # Delete metadata from cloud_configs
    try:
        del_meta_url = f"{SUPABASE_URL}/rest/v1/cloud_configs?id=eq.{urllib.parse.quote(f'ACC_{clean_user.upper()}')}"
        urllib.request.urlopen(urllib.request.Request(del_meta_url, headers=headers, method="DELETE"), timeout=5)
    except Exception:
        pass

    clear_auth()
    try:
        em = _load_user_emails()
        em.pop(clean_user.lower(), None)
        with open(_USER_EMAILS_FILE, "w", encoding="utf-8") as f:
            json.dump(em, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return True, "Акаунт успішно видалено!"


# ══════════════════════════════════════════════════════════════════════════════
#  Global Real-Time Chat System
# ══════════════════════════════════════════════════════════════════════════════
def send_global_chat_message(author, message):
    clean_auth = author.strip() or "Player"
    clean_msg = message.strip()
    if not clean_msg:
        return False, "Повідомлення не може бути порожнім!"
    if len(clean_msg) > 300:
        return False, "Повідомлення занадто довге (максимум 300 символів)!"

    msg_id = f"CHAT_{int(time.time() * 1000)}_{random.randint(100, 999)}"
    url = f"{SUPABASE_URL}/rest/v1/cloud_configs"
    payload = json.dumps({
        "id": msg_id,
        "name": "global_chat",
        "author": clean_auth,
        "description": clean_msg,
        "content": {
            "message": clean_msg,
            "author": clean_auth,
            "created_at": time.time()
        },
        "downloads": 0
    }).encode("utf-8")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return True, "Надіслано"
    except Exception as e:
        return False, str(e)

def fetch_global_chat_messages(limit=60):
    url = f"{SUPABASE_URL}/rest/v1/cloud_configs?name=eq.global_chat&order=created_at.desc&limit={limit}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            data.reverse()
            return True, data
    except Exception as e:
        return False, []


# ══════════════════════════════════════════════════════════════════════════
#  Player Presence & Activity System (Online / Server / Singleplayer)
# ══════════════════════════════════════════════════════════════════════════
def update_player_presence(username, status="online", activity="Launcher", server=""):
    """
    Оновлює онлайн-статус гравця в Supabase.
    status: 'online', 'in_game', 'offline'
    activity: 'В лаунчері', 'Одиночна гра (Singleplayer)', 'На сервері'
    server: назва або IP сервера
    """
    clean_u = username.strip()
    if not clean_u:
        return False, "Нікнейм порожній"

    status_id = f"STATUS_{clean_u.upper()}"
    url = f"{SUPABASE_URL}/rest/v1/cloud_configs"

    payload_data = {
        "id": status_id,
        "name": "player_status",
        "author": clean_u,
        "description": status,
        "content": {
            "status": status,
            "activity": activity,
            "server": server,
            "last_seen": int(time.time())
        },
        "downloads": 0
    }
    payload = json.dumps(payload_data, ensure_ascii=False).encode("utf-8")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json; charset=utf-8",
        "Prefer": "resolution=merge-duplicates"
    }
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=6) as resp:
            return True, "Статус оновлено"
    except Exception as e:
        return False, str(e)


def fetch_players_presence(usernames=None):
    """
    Отримує актуальний статус гравців. Якщо гравець не надсилав пінги понад 2 хвилини — він вважається офлайн.
    Повертає dict: { username_lower: { 'is_online': bool, 'text': str, 'color': str, 'server': str, 'activity': str } }
    """
    url = f"{SUPABASE_URL}/rest/v1/cloud_configs?name=eq.player_status&select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    results = {}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=7) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            now = int(time.time())
            for item in data:
                author = item.get("author", "")
                if not author:
                    continue
                content = item.get("content", {})
                if not isinstance(content, dict):
                    content = {}
                last_seen = content.get("last_seen", 0)
                raw_status = content.get("status", "offline")
                activity = content.get("activity", "В лаунчері")
                server = content.get("server", "")

                # Якщо пінг був менше 130 секунд тому і статус не офлайн
                is_active = (now - last_seen < 130) and (raw_status != "offline")

                if is_active:
                    if raw_status == "in_game":
                        if server:
                            text = f"Грає на сервері: {server}"
                        elif "single" in activity.lower() or "одиноч" in activity.lower():
                            text = "Грає в одиночному режимі (Singleplayer)"
                        else:
                            text = f"Грає в клієнті ({activity})"
                        color = "#10b981"  # Emerald green
                    else:
                        text = "В мережі (У лаунчері)"
                        color = "#22c55e"  # Green
                else:
                    text = "Офлайн"
                    color = "#64748b"  # Slate gray

                results[author.lower()] = {
                    "is_online": is_active,
                    "text": text,
                    "color": color,
                    "activity": activity if is_active else "Офлайн",
                    "server": server if is_active else "",
                    "last_seen": last_seen
                }
    except Exception as e:
        print("Presence fetch error:", e)
    return results


# ══════════════════════════════════════════════════════════════════════════
#  Community Resource Packs Catalog System (Player Uploads)
# ══════════════════════════════════════════════════════════════════════════
def list_community_resourcepacks():
    """Повертає список ресурспаків, опублікованих гравцями спільноти."""
    url = f"{SUPABASE_URL}/rest/v1/cloud_configs?name=eq.resourcepack&order=created_at.desc"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            packs = []
            for item in data:
                c = item.get("content", {})
                if not isinstance(c, dict):
                    c = {}
                pack_obj = {
                    "id": item.get("id"),
                    "name": fix_mojibake_text(c.get("pack_name", item.get("description", "Resource Pack"))),
                    "author": fix_mojibake_text(item.get("author", "Unknown")),
                    "description": fix_mojibake_text(c.get("description", "")),
                    "file_url": c.get("file_url", ""),
                    "file_name": c.get("file_name", "pack.zip"),
                    "downloads": item.get("downloads", 0),
                    "created_at": item.get("created_at")
                }
                packs.append(pack_obj)
            return True, packs
    except Exception as e:
        return False, []


def publish_community_resourcepack(pack_name, author, download_url, description=""):
    """Публікує ресурспак гравця в каталог спільноти."""
    clean_name = pack_name.strip()
    clean_author = author.strip() or "Player"
    clean_url = download_url.strip()
    clean_desc = description.strip()

    if not clean_name:
        return False, "Назва ресурспаку не може бути порожньою!"
    if not clean_url.startswith(("http://", "https://")):
        return False, "Вкажіть пряме посилання на завантаження (.zip)!"

    share_id = f"RP_{generate_share_code(6)}"
    file_name = clean_name.replace(" ", "_") + ".zip"
    if not file_name.endswith(".zip"):
        file_name += ".zip"

    url = f"{SUPABASE_URL}/rest/v1/cloud_configs"
    payload = json.dumps({
        "id": share_id,
        "name": "resourcepack",
        "author": clean_author,
        "description": clean_name,
        "content": {
            "pack_name": clean_name,
            "author": clean_author,
            "description": clean_desc,
            "file_url": clean_url,
            "file_name": file_name
        },
        "downloads": 0
    }, ensure_ascii=False).encode("utf-8")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json; charset=utf-8"
    }
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return True, share_id
    except Exception as e:
        return False, str(e)


def install_community_resourcepack(pack_item, rp_dir, progress_cb=None):
    """Завантажує ресурспак зі спільноти у папку resourcepacks/."""
    os.makedirs(rp_dir, exist_ok=True)
    file_url = pack_item.get("file_url")
    if not file_url:
        return False, "Немає посилання на завантаження"

    filename = pack_item.get("file_name", "pack.zip")
    if not filename.endswith(".zip"):
        filename += ".zip"

    target_path = os.path.join(rp_dir, filename)
    temp_path = target_path + ".download"

    req = urllib.request.Request(file_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp, open(temp_path, "wb") as out_file:
            total_size = int(resp.headers.get("Content-Length", 0))
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

        # Increment download counter in Supabase
        pack_id = pack_item.get("id")
        if pack_id:
            try:
                inc_url = f"{SUPABASE_URL}/rest/v1/cloud_configs?id=eq.{urllib.parse.quote(pack_id)}"
                inc_payload = json.dumps({"downloads": pack_item.get("downloads", 0) + 1}).encode("utf-8")
                inc_headers = {
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                }
                urllib.request.urlopen(urllib.request.Request(inc_url, data=inc_payload, headers=inc_headers, method="PATCH"), timeout=5)
            except Exception:
                pass

        return True, filename
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False, str(e)


