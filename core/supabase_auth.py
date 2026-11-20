import os
import json
import urllib.request
import urllib.error

SUPABASE_URL = "https://bgbglvqfrfswopxukdga.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJnYmdsdnFmcmZzd29weHVrZGdhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTQ2MDEzNjQsImV4cCI6MjExMDE3NzM2NH0.rbIiDPtOzyYtt8ytX2BGJJOX8-Ds1Yy-tEMTvF9SsEk"

from core.config import AUTH_FILE, get_data_dir

AUTH_CACHE_FILE = AUTH_FILE

def load_cached_session():
    """Loads saved login session if 'Remember Me' was checked."""
    if os.path.exists(AUTH_CACHE_FILE):
        try:
            with open(AUTH_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("access_token") and data.get("user"):
                    return data
        except Exception:
            pass
    return None

def save_session(session_data):
    """Saves auth session to disk."""
    try:
        with open(AUTH_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Failed to save auth session:", e)

def clear_session():
    """Removes saved auth session on logout."""
    if os.path.exists(AUTH_CACHE_FILE):
        try:
            os.remove(AUTH_CACHE_FILE)
        except Exception:
            pass

def supabase_sign_in(email, password):
    """Sign in existing user with email and password."""
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    payload = json.dumps({"email": email.strip(), "password": password}).encode("utf-8")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return True, data
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode("utf-8"))
            msg = err.get("msg") or err.get("error_description") or str(err)
            return False, msg
        except Exception:
            return False, f"HTTP Error {e.code}"
    except Exception as e:
        return False, str(e)

def supabase_sign_up(email, password, username="Player"):
    """Register new user with email and password."""
    url = f"{SUPABASE_URL}/auth/v1/signup"
    payload = json.dumps({
        "email": email.strip(),
        "password": password,
        "data": {"username": username}
    }).encode("utf-8")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return True, data
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode("utf-8"))
            msg = err.get("msg") or err.get("error_description") or str(err)
            return False, msg
        except Exception:
            return False, f"HTTP Error {e.code}"
    except Exception as e:
        return False, str(e)
