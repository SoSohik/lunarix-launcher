import os
import sys
import json
import time
import threading
import concurrent.futures
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageOps
import numpy as np
import io

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# Windows Taskbar Icon Fix
if os.name == 'nt':
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('lunarix.client.launcher.1.21.11')
    except Exception:
        pass

# Paths
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.config import (
    load_config,
    save_config,
    detect_java,
    get_data_dir,
    get_cache_dir,
    get_avatars_cache_dir,
    clear_all_launcher_data,
    restart_launcher,
    ALTS_FILE,
    OLD_ALTS_FILE,
    AUTH_FILE
)
from core.profile import (
    avatar_path as profile_avatar_path,
    display_name as profile_display_name,
    set_avatar_from_file as profile_set_avatar,
    clear_avatar as profile_clear_avatar,
    export_profile as profile_export,
)
from core.downloader import (
    is_game_installed,
    install_or_update_game,
    check_launcher_update,
    check_client_update,
    apply_launcher_update,
    cleanup_launcher_update_leftovers,
    LAUNCHER_VERSION,
)
from core.launcher import launch_minecraft
from core.modrinth import (
    search_modrinth_mods,
    install_mod_from_modrinth,
    load_mod_icon_pil,
    search_modrinth_resourcepacks,
    install_resourcepack_from_modrinth
)
from core.curseforge import (
    search_curseforge_mods,
    search_curseforge_resourcepacks,
    install_file_from_curseforge,
    load_curseforge_icon_pil
)
from core.i18n import t
from core.cloud_configs import (
    get_base_dir,
    sign_in_nickname,
    sign_up_nickname,
    load_auth,
    save_auth,
    clear_auth,
    verify_account_valid,
    update_user_password,
    find_account_by_identifier,
    list_cloud_configs,
    get_cloud_config_by_id,
    publish_cloud_config,
    list_all_registered_users,
    list_accepted_friends,
    list_pending_incoming_requests,
    list_pending_outgoing_requests,
    send_friend_request,
    accept_friend_request,
    decline_or_cancel_request,
    remove_friendship,
    get_hwid,
    get_hwid_registered_count,
    send_email_verification_code,
    verify_email_code,
    register_with_email_and_hwid,
    request_username_rename,
    get_pending_rename_request,
    get_account_email,
    request_account_deletion_code,
    confirm_account_deletion,
    send_global_chat_message,
    fetch_global_chat_messages,
    load_json_file_safe,
    sanitize_config_encoding,
    fix_mojibake_text,
    update_player_presence,
    fetch_players_presence,
    list_community_resourcepacks,
    publish_community_resourcepack,
    install_community_resourcepack
)
from core.local_configs import (
    CLIENT_CONFIG_DIR,
    list_local_configs,
    create_config_file,
    rename_config_file,
    delete_config_file,
    ConfigEditorWindow,
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# ─── Glassmorphism Palette ──────────────────────────────────────────────────────
BG_MAIN         = "#070c18"
BG_SIDEBAR      = "#060a14"
BG_GLASS_CARD   = "#0b162c"
BG_GLASS_INNER  = "#081020"
BORDER_GLASS    = "#1d3557"
BORDER_GLOW     = "#38bdf8"
ACCENT_BLUE     = "#2563eb"
ACCENT_BLUE_HOVER = "#1d4ed8"
ACCENT_CYAN     = "#38bdf8"
TEXT_WHITE      = "#f8fafc"
TEXT_MUTED      = "#8aa4c8"
TEXT_BRIGHT     = "#e2e8f0"

# Background video in Downloads
DOWNLOADS_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
VIDEO_PATH = os.path.join(DOWNLOADS_DIR, "minecraft-sakura-spring-wallsflow-com.mp4")
GIF_PATH = os.path.join(DOWNLOADS_DIR, "minecraft-sakura-spring-wallsflow-com.gif")

# Alts config file (stored in persistent data directory)
if not os.path.exists(ALTS_FILE) and os.path.exists(OLD_ALTS_FILE):
    try:
        shutil.copy2(OLD_ALTS_FILE, ALTS_FILE)
    except Exception:
        pass

LANG_MAP = {
    "Українська": "uk",
    "English": "en",
    "Русский": "ru"
}
LANG_MAP_REV = {v: k for k, v in LANG_MAP.items()}


# ══════════════════════════════════════════════════════════════════════════════
#  Alt Accounts Data & Avatar Helpers
# ══════════════════════════════════════════════════════════════════════════════
def load_alts():
    target = ALTS_FILE if os.path.exists(ALTS_FILE) else OLD_ALTS_FILE
    if os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return ["Player"]

def save_alts(alts):
    try:
        os.makedirs(os.path.dirname(ALTS_FILE), exist_ok=True)
        with open(ALTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alts, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def generate_steve_avatar(size=36):
    img = Image.new('RGBA', (8, 8), (0, 0, 0, 0))
    hair = (40, 24, 16, 255)
    skin = (185, 122, 87, 255)
    eye_white = (255, 255, 255, 255)
    eye_blue = (44, 76, 140, 255)
    mouth = (112, 60, 48, 255)
    pixels = [
        [hair, hair, hair, hair, hair, hair, hair, hair],
        [hair, hair, hair, hair, hair, hair, hair, hair],
        [hair, skin, skin, skin, skin, skin, skin, hair],
        [skin, skin, skin, skin, skin, skin, skin, skin],
        [skin, eye_white, eye_blue, skin, skin, eye_blue, eye_white, skin],
        [skin, skin, skin, mouth, mouth, skin, skin, skin],
        [skin, skin, mouth, mouth, mouth, mouth, skin, skin],
        [skin, skin, skin, skin, skin, skin, skin, skin],
    ]
    for y in range(8):
        for x in range(8):
            img.putpixel((x, y), pixels[y][x])
    return img.resize((size, size), Image.Resampling.NEAREST)

def fetch_skin_head(username, size=36):
    import urllib.request
    clean_u = (username or "Player").strip()
    cache_file = os.path.join(get_avatars_cache_dir(), f"{clean_u.lower()}_{size}.png")
    if os.path.exists(cache_file):
        try:
            return Image.open(cache_file).resize((size, size), Image.Resampling.LANCZOS)
        except Exception:
            pass

    try:
        url = f"https://minotar.net/helm/{clean_u}/{size}.png"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = resp.read()
            img = Image.open(io.BytesIO(data))
            try:
                with open(cache_file, "wb") as cf:
                    cf.write(data)
            except Exception:
                pass
            return img.resize((size, size), Image.Resampling.LANCZOS)
    except Exception:
        pass

    try:
        url = f"https://crafatar.com/avatars/{clean_u}?size={size}&overlay=true"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = resp.read()
            img = Image.open(io.BytesIO(data))
            try:
                with open(cache_file, "wb") as cf:
                    cf.write(data)
            except Exception:
                pass
            return img.resize((size, size), Image.Resampling.LANCZOS)
    except Exception:
        pass

    return generate_steve_avatar(size)


# ══════════════════════════════════════════════════════════════════════════════
#  Alt Switcher (Top Right Glass Capsule)
# ══════════════════════════════════════════════════════════════════════════
class AltSwitcherWidget(ctk.CTkFrame):
    def __init__(self, parent, initial_username="Player", on_change=None, **kwargs):
        super().__init__(
            parent,
            fg_color="#081020",
            corner_radius=16,
            border_width=1,
            border_color="#38bdf8",
            **kwargs
        )
        self._on_change = on_change
        self._alts = load_alts()
        self._current = initial_username
        self._avatar_cache = {}
        self._popup = None

        if self._current not in self._alts:
            self._alts.append(self._current)
            save_alts(self._alts)

        self._build()
        self._load_avatar(self._current)

    def _build(self):
        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(fill="x", padx=8, pady=4)

        self.avatar_lbl = ctk.CTkLabel(
            self.inner, text="", width=32, height=32, corner_radius=8
        )
        self.avatar_lbl.pack(side="left", padx=(0, 8))

        info_col = ctk.CTkFrame(self.inner, fg_color="transparent")
        info_col.pack(side="left", padx=(0, 8))

        self.name_lbl = ctk.CTkLabel(
            info_col, text=self._current,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_WHITE, anchor="w"
        )
        self.name_lbl.pack(anchor="w")

        self.sub_lbl = ctk.CTkLabel(
            info_col, text="Offline Mode",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=ACCENT_CYAN, anchor="w"
        )
        self.sub_lbl.pack(anchor="w")

        self.arrow_btn = ctk.CTkButton(
            self.inner, text="▼", width=24, height=24,
            font=ctk.CTkFont(size=9),
            fg_color="#0e1f38", hover_color=ACCENT_BLUE,
            text_color=TEXT_WHITE, corner_radius=6,
            command=self._toggle_popup
        )
        self.arrow_btn.pack(side="right")

    def get_username(self):
        return self._current

    def set_username(self, name):
        self._current = name
        self.name_lbl.configure(text=name)
        if name not in self._alts:
            self._alts.append(name)
            save_alts(self._alts)
        self._load_avatar(name)
        if self._on_change:
            self._on_change(name)

    def _load_avatar(self, username):
        steve = generate_steve_avatar(32)
        ctk_steve = ctk.CTkImage(light_image=steve, dark_image=steve, size=(32, 32))
        self.avatar_lbl.configure(image=ctk_steve)

        def _fetch():
            img = fetch_skin_head(username, size=32)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32))
            self._avatar_cache[username] = ctk_img
            try:
                self.after(0, lambda: self.avatar_lbl.configure(image=ctk_img))
            except Exception:
                pass
        threading.Thread(target=_fetch, daemon=True).start()

    def _toggle_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None
            return
        self._show_popup()

    def _show_popup(self):
        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 4
        w = max(self.winfo_width(), 240)

        popup = tk.Toplevel(self)
        popup.wm_overrideredirect(True)
        popup.geometry(f"{w}x{min(len(self._alts) * 44 + 60, 260)}+{x}+{y}")
        popup.configure(bg="#070c18")
        popup.attributes("-topmost", True)
        self._popup = popup

        frame = ctk.CTkScrollableFrame(popup, fg_color="#0b162c", corner_radius=12)
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        for alt in self._alts:
            is_active = (alt == self._current)
            row_color = "#122545" if is_active else "transparent"
            row = ctk.CTkFrame(frame, fg_color=row_color, corner_radius=8)
            row.pack(fill="x", padx=4, pady=2)

            av_lbl = ctk.CTkLabel(row, text="", width=24, height=24)
            av_lbl.pack(side="left", padx=(8, 6), pady=4)
            if alt in self._avatar_cache:
                av_lbl.configure(image=self._avatar_cache[alt])
            else:
                st = generate_steve_avatar(24)
                av_lbl.configure(image=ctk.CTkImage(light_image=st, dark_image=st, size=(24, 24)))

            ctk.CTkLabel(
                row, text=alt,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold" if is_active else "normal"),
                text_color=ACCENT_CYAN if is_active else TEXT_WHITE, anchor="w"
            ).pack(side="left", fill="x", expand=True)

            if is_active:
                ctk.CTkLabel(row, text="✓", font=ctk.CTkFont(size=12, weight="bold"), text_color=ACCENT_CYAN).pack(side="right", padx=8)
            else:
                ctk.CTkButton(
                    row, text="Вибрати", width=65, height=22,
                    font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                    fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=11,
                    command=lambda a=alt: self._select_alt(a, popup)
                ).pack(side="right", padx=6, pady=4)

        sep = ctk.CTkFrame(frame, fg_color="#1d3557", height=1)
        sep.pack(fill="x", padx=8, pady=(4, 2))

        add_row = ctk.CTkFrame(frame, fg_color="transparent")
        add_row.pack(fill="x", padx=4, pady=(2, 4))

        new_entry = ctk.CTkEntry(
            add_row, placeholder_text="Новий нікнейм...",
            height=28, font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="#060d1a", border_color=BORDER_GLASS, corner_radius=8
        )
        new_entry.pack(side="left", fill="x", expand=True, padx=(4, 4))

        ctk.CTkButton(
            add_row, text="+", width=28, height=28,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=8,
            command=lambda: self._add_new_alt(new_entry.get().strip(), popup)
        ).pack(side="right", padx=(0, 4))

        popup.bind("<FocusOut>", lambda e: self._close_popup_safe(popup))

    def _close_popup_safe(self, popup):
        try:
            if popup.winfo_exists():
                popup.destroy()
        except Exception:
            pass
        self._popup = None

    def _select_alt(self, alt, popup):
        self._close_popup_safe(popup)
        self.set_username(alt)

    def _add_new_alt(self, name, popup):
        if name and name not in self._alts:
            self._alts.append(name)
            save_alts(self._alts)
        if name:
            self._close_popup_safe(popup)
            self.set_username(name)


# ══════════════════════════════════════════════════════════════════════════════
#  Shimmer Progress Bar (Canvas-based)
# ══════════════════════════════════════════════════════════════════════════════
class GlassProgressBar(tk.Canvas):
    BAR_H = 10
    CORNER = 5

    def __init__(self, parent, width=360, **kwargs):
        kwargs.setdefault("bg", "#081020")
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bd", 0)
        super().__init__(
            parent,
            width=width,
            height=self.BAR_H + 6,
            **kwargs
        )
        self._bar_width = width
        self._value = 0.0
        self._shimmer_x = 0
        self._animating = False
        self._draw()

    def set(self, value):
        self._value = max(0.0, min(1.0, value))
        self._draw()
        if value > 0 and not self._animating:
            self._start_shimmer()
        elif value <= 0:
            self._animating = False

    def _draw(self):
        self.delete("all")
        w = self._bar_width
        h = self.BAR_H
        pad_y = 3

        self._rounded_rect(2, pad_y, w - 2, pad_y + h, self.CORNER, fill="#071222", outline="#1d3557")

        fill_w = int((w - 4) * self._value)
        if fill_w > 0:
            for i in range(fill_w):
                ratio = i / max(fill_w - 1, 1)
                r = int(0x25 + (0x38 - 0x25) * ratio)
                g = int(0x63 + (0xbd - 0x63) * ratio)
                b = int(0xeb + (0xf8 - 0xeb) * ratio)
                color = f"#{r:02x}{g:02x}{b:02x}"
                self.create_line(2 + i, pad_y + 1, 2 + i, pad_y + h - 1, fill=color)

            self.create_line(2, pad_y + 1, 2 + fill_w, pad_y + 1, fill="#7dd3fc", width=1)

            if self._animating:
                sx = self._shimmer_x
                sw = 50
                for i in range(sw):
                    alpha_ratio = 1.0 - abs(i - sw // 2) / (sw // 2)
                    brightness = int(alpha_ratio * 200)
                    color = f"#{brightness:02x}{brightness:02x}{min(brightness + 55, 255):02x}"
                    xx = sx - sw // 2 + i
                    if 2 <= xx <= 2 + fill_w:
                        self.create_line(xx, pad_y + 1, xx, pad_y + h - 1, fill=color)

    def _rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        pts = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.create_polygon(pts, smooth=True, **kwargs)

    def _start_shimmer(self):
        self._animating = True
        self._shimmer_loop()

    def _shimmer_loop(self):
        if not self._animating or self._value <= 0:
            self._animating = False
            return
        self._shimmer_x = (self._shimmer_x + 5) % (self._bar_width + 50)
        self._draw()
        try:
            self.after(30, self._shimmer_loop)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  Launcher Self-Update Modal Overlay
# ══════════════════════════════════════════════════════════════════════════════
class LauncherUpdateModal(ctk.CTkFrame):
    """Frosted Glass Self-Update Dialog for the Launcher."""
    def __init__(self, parent, update_info, on_update, on_cancel=None,
                 title_text=None, subtitle_text=None, btn_text=None, **kwargs):
        super().__init__(
            parent,
            fg_color="#070e1c",
            corner_radius=22,
            border_width=2,
            border_color="#38bdf8",
            **kwargs
        )
        self.update_info = update_info
        self.on_update = on_update
        self.on_cancel = on_cancel
        self._title_text = title_text
        self._subtitle_text = subtitle_text
        self._btn_text = btn_text
        self._build_ui()

    def _build_ui(self):
        new_ver = self.update_info.get("version", "1.0.1")
        self.title_lbl = ctk.CTkLabel(
            self,
            text=self._title_text or "ДОСТУПНЕ ОНОВЛЕННЯ ЛАУНЧЕРА",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#38bdf8"
        )
        self.title_lbl.pack(pady=(22, 6))

        self.sub_lbl = ctk.CTkLabel(
            self,
            text=self._subtitle_text or f"Знайдено нову версію v{new_ver}!\nБажаєте оновити лаунчер автоматично?",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#94a3b8",
            justify="center"
        )
        self.sub_lbl.pack(pady=(0, 14), padx=20)

        self.progress_bar = ctk.CTkProgressBar(self, width=320, height=8, corner_radius=4, progress_color="#38bdf8")
        self.progress_bar.set(0)

        self.status_lbl = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#38bdf8"
        )

        self.btn_row = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_row.pack(fill="x", padx=32, pady=(10, 20))

        self.btn_update = ctk.CTkButton(
            self.btn_row,
            text=self._btn_text or "Оновити зараз",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            corner_radius=10,
            command=self._start_update
        )
        self.btn_update.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.btn_cancel = ctk.CTkButton(
            self.btn_row,
            text="Пізніше",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#1e293b",
            hover_color="#334155",
            corner_radius=10,
            command=self._close
        )
        self.btn_cancel.pack(side="right", expand=True, fill="x", padx=(6, 0))

    def _start_update(self):
        self.btn_update.configure(state="disabled")
        self.btn_cancel.configure(state="disabled")
        self.progress_bar.pack(pady=(4, 6))
        self.status_lbl.pack(pady=(0, 10))
        self.status_lbl.configure(text="Підготовка до завантаження...")
        self.on_update(self.update_info, self._on_progress)

    def _on_progress(self, pct, text):
        self.after(0, lambda: self._update_ui_progress(pct, text))

    def _update_ui_progress(self, pct, text):
        self.progress_bar.set(pct)
        self.status_lbl.configure(text=text)

    def _close(self):
        if self.on_cancel:
            self.on_cancel()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
#  Supabase Auth Modal Window (Nickname + Password + Forgot Password + OTP)
# ══════════════════════════════════════════════════════════════════════════════
class SupabaseAuthModal(ctk.CTkToplevel):
    """Standalone Frosted Glass Login, Registration & Password Reset Window without Launcher behind."""
    def __init__(self, parent, on_success, initial_error=None, **kwargs):
        super().__init__(parent)
        self.parent = parent
        self.on_success = on_success
        self.mode = "login"  # "login", "register", "forgot"
        self.code_sent = False
        self.resend_timer_id = None
        self.resend_seconds_left = 0
        self.active_reset_user = ""
        self.active_reset_email = ""

        self.title("LUNARIX CLIENT · Авторизація")
        self.geometry("420x560")
        self.resizable(False, False)
        self.configure(fg_color="#070e1c")
        self.attributes("-topmost", True)

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - 420) // 2)
        y = max(0, (sh - 560) // 2)
        self.geometry(f"420x560+{x}+{y}")

        icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui(initial_error)

    def _on_close(self):
        if not getattr(self.parent, "is_authenticated", False):
            self.parent.destroy()
            sys.exit(0)
        else:
            self.destroy()

    def _build_ui(self, initial_error=None):
        # Header title
        self.title_lbl = ctk.CTkLabel(
            self,
            text="ВХІД ДО LUNARIX",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#60a5fa"
        )
        self.title_lbl.pack(pady=(20, 2))

        self.sub_lbl = ctk.CTkLabel(
            self,
            text="Увійдіть за допомогою нікнейму та паролю",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_MUTED
        )
        self.sub_lbl.pack(pady=(0, 10))

        # Inputs container
        self.form = ctk.CTkFrame(self, fg_color="transparent")
        self.form.pack(fill="x", padx=28)

        # Username / Identifier
        self.username_lbl = ctk.CTkLabel(self.form, text="Нікнейм гравця", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_WHITE)
        self.username_lbl.pack(anchor="w", pady=(0, 2))
        self.username_entry = ctk.CTkEntry(
            self.form, height=34, font=ctk.CTkFont(family="Segoe UI", size=12),
            placeholder_text="Введіть ваш нікнейм",
            fg_color="#040914", border_color=BORDER_GLASS, corner_radius=10
        )
        self.username_entry.pack(fill="x", pady=(0, 8))

        # Email Container (for register mode)
        self.email_container = ctk.CTkFrame(self.form, fg_color="transparent")
        ctk.CTkLabel(self.email_container, text="Електронна пошта (для підтвердження)", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", pady=(0, 2))
        self.email_entry = ctk.CTkEntry(
            self.email_container, height=34, font=ctk.CTkFont(family="Segoe UI", size=12),
            placeholder_text="name@example.com",
            fg_color="#040914", border_color=BORDER_GLASS, corner_radius=10
        )
        self.email_entry.pack(fill="x")

        # Password Container (with Eye toggle)
        self.pwd_container = ctk.CTkFrame(self.form, fg_color="transparent")
        self.pwd_container.pack(fill="x", pady=(0, 4))

        self.pwd_lbl = ctk.CTkLabel(self.pwd_container, text="Пароль", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_WHITE)
        self.pwd_lbl.pack(anchor="w", pady=(0, 2))

        pwd_row = ctk.CTkFrame(self.pwd_container, fg_color="transparent")
        pwd_row.pack(fill="x")
        self.pwd_entry = ctk.CTkEntry(
            pwd_row, height=34, font=ctk.CTkFont(family="Segoe UI", size=12),
            show="•", placeholder_text="Введіть пароль",
            fg_color="#040914", border_color=BORDER_GLASS, corner_radius=10
        )
        self.pwd_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.eye_btn = ctk.CTkButton(
            pwd_row, text="👁", width=36, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            fg_color="#142c54", hover_color="#1e4078", corner_radius=8,
            command=self._toggle_pwd_visibility
        )
        self.eye_btn.pack(side="right")

        # Forgot password button (Login mode)
        self.forgot_btn = ctk.CTkButton(
            self.form, text="Забули пароль? Змінити пароль",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="transparent", hover_color="#081020",
            text_color="#60a5fa", height=20,
            command=self._switch_to_forgot
        )
        self.forgot_btn.pack(anchor="e", pady=(2, 6))

        # Code Container (Step 2: OTP Code + Resend / Change email)
        self.code_container = ctk.CTkFrame(self.form, fg_color="transparent")
        ctk.CTkLabel(self.code_container, text="6-значний код з пошти", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#38bdf8").pack(anchor="w", pady=(0, 2))
        self.code_entry = ctk.CTkEntry(
            self.code_container, height=34, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            placeholder_text="Введіть 6 цифр з пошти",
            fg_color="#040914", border_color="#38bdf8", corner_radius=10
        )
        self.code_entry.pack(fill="x", pady=(0, 6))

        # New Password container for Forgot Password step 2
        self.new_pwd_container = ctk.CTkFrame(self.code_container, fg_color="transparent")
        ctk.CTkLabel(self.new_pwd_container, text="Новий пароль (від 4 символів)", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_WHITE).pack(anchor="w", pady=(0, 2))
        np_row = ctk.CTkFrame(self.new_pwd_container, fg_color="transparent")
        np_row.pack(fill="x", pady=(0, 6))
        self.new_pwd_entry = ctk.CTkEntry(
            np_row, height=34, font=ctk.CTkFont(family="Segoe UI", size=12),
            show="•", placeholder_text="Введіть новий пароль",
            fg_color="#040914", border_color=BORDER_GLASS, corner_radius=10
        )
        self.new_pwd_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.new_eye_btn = ctk.CTkButton(
            np_row, text="👁", width=36, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            fg_color="#142c54", hover_color="#1e4078", corner_radius=8,
            command=self._toggle_new_pwd_visibility
        )
        self.new_eye_btn.pack(side="right")

        # Buttons row: Change Email + Resend Code (40s timer)
        code_actions_row = ctk.CTkFrame(self.code_container, fg_color="transparent")
        code_actions_row.pack(fill="x", pady=(2, 6))

        self.btn_change_email = ctk.CTkButton(
            code_actions_row, text="✏️ Змінити email",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color="#1e293b", hover_color="#334155", text_color="#94a3b8",
            height=28, corner_radius=8, command=self._handle_change_email
        )
        self.btn_change_email.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_resend_code = ctk.CTkButton(
            code_actions_row, text="Повторити (40с)",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color="#142c54", hover_color="#1e4078", text_color="#38bdf8",
            height=28, corner_radius=8, command=self._handle_resend_code,
            state="disabled"
        )
        self.btn_resend_code.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Remember Me Checkbox
        self.remember_cb = ctk.CTkCheckBox(
            self.form, text="Запам'ятати мене", font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_MUTED, fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER
        )
        self.remember_cb.select()
        self.remember_cb.pack(anchor="w", pady=(4, 8))

        # Status Message Label
        self.msg_lbl = ctk.CTkLabel(
            self, text=initial_error or "",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#f87171" if initial_error else "#38bdf8",
            wraplength=340, justify="center"
        )
        self.msg_lbl.pack(pady=(0, 6))

        # Action Button (Login / Register / Reset)
        self.action_btn = ctk.CTkButton(
            self,
            text="УВІЙТИ",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
            height=40, corner_radius=12,
            command=self._handle_action
        )
        self.action_btn.pack(fill="x", padx=28, pady=(0, 8))

        # Mode switch button
        self.switch_btn = ctk.CTkButton(
            self,
            text="Немає акаунту? Створити новий",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="transparent", hover_color="#0e1f38",
            text_color=ACCENT_CYAN,
            command=self._toggle_mode
        )
        self.switch_btn.pack(pady=(0, 16))

    def _toggle_pwd_visibility(self):
        if self.pwd_entry.cget("show") == "•":
            self.pwd_entry.configure(show="")
            self.eye_btn.configure(fg_color="#1d4ed8")
        else:
            self.pwd_entry.configure(show="•")
            self.eye_btn.configure(fg_color="#142c54")

    def _toggle_new_pwd_visibility(self):
        if self.new_pwd_entry.cget("show") == "•":
            self.new_pwd_entry.configure(show="")
            self.new_eye_btn.configure(fg_color="#1d4ed8")
        else:
            self.new_pwd_entry.configure(show="•")
            self.new_eye_btn.configure(fg_color="#142c54")

    def _start_resend_timer(self, seconds=40):
        if self.resend_timer_id:
            try:
                self.after_cancel(self.resend_timer_id)
            except Exception:
                pass
        self.resend_seconds_left = seconds
        self._tick_resend_timer()

    def _tick_resend_timer(self):
        if not self.winfo_exists():
            return
        if self.resend_seconds_left > 0:
            self.btn_resend_code.configure(
                state="disabled",
                text=f"Повторити ({self.resend_seconds_left}с)",
                fg_color="#1e293b",
                text_color=TEXT_MUTED
            )
            self.resend_seconds_left -= 1
            self.resend_timer_id = self.after(1000, self._tick_resend_timer)
        else:
            self.btn_resend_code.configure(
                state="normal",
                text="🔄 Надіслати повторно",
                fg_color="#142c54",
                hover_color="#1e4078",
                text_color="#38bdf8"
            )
            self.resend_timer_id = None

    def _handle_change_email(self):
        self.code_sent = False
        self.code_container.pack_forget()
        self.new_pwd_container.pack_forget()
        self.email_container.pack(fill="x", pady=(0, 8))
        self.email_entry.focus()
        btn_text = "ОТРИМАТИ КОД З ПОШТИ" if self.mode == "register" else "ОТРИМАТИ КОД НА ПОШТУ"
        self.action_btn.configure(state="normal", text=btn_text)
        self.msg_lbl.configure(text="Введіть правильну адресу пошти та надішліть код", text_color="#38bdf8")

    def _handle_resend_code(self):
        if self.mode == "register":
            uname = self.username_entry.get().strip()
            email = self.email_entry.get().strip()
            if email:
                self.action_btn.configure(state="disabled", text="Повторне надсилання...")
                def resend_worker():
                    ok, code = send_email_verification_code(email, uname, action="register")
                    self.after(0, lambda: self._on_code_sent(email))
                threading.Thread(target=resend_worker, daemon=True).start()
        elif self.mode == "forgot":
            if self.active_reset_email and self.active_reset_user:
                self.action_btn.configure(state="disabled", text="Повторне надсилання...")
                def resend_forgot():
                    ok, code = send_email_verification_code(self.active_reset_email, self.active_reset_user, action="reset_password")
                    self.after(0, lambda: self._on_code_sent(self.active_reset_email))
                threading.Thread(target=resend_forgot, daemon=True).start()

    def _switch_to_forgot(self):
        self.mode = "forgot"
        self.code_sent = False
        self.msg_lbl.configure(text="")
        self.title_lbl.configure(text="ВІДНОВЛЕННЯ ПАРОЛЮ")
        self.sub_lbl.configure(text="Введіть нікнейм або прив'язану пошту")
        self.username_lbl.configure(text="Нікнейм або Email")
        self.username_entry.configure(placeholder_text="Нікнейм або електронна пошта")
        self.email_container.pack_forget()
        self.pwd_container.pack_forget()
        self.code_container.pack_forget()
        self.forgot_btn.pack_forget()
        self.remember_cb.pack_forget()
        self.action_btn.configure(state="normal", text="ОТРИМАТИ КОД НА ПОШТУ")
        self.switch_btn.configure(text="← Повернутися до входу")

    def _toggle_mode(self):
        if self.mode == "forgot":
            self.mode = "login"
        elif self.mode == "login":
            self.mode = "register"
        else:
            self.mode = "login"

        self.code_sent = False
        self.msg_lbl.configure(text="")

        if self.mode == "register":
            self.title_lbl.configure(text="РЕЄСТРАЦІЯ АКАУНТУ")
            self.sub_lbl.configure(text="Прив'язка пошти + ліміт 3 акаунти на ПК (HWID)")
            self.username_lbl.configure(text="Нікнейм гравця")
            self.username_entry.configure(placeholder_text="Введіть ваш нікнейм")
            self.email_container.pack(fill="x", pady=(0, 8))
            self.pwd_container.pack(fill="x", pady=(0, 4))
            self.code_container.pack_forget()
            self.new_pwd_container.pack_forget()
            self.forgot_btn.pack_forget()
            self.remember_cb.pack(anchor="w", pady=(4, 8))
            self.action_btn.configure(state="normal", text="ОТРИМАТИ КОД З ПОШТИ")
            self.switch_btn.configure(text="Вже маєте акаунт? Увійти")
        elif self.mode == "login":
            self.title_lbl.configure(text="ВХІД ДО LUNARIX")
            self.sub_lbl.configure(text="Увійдіть за допомогою нікнейму та паролю")
            self.username_lbl.configure(text="Нікнейм гравця")
            self.username_entry.configure(placeholder_text="Введіть ваш нікнейм")
            self.email_container.pack_forget()
            self.pwd_container.pack(fill="x", pady=(0, 4))
            self.code_container.pack_forget()
            self.new_pwd_container.pack_forget()
            self.forgot_btn.pack(anchor="e", pady=(2, 6))
            self.remember_cb.pack(anchor="w", pady=(4, 8))
            self.action_btn.configure(state="normal", text="УВІЙТИ")
            self.switch_btn.configure(text="Немає акаунту? Створити новий")

    def _on_code_sent(self, target_email):
        self.code_sent = True
        self.email_container.pack_forget()
        self.code_container.pack(fill="x", pady=(0, 8))
        self.code_entry.delete(0, "end")
        self.code_entry.focus()
        self._start_resend_timer(40)
        if self.mode == "register":
            self.action_btn.configure(state="normal", text="ПІДТВЕРДИТИ КОД ТА ЗАРЕЄСТРУВАТИСЯ")
        else:
            self.new_pwd_container.pack(fill="x", pady=(0, 6))
            self.action_btn.configure(state="normal", text="ПІДТВЕРДИТИ ТА ЗМІНИТИ ПАРОЛЬ")
        self.msg_lbl.configure(text=f"Код підтвердження надіслано на {target_email}!", text_color="#38bdf8")

    def _handle_action(self):
        uname = self.username_entry.get().strip()

        # ─── 1. FORGOT PASSWORD MODE ──────────────────────────────────────────
        if self.mode == "forgot":
            if not uname:
                self.msg_lbl.configure(text="Введіть нікнейм або електронну пошту!", text_color="#f87171")
                return

            if not self.code_sent:
                self.action_btn.configure(state="disabled", text="Пошук акаунта та надсилання коду...")
                self.msg_lbl.configure(text="")

                def forgot_send_worker():
                    user, email = find_account_by_identifier(uname)
                    if not user and not email:
                        self.after(0, lambda: self._on_fail("Акаунт із такими даними не знайдено!"))
                        return
                    target_email = email or get_account_email(user or uname)
                    if not target_email or "@" not in target_email or target_email.endswith("@lunarix.user"):
                        self.after(0, lambda: self._on_fail(f"До акаунта «{user or uname}» не знайдено прив'язаної пошти!"))
                        return
                    target_user = user or uname
                    self.active_reset_user = target_user
                    self.active_reset_email = target_email
                    ok, code = send_email_verification_code(target_email, target_user, action="reset_password")
                    self.after(0, lambda: self._on_code_sent(target_email))

                threading.Thread(target=forgot_send_worker, daemon=True).start()
                return

            # Step 2 of Forgot Password: Confirm OTP & set new password
            code = self.code_entry.get().strip()
            new_p = self.new_pwd_entry.get().strip()
            if not code or len(code) < 4:
                self.msg_lbl.configure(text="Введіть 6-значний код підтвердження з пошти!", text_color="#f87171")
                return
            if not new_p or len(new_p) < 4:
                self.msg_lbl.configure(text="Новий пароль має містити щонайменше 4 символи!", text_color="#f87171")
                return

            self.action_btn.configure(state="disabled", text="Оновлення паролю...")
            def forgot_confirm_worker():
                ok_code, msg_c = verify_email_code(self.active_reset_email, self.active_reset_user, code, action="reset_password")
                if not ok_code:
                    self.after(0, lambda: self._on_fail(msg_c))
                    return

                ok_upd, msg_u = update_user_password(self.active_reset_user, new_p)
                if ok_upd:
                    def on_reset_done():
                        messagebox.showinfo("LUNARIX", f"Пароль для «{self.active_reset_user}» успішно оновлено!\nТепер увійдіть з новим паролем.", parent=self)
                        self.mode = "login"
                        self._toggle_mode()
                        self.username_entry.delete(0, "end")
                        self.username_entry.insert(0, self.active_reset_user)
                        self.pwd_entry.delete(0, "end")
                        self.pwd_entry.insert(0, new_p)
                        self.msg_lbl.configure(text="Пароль змінено! Натисніть «Увійти»", text_color="#22c55e")
                    self.after(0, on_reset_done)
                else:
                    self.after(0, lambda: self._on_fail(str(msg_u)))

            threading.Thread(target=forgot_confirm_worker, daemon=True).start()
            return

        # ─── 2. REGISTER MODE ────────────────────────────────────────────────
        if self.mode == "register":
            pwd = self.pwd_entry.get().strip()
            if not uname or len(uname) < 3:
                self.msg_lbl.configure(text="Нікнейм має містити щонайменше 3 символи!", text_color="#f87171")
                return
            if not pwd or len(pwd) < 4:
                self.msg_lbl.configure(text="Пароль має містити щонайменше 4 символи!", text_color="#f87171")
                return

            email = self.email_entry.get().strip()
            if not email or "@" not in email or "." not in email:
                self.msg_lbl.configure(text="Введіть коректну електронну пошту!", text_color="#f87171")
                return

            # Step 1: Send verification code
            if not self.code_sent:
                self.action_btn.configure(state="disabled", text="Перевірка HWID та надсилання коду...")
                self.msg_lbl.configure(text="")

                def send_worker():
                    hwid = get_hwid()
                    count = get_hwid_registered_count(hwid)
                    if count >= 3:
                        self.after(0, lambda: self._on_fail("На цей комп'ютер (HWID) вже зареєстровано максимум 3 акаунти!"))
                        return

                    ok, code = send_email_verification_code(email, uname, action="register")
                    self.after(0, lambda: self._on_code_sent(email))

                threading.Thread(target=send_worker, daemon=True).start()
                return

            # Step 2: Confirm registration with code
            code = self.code_entry.get().strip()
            if not code or len(code) < 4:
                self.msg_lbl.configure(text="Введіть 6-значний код підтвердження з пошти!", text_color="#f87171")
                return

            self.action_btn.configure(state="disabled", text="Реєстрація...")
            def reg_worker():
                ok, res = register_with_email_and_hwid(uname, email, pwd, code)
                if ok:
                    if self.remember_cb.get():
                        save_auth(uname, password=pwd)
                    alts = load_alts()
                    if uname not in alts:
                        alts.append(uname)
                        save_alts(alts)
                    self.after(0, lambda: self.on_success(uname))
                else:
                    self.after(0, lambda: self._on_fail(str(res)))

            threading.Thread(target=reg_worker, daemon=True).start()
            return

        # ─── 3. LOGIN MODE ───────────────────────────────────────────────────
        pwd = self.pwd_entry.get().strip()
        if not uname or len(uname) < 3:
            self.msg_lbl.configure(text="Нікнейм має містити щонайменше 3 символи!", text_color="#f87171")
            return
        if not pwd or len(pwd) < 4:
            self.msg_lbl.configure(text="Пароль має містити щонайменше 4 символи!", text_color="#f87171")
            return

        self.action_btn.configure(state="disabled", text="Перевірка...")
        self.msg_lbl.configure(text="")

        def login_worker():
            success, res = sign_in_nickname(uname, pwd)
            if success:
                if self.remember_cb.get():
                    save_auth(uname, password=pwd)
                alts = load_alts()
                if uname not in alts:
                    alts.append(uname)
                    save_alts(alts)
                self.after(0, lambda: self.on_success(uname))
            else:
                self.after(0, lambda: self._on_fail(str(res)))

        threading.Thread(target=login_worker, daemon=True).start()

    def _on_fail(self, error_msg):
        if self.mode == "forgot":
            btn_text = "ПІДТВЕРДИТИ ТА ЗМІНИТИ ПАРОЛЬ" if self.code_sent else "ОТРИМАТИ КОД НА ПОШТУ"
        elif self.mode == "register":
            btn_text = "ПІДТВЕРДИТИ КОД ТА ЗАРЕЄСТРУВАТИСЯ" if self.code_sent else "ОТРИМАТИ КОД З ПОШТИ"
        else:
            btn_text = "УВІЙТИ"
        self.action_btn.configure(state="normal", text=btn_text)
        self.msg_lbl.configure(text=f"Помилка: {error_msg}", text_color="#f87171")


# ══════════════════════════════════════════════════════════════════════════════
#  Main Launcher App
# ══════════════════════════════════════════════════════════════════════════
class LunarixLauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()  # Головне вікно лаунчера сховане до перевірки авторизації

        self.config_data = load_config()
        self.lang = self.config_data.get("lang", "uk")
        self.is_busy = False

        # Supabase session state (Nickname-based)
        self.auth_user = None
        self.is_authenticated = False

        # Modrinth pagination state
        self.mr_page = 0
        self.mr_limit = 6
        self.mr_total = 0
        self.mr_query = ""

        # CurseForge mods pagination state
        self.cf_page = 0
        self.cf_limit = 6
        self.cf_total = 0
        self.cf_query = ""

        # Resource packs pagination state
        self.rp_mr_page = 0
        self.rp_mr_limit = 6
        self.rp_mr_total = 0
        self.rp_mr_query = ""

        self.rp_cf_page = 0
        self.rp_cf_limit = 6
        self.rp_cf_total = 0
        self.rp_cf_query = ""

        self.title("LUNARIX CLIENT · Fabric 1.21.11")
        win_w, win_h = 1140, 670
        self.minsize(1000, 620)
        self.configure(fg_color=BG_MAIN)
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - win_w) // 2)
        y = max(0, (sh - win_h) // 2)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

        self._setup_window_icons()

        # Video Background Setup
        self._init_video_background()

        # Build Main UI Panels
        self._build_layout()
        self._show_home()
        self._refresh_game_state()

        # Check authentication on launch (Server verification + Standalone Login window)
        self._check_initial_auth()

        # Check for launcher self-update in background
        threading.Thread(target=self._check_launcher_update_bg, daemon=True).start()

        # Check for client (game files) update in background
        threading.Thread(target=self._check_client_update_bg, daemon=True).start()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _check_launcher_update_bg(self):
        try:
            has_update, update_info = check_launcher_update(current_version=LAUNCHER_VERSION)
            if has_update and update_info:
                self.after(1000, lambda: self._show_launcher_update_modal(update_info))
        except Exception as e:
            print(f"[Launcher Update BG] Error: {e}")

    def _show_launcher_update_modal(self, update_info):
        if hasattr(self, '_update_modal') and self._update_modal and self._update_modal.winfo_exists():
            return
        self._update_modal = LauncherUpdateModal(
            self,
            update_info=update_info,
            on_update=self._execute_launcher_update,
            on_cancel=lambda: setattr(self, '_update_modal', None),
            width=420,
            height=250
        )
        self._update_modal.place(relx=0.5, rely=0.5, anchor="center")

    def _execute_launcher_update(self, update_info, progress_cb):
        def _worker():
            try:
                apply_launcher_update(update_info, progress_cb=progress_cb)
            except Exception as e:
                def _show_err():
                    messagebox.showerror("Помилка оновлення", f"Не вдалося автоматично оновити лаунчер:\n{e}")
                    if hasattr(self, '_update_modal') and self._update_modal:
                        self._update_modal.destroy()
                        self._update_modal = None
                self.after(0, _show_err)

        threading.Thread(target=_worker, daemon=True).start()

    def _check_client_update_bg(self):
        try:
            g_dir = self.config_data.get("game_dir", "")
            has_update, update_info = check_client_update(g_dir)
            if has_update and update_info:
                self.after(1000, lambda: self._show_client_update_modal(update_info))
        except Exception as e:
            print(f"[Client Update BG] Error: {e}")

    def _show_client_update_modal(self, update_info):
        if hasattr(self, '_update_modal') and self._update_modal and self._update_modal.winfo_exists():
            return
        ver = update_info.get("version", "")
        self._update_modal = LauncherUpdateModal(
            self,
            update_info=update_info,
            on_update=self._execute_client_update,
            on_cancel=lambda: setattr(self, '_update_modal', None),
            title_text="ДОСТУПНЕ ОНОВЛЕННЯ КЛІЄНТА",
            subtitle_text=f"Знайдено нову версію клієнта v{ver}!\nБажаєте оновити гру автоматично?",
            btn_text="Оновити зараз",
            width=420,
            height=250
        )
        self._update_modal.place(relx=0.5, rely=0.5, anchor="center")

    def _execute_client_update(self, update_info, progress_cb):
        def _worker():
            try:
                g_dir = self.config_data.get("game_dir", "")
                install_or_update_game(g_dir, progress_cb=progress_cb, log_cb=self._log)
                def _done():
                    if hasattr(self, '_update_modal') and self._update_modal:
                        try:
                            self._update_modal.destroy()
                        except Exception:
                            pass
                        self._update_modal = None
                    messagebox.showinfo("Готово", "Клієнт успішно оновлено!")
                    self._refresh_game_state()
                self.after(0, _done)
            except Exception as e:
                def _show_err():
                    messagebox.showerror("Помилка оновлення", f"Не вдалося оновити клієнт:\n{e}")
                    if hasattr(self, '_update_modal') and self._update_modal:
                        self._update_modal.destroy()
                        self._update_modal = None
                self.after(0, _show_err)
        threading.Thread(target=_worker, daemon=True).start()

    def _start_presence_heartbeat(self):
        if hasattr(self, '_presence_started') and self._presence_started:
            return
        self._presence_started = True

        def loop():
            while getattr(self, '_presence_started', False):
                try:
                    curr_u = self.auth_user.get("username") if self.auth_user else self.alt_switcher.get_username()
                    if curr_u:
                        if getattr(self, 'game_proc', None) is not None and self.game_proc.poll() is None:
                            update_player_presence(username=curr_u, status="in_game", activity="У грі", server="")
                        elif not self.is_busy:
                            update_player_presence(username=curr_u, status="online", activity="У лаунчері", server="")
                except Exception:
                    pass
                for _ in range(40):
                    if not getattr(self, '_presence_started', False):
                        break
                    time.sleep(1)

        threading.Thread(target=loop, daemon=True).start()

    def _on_close(self):
        self._presence_started = False
        try:
            curr_u = self.auth_user.get("username") if self.auth_user else self.alt_switcher.get_username()
            if curr_u:
                update_player_presence(username=curr_u, status="offline", activity="Офлайн", server="")
        except Exception:
            pass
        self._video_running = False
        if hasattr(self, '_video_cap') and self._video_cap:
            try:
                self._video_cap.release()
            except Exception:
                pass
        self.destroy()

    def tr(self, key, **kwargs):
        return t(self.lang, key, **kwargs)

    def _setup_window_icons(self):
        icon_ico = os.path.join(BASE_DIR, "assets", "icon.ico")
        icon_png = os.path.join(BASE_DIR, "assets", "icon.png")
        if os.path.exists(icon_ico):
            try:
                self.iconbitmap(icon_ico)
            except Exception:
                pass
        if os.path.exists(icon_png):
            try:
                self._photo_icon = tk.PhotoImage(file=icon_png)
                self.iconphoto(True, self._photo_icon)
            except Exception:
                pass

    # ──────────────────────────────────────────────────────────────────────────
    #  Full-Screen Video Loop Background
    # ──────────────────────────────────────────────────────────────────────────
    def _init_video_background(self):
        self._bg_label = tk.Label(self, bd=0, bg=BG_MAIN)
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        self._video_running = False
        self._video_cap = None
        self._current_photo = None
        self._latest_frame_img = None
        self._has_new_frame = False
        self._frame_lock = threading.Lock()
        self._video_target_size = (1060, 640)
        self._video_thread = None
        self._last_bg_size = (0, 0)

        self.bind("<Configure>", self._on_window_resize)

        if self.config_data.get("animated_background", False):
            self._start_video_playback()
        else:
            self._draw_fallback_gradient()

    def _start_video_playback(self):
        if self._video_running:
            return
        target_file = None
        if os.path.exists(VIDEO_PATH):
            target_file = VIDEO_PATH
        elif os.path.exists(GIF_PATH):
            target_file = GIF_PATH

        if CV2_AVAILABLE and target_file and os.path.exists(target_file):
            try:
                self._video_cap = cv2.VideoCapture(target_file)
                self._video_running = True
                self._video_thread = threading.Thread(target=self._video_worker_loop, daemon=True)
                self._video_thread.start()
                self.after(50, self._render_video_frame)
            except Exception as e:
                print("Failed to open background video:", e)
                self._draw_fallback_gradient()
        else:
            self._draw_fallback_gradient()

    def _stop_video_playback(self):
        self._video_running = False
        if self._video_cap is not None:
            try:
                self._video_cap.release()
            except Exception:
                pass
            self._video_cap = None
        self._draw_fallback_gradient()

    def _on_window_resize(self, event):
        if event.widget is self:
            w, h = event.width, event.height
            if w >= 200 and h >= 200 and (w, h) != self._last_bg_size:
                self._last_bg_size = (w, h)
                self._video_target_size = (w, h)
                if not self.config_data.get("animated_background", False):
                    self._draw_fallback_gradient()

    def _video_worker_loop(self):
        target_fps = 25
        frame_time = 1.0 / target_fps
        while self._video_running and self._video_cap is not None:
            t0 = time.time()
            if not self.config_data.get("animated_background", False):
                time.sleep(0.2)
                continue

            w, h = self._video_target_size
            if w < 10 or h < 10:
                w, h = 1060, 640

            ret, frame = self._video_cap.read()
            if not ret:
                self._video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._video_cap.read()
                if not ret:
                    time.sleep(0.05)
                    continue

            try:
                resized = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)
                rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

                # Frosted glass background:
                small = cv2.resize(rgb, (max(1, w // 4), max(1, h // 4)))
                small_blur = cv2.GaussianBlur(small, (7, 7), 0)
                blur = cv2.resize(small_blur, (w, h), interpolation=cv2.INTER_LINEAR)

                glass_tinted = (blur * 0.40 + np.array([8, 16, 32])).clip(0, 255).astype(np.float32)
                clear_video = (rgb * 0.88).clip(0, 255).astype(np.float32)

                # Rear tiles are ~65% transparent: mostly the sharp background
                # video with a light frosted-glass tint on top.
                panel = (clear_video * 0.68 + glass_tinted * 0.32).clip(0, 255).astype(np.uint8)

                mask = np.zeros((h, w, 1), dtype=np.float32)
                mask[14:max(15, h - 14), 14:min(w, 250)] = 1.0
                mask[14:max(15, h - 14), 260:max(261, w - 14)] = 1.0

                composite = np.where(mask > 0.5, panel, clear_video.astype(np.uint8))
                img = Image.fromarray(composite)
                with self._frame_lock:
                    self._latest_frame_img = img
                    self._has_new_frame = True
            except Exception:
                pass

            dt = time.time() - t0
            to_sleep = frame_time - dt
            if to_sleep > 0.001:
                time.sleep(to_sleep)

    def _render_video_frame(self):
        if not self._video_running:
            return

        w = self.winfo_width()
        h = self.winfo_height()
        if w >= 10 and h >= 10:
            self._video_target_size = (w, h)

        if not self.config_data.get("animated_background", False):
            if not getattr(self, "_showing_static_bg", False):
                self._draw_fallback_gradient()
                self._showing_static_bg = True
            self.after(200, self._render_video_frame)
            return

        self._showing_static_bg = False
        if self._has_new_frame and self._latest_frame_img is not None:
            with self._frame_lock:
                img = self._latest_frame_img
                self._has_new_frame = False
            try:
                self._current_photo = ImageTk.PhotoImage(img)
                self._bg_label.configure(image=self._current_photo)
            except Exception:
                pass

        self.after(33, self._render_video_frame)

    def _draw_fallback_gradient(self):
        w = max(self.winfo_width(), 1060)
        h = max(self.winfo_height(), 640)
        try:
            y = np.linspace(0, 1, h)[:, None]
            x = np.linspace(0, 1, w)[None, :]
            r = 6 + 6 * y
            g = 9 + 15 * y
            b = 19 + 29 * y

            dist1 = np.sqrt((x - 0.75)**2 + (y - 0.25)**2)
            glow1 = np.clip(1.0 - dist1 / 0.6, 0, 1)**2 * 25.0

            dist2 = np.sqrt((x - 0.2)**2 + (y - 0.85)**2)
            glow2 = np.clip(1.0 - dist2 / 0.5, 0, 1)**2 * 18.0

            rgb = np.zeros((h, w, 3), dtype=np.uint8)
            rgb[..., 0] = np.clip(r + glow1 * 0.2, 0, 255).astype(np.uint8)
            rgb[..., 1] = np.clip(g + glow1 * 0.6 + glow2 * 0.4, 0, 255).astype(np.uint8)
            rgb[..., 2] = np.clip(b + glow1 * 1.0 + glow2 * 0.8, 0, 255).astype(np.uint8)

            img = Image.fromarray(rgb)
        except Exception:
            img = Image.new("RGB", (w, h), (7, 12, 24))
            draw = ImageDraw.Draw(img)
            for i in range(h):
                ratio = i / h
                draw.line([(0, i), (w, i)], fill=(int(7 + 10 * ratio), int(12 + 16 * ratio), int(24 + 28 * ratio)))

        self._current_photo = ImageTk.PhotoImage(img)
        self._bg_label.configure(image=self._current_photo)

    # ──────────────────────────────────────────────────────────────────────────
    #  Supabase Auth Modal & Protection (Pure Nickname)
    # ──────────────────────────────────────────────────────────────────────────
    def _check_initial_auth(self):
        saved = load_auth()
        if not saved or not saved.get("username"):
            self.is_authenticated = False
            self.auth_user = None
            self._show_auth_modal()
            return

        uname = saved.get("username")
        pwd_hash = saved.get("password_hash")

        def check_server():
            valid, info = verify_account_valid(uname, pwd_hash)
            if valid:
                def on_valid():
                    self.auth_user = saved
                    self.is_authenticated = True
                    self._apply_authenticated_user()
                    self._refresh_game_state()
                    self._refresh_profile_view()
                    self._start_presence_heartbeat()
                    self.deiconify()  # Відображаємо вікно лаунчера
                self.after(0, on_valid)
            else:
                def on_invalid():
                    clear_auth()
                    self.auth_user = None
                    self.is_authenticated = False
                    err_msg = str(info)
                    self._show_auth_modal(initial_error=err_msg)
                self.after(0, on_invalid)

        threading.Thread(target=check_server, daemon=True).start()

    def _show_auth_modal(self, initial_error=None):
        if hasattr(self, '_auth_modal') and self._auth_modal and self._auth_modal.winfo_exists():
            try:
                self._auth_modal.lift()
                self._auth_modal.focus_force()
            except Exception:
                pass
            return
        self.withdraw()  # Лаунчер схований, тільки вікно логіну
        self._auth_modal = SupabaseAuthModal(self, on_success=self._on_auth_success, initial_error=initial_error)

    def _on_auth_success(self, username):
        saved = load_auth() or {"username": username}
        self.auth_user = saved
        self.is_authenticated = True
        if hasattr(self, '_auth_modal') and self._auth_modal:
            try:
                self._auth_modal.destroy()
            except Exception:
                pass
            self._auth_modal = None

        if username:
            self.alt_switcher.set_username(username)
            self.config_data["username"] = username
            if not (self.config_data.get("display_name") or "").strip():
                self.config_data["display_name"] = username
            save_config(self.config_data)

        self._apply_authenticated_user()
        self._refresh_game_state()
        self._refresh_profile_view()
        self._start_presence_heartbeat()
        self.deiconify()  # Відкриваємо лаунчер
        messagebox.showinfo("LUNARIX", f"Успішний вхід! Вітаємо, {username}!")

    def _apply_authenticated_user(self):
        if self.auth_user:
            uname = self.auth_user.get("username", "Player")
            self.user_session_lbl.configure(text=uname, text_color="#f8fafc")
            self.btn_auth_logout.configure(text="Вийти", fg_color="#142c54", hover_color="#1d3f78")
            if hasattr(self, 'user_dot'):
                self.user_dot.configure(text_color="#22c55e")
        else:
            self.user_session_lbl.configure(text="Гість", text_color=TEXT_MUTED)
            self.btn_auth_logout.configure(text="Увійти в акаунт", fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER)
            if hasattr(self, 'user_dot'):
                self.user_dot.configure(text_color="#f59e0b")

    def _on_logout(self):
        clear_auth()
        self.auth_user = None
        self.is_authenticated = False
        self.user_session_lbl.configure(text="Гість", text_color=TEXT_MUTED)
        self.btn_auth_logout.configure(text="Увійти в акаунт", fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER)
        if hasattr(self, 'user_dot'):
            self.user_dot.configure(text_color="#f59e0b")
        self._refresh_game_state()
        self.withdraw()  # Лаунчер ховається, відкривається тільки вікно логіну
        self._show_auth_modal()

    # ──────────────────────────────────────────────────────────────────────────
    #  Layout: Sidebar + Main Content (Glassmorphic)
    # ──────────────────────────────────────────────────────────────────────────
    def _build_layout(self):
        # 1. Glass Sidebar Panel (left) - Expanded to 260px with pack_propagate(False)
        self.sidebar = ctk.CTkFrame(
            self,
            width=260,
            corner_radius=20,
            fg_color="#070e1c",
            border_width=1,
            border_color="#1e3a5f"
        )
        self.sidebar.pack_propagate(False)
        self.sidebar.place(x=14, y=14, relheight=0.95)

        # Brand header
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=(18, 14))

        icon_png = os.path.join(BASE_DIR, "assets", "icon.png")
        if os.path.exists(icon_png):
            try:
                img = Image.open(icon_png)
                self.logo_ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(34, 34))
                ctk.CTkLabel(brand, image=self.logo_ctk_img, text="").pack(side="left", padx=(0, 10))
            except Exception:
                pass

        b_text = ctk.CTkFrame(brand, fg_color="transparent")
        b_text.pack(side="left")
        ctk.CTkLabel(
            b_text, text="LUNARIX",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#60a5fa"
        ).pack(anchor="w")
        ctk.CTkLabel(
            b_text, text="CLIENT · 1.21.11",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color="#38bdf8"
        ).pack(anchor="w")

        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color="#1e3a5f")
        sep.pack(fill="x", padx=14, pady=(0, 10))

        # Load modern vector tab icons
        self.tab_icons = {}
        icons_dir = os.path.join(BASE_DIR, "assets", "tab_icons")
        for t_id in ["home", "profile", "alts", "chat", "configs", "localcfg", "resourcepacks", "friends", "mods", "changelog", "settings"]:
            act_path = os.path.join(icons_dir, f"{t_id}_active.png")
            inact_path = os.path.join(icons_dir, f"{t_id}_inactive.png")
            if os.path.exists(act_path) and os.path.exists(inact_path):
                act_img = Image.open(act_path)
                inact_img = Image.open(inact_path)
                self.tab_icons[t_id] = {
                    "active": ctk.CTkImage(light_image=act_img, dark_image=act_img, size=(18, 18)),
                    "inactive": ctk.CTkImage(light_image=inact_img, dark_image=inact_img, size=(18, 18))
                }

        # Navigation Buttons inside Scrollable Frame with Slider (Scrollbar)
        self.nav_btns = {}
        self.tab_defs = [
            ("home",          "tab_home",          self._show_home),
            ("profile",       "tab_profile",       self._show_profile),
            ("alts",          "tab_alts",          self._show_alts),
            ("chat",          "tab_chat",          self._show_chat),
            ("configs",       "tab_configs",       self._show_configs),
            ("localcfg",      "tab_localcfg",      self._show_localcfg),
            ("resourcepacks", "tab_resourcepacks", self._show_resourcepacks),
            ("friends",       "tab_friends",       self._show_friends),
            ("mods",          "tab_mods",          self._show_mods),
            ("changelog",     "tab_changelog",     self._show_changelog),
            ("settings",      "tab_settings",      self._show_settings),
        ]

        self.sidebar_nav_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.sidebar_nav_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        for tab_id, lang_key, cmd in self.tab_defs:
            icon_pair = self.tab_icons.get(tab_id)
            init_icon = icon_pair["inactive"] if icon_pair else None
            btn = ctk.CTkButton(
                self.sidebar_nav_scroll,
                text="  " + self.tr(lang_key),
                image=init_icon,
                compound="left",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                fg_color="transparent",
                text_color=TEXT_MUTED,
                hover_color="#122544",
                anchor="w",
                height=40,
                corner_radius=10,
                command=cmd
            )
            btn.pack(fill="x", padx=6, pady=2)
            self.nav_btns[tab_id] = btn

        # Bottom Supabase Account Info in Sidebar
        auth_box = ctk.CTkFrame(
            self.sidebar,
            fg_color="#0b162c",
            corner_radius=14,
            border_width=1,
            border_color="#1e3a5f"
        )
        auth_box.pack(side="bottom", fill="x", padx=10, pady=12)

        status_row = ctk.CTkFrame(auth_box, fg_color="transparent")
        status_row.pack(fill="x", padx=10, pady=(8, 2))

        self.user_dot = ctk.CTkLabel(status_row, text="●", font=ctk.CTkFont(size=10), text_color="#22c55e" if self.is_authenticated else "#f59e0b", width=12)
        self.user_dot.pack(side="left", padx=(0, 4))

        display_name = self.auth_user.get("username", "Гість") if self.is_authenticated else "Гість"
        self.user_session_lbl = ctk.CTkLabel(
            status_row, text=display_name,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#f8fafc" if self.is_authenticated else TEXT_MUTED
        )
        self.user_session_lbl.pack(side="left")

        self.btn_auth_logout = ctk.CTkButton(
            auth_box,
            text="Вийти" if self.is_authenticated else "Увійти в акаунт",
            height=26,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#142c54" if self.is_authenticated else ACCENT_BLUE,
            hover_color="#1d3f78" if self.is_authenticated else ACCENT_BLUE_HOVER,
            corner_radius=8,
            command=lambda: self._on_logout() if self.is_authenticated else self._show_auth_modal()
        )
        self.btn_auth_logout.pack(fill="x", padx=10, pady=(4, 8))

        # 2. Main Content Glass Container (right)
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.place(x=286, y=14, relwidth=0.72, relheight=0.95)
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

        self._init_home_view()
        self._init_profile_view()
        self._init_alts_view()
        self._init_chat_view()
        self._init_configs_view()
        self._init_localcfg_view()
        self._init_resourcepacks_view()
        self._init_friends_view()
        self._init_mods_view()
        self._init_changelog_view()
        self._init_settings_view()

    def _select_tab(self, tab_name):
        for t_id, btn in self.nav_btns.items():
            icon_pair = self.tab_icons.get(t_id)
            if t_id == tab_name:
                btn.configure(
                    fg_color="#142c54",
                    text_color="#60a5fa",
                    image=icon_pair["active"] if icon_pair else None,
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    border_width=1,
                    border_color="#2563eb"
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=TEXT_MUTED,
                    image=icon_pair["inactive"] if icon_pair else None,
                    font=ctk.CTkFont(family="Segoe UI", size=13),
                    border_width=0
                )

    # ══════════════════════════════════════════════════════════════════════════
    #  1. HOME VIEW
    # ══════════════════════════════════════════════════════════════════════════
    def _init_home_view(self):
        self.home_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")

        # ── TOP BAR (Banner Left + Alt Switcher Right) ──────────────────────────
        top_bar = ctk.CTkFrame(
            self.home_frame,
            fg_color="transparent",
            corner_radius=20,
            border_width=1,
            border_color="#38bdf8"
        )
        top_bar.pack(fill="x", pady=(0, 14))

        t_in = ctk.CTkFrame(top_bar, fg_color="transparent")
        t_in.pack(fill="x", padx=20, pady=12)

        h_left = ctk.CTkFrame(t_in, fg_color="transparent")
        h_left.pack(side="left")

        self.hero_t_lbl = ctk.CTkLabel(
            h_left, text="LUNARIX CLIENT",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#60a5fa"
        )
        self.hero_t_lbl.pack(anchor="w")

        self.hero_sub_lbl = ctk.CTkLabel(
            h_left, text="Minecraft 1.21.11 · Fabric Loader",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_MUTED
        )
        self.hero_sub_lbl.pack(anchor="w", pady=(2, 0))

        h_right = ctk.CTkFrame(t_in, fg_color="transparent")
        h_right.pack(side="right")

        v_badge = ctk.CTkFrame(h_right, fg_color="transparent", corner_radius=10, border_width=1, border_color="#38bdf8")
        v_badge.pack(side="right", padx=(10, 0))
        ctk.CTkLabel(
            v_badge, text=f"v{LAUNCHER_VERSION}",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=ACCENT_CYAN
        ).pack(padx=12, pady=6)

        self.alt_switcher = AltSwitcherWidget(
            h_right,
            initial_username=self.config_data.get("username", "Player"),
            on_change=self._on_alt_changed
        )
        self.alt_switcher.pack(side="right")

        # ── CENTER ACTION CARD (Glassmorphism Deck) ────────────────────────────
        act_card = ctk.CTkFrame(
            self.home_frame,
            fg_color="transparent",
            corner_radius=22,
            border_width=1,
            border_color="#38bdf8"
        )
        act_card.pack(fill="both", expand=True)

        center_deck = ctk.CTkFrame(act_card, fg_color="transparent")
        center_deck.pack(expand=True, pady=10)

        # Big Play Button
        self.home_main_btn = ctk.CTkButton(
            center_deck,
            text=self.tr("btn_play"),
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            height=58,
            width=360,
            corner_radius=14,
            command=self._on_home_main_btn_click
        )
        self.home_main_btn.pack(pady=(0, 16))

        # Progress bar container
        prog_container = ctk.CTkFrame(center_deck, fg_color="transparent", width=360)
        prog_container.pack(pady=(0, 4))
        prog_container.pack_propagate(False)

        # Status text row
        self.status_row = ctk.CTkFrame(prog_container, fg_color="transparent")
        self.status_row.pack(fill="x", pady=(0, 4))

        self.status_stage_lbl = ctk.CTkLabel(
            self.status_row, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_MUTED, anchor="w"
        )
        self.status_stage_lbl.pack(side="left")

        self.status_pct_lbl = ctk.CTkLabel(
            self.status_row, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=ACCENT_CYAN, anchor="e"
        )
        self.status_pct_lbl.pack(side="right")

        # Shimmer Progress Bar
        self.glass_progress = GlassProgressBar(prog_container, width=360)
        self.glass_progress.pack()

        class _ProgressShim:
            def __init__(s): pass
            def set(s, v):
                try:
                    self.glass_progress.set(v)
                except Exception:
                    pass
        self.progress_bar = _ProgressShim()

    def _on_alt_changed(self, username):
        self.config_data["username"] = username
        save_config(self.config_data)

    # ══════════════════════════════════════════════════════════════════════════
    #  1.5 ALTS VIEW (Dedicated Alt Manager)
    # ══════════════════════════════════════════════════════════════════════════
    def _init_alts_view(self):
        self.alts_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")

        # Header banner
        header = ctk.CTkFrame(self.alts_frame, fg_color="transparent", corner_radius=16, border_width=1, border_color="#1e3a5f")
        header.pack(fill="x", pady=(0, 10))

        h_left = ctk.CTkFrame(header, fg_color="transparent")
        h_left.pack(side="left", padx=16, pady=10)
        ctk.CTkLabel(
            h_left, text="Альт Менеджер (Керування акаунтами)",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#60a5fa"
        ).pack(anchor="w")
        ctk.CTkLabel(
            h_left, text="Керування акаунтами та швидке перемикання для клієнта і гри",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_MUTED
        ).pack(anchor="w")

        h_right = ctk.CTkFrame(header, fg_color="transparent")
        h_right.pack(side="right", padx=16, pady=10)

        btn_add = ctk.CTkButton(
            h_right, text="➕ Додати акаунт",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=10,
            command=self._show_add_alt_modal
        )
        btn_add.pack(side="right")

        # Active Account Status Card
        self.alts_active_card = ctk.CTkFrame(self.alts_frame, fg_color="#0b162c", corner_radius=16, border_width=1, border_color="#2563eb")
        self.alts_active_card.pack(fill="x", pady=(0, 10))

        self.alts_active_inner = ctk.CTkFrame(self.alts_active_card, fg_color="transparent")
        self.alts_active_inner.pack(fill="x", padx=16, pady=12)

        self.alts_active_avatar_lbl = ctk.CTkLabel(self.alts_active_inner, text="", width=48, height=48)
        self.alts_active_avatar_lbl.pack(side="left", padx=(0, 14))

        act_col = ctk.CTkFrame(self.alts_active_inner, fg_color="transparent")
        act_col.pack(side="left", fill="both", expand=True)

        self.alts_active_title_lbl = ctk.CTkLabel(
            act_col, text="Активний акаунт: Player",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#f8fafc"
        )
        self.alts_active_title_lbl.pack(anchor="w")

        self.alts_active_desc_lbl = ctk.CTkLabel(
            act_col, text="Цей акаунт зараз активний у софті Lunarix Client та готовий до запуску гри.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#38bdf8"
        )
        self.alts_active_desc_lbl.pack(anchor="w", pady=(2, 0))

        # Alts list scrollable frame
        self.alts_scroll = ctk.CTkScrollableFrame(self.alts_frame, fg_color="transparent")
        self.alts_scroll.pack(fill="both", expand=True)

    def _load_alts_view(self):
        for w in self.alts_scroll.winfo_children():
            w.destroy()

        current_username = self.config_data.get("username", "Player")
        self.alts_active_title_lbl.configure(text=f"Активний акаунт: {current_username}")

        def _load_act_avatar():
            img = fetch_skin_head(current_username, size=48)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(48, 48))
            try:
                self.after(0, lambda: self.alts_active_avatar_lbl.configure(image=ctk_img))
            except Exception:
                pass
        threading.Thread(target=_load_act_avatar, daemon=True).start()

        alts = load_alts()
        if not alts:
            alts = [current_username]
            save_alts(alts)

        for alt_name in alts:
            is_cur = (alt_name == current_username)
            card = ctk.CTkFrame(
                self.alts_scroll,
                fg_color="#0e1f38" if is_cur else "#0b162c",
                corner_radius=14,
                border_width=1,
                border_color="#38bdf8" if is_cur else "#1e3a5f"
            )
            card.pack(fill="x", pady=4, padx=4)

            c_in = ctk.CTkFrame(card, fg_color="transparent")
            c_in.pack(fill="x", padx=14, pady=10)

            av_lbl = ctk.CTkLabel(c_in, text="", width=36, height=36)
            av_lbl.pack(side="left", padx=(0, 12))

            def _load_item_head(u_name=alt_name, target_lbl=av_lbl):
                img = fetch_skin_head(u_name, size=36)
                c_img = ctk.CTkImage(light_image=img, dark_image=img, size=(36, 36))
                try:
                    self.after(0, lambda: target_lbl.configure(image=c_img))
                except Exception:
                    pass
            threading.Thread(target=_load_item_head, daemon=True).start()

            col = ctk.CTkFrame(c_in, fg_color="transparent")
            col.pack(side="left", fill="both", expand=True)

            ctk.CTkLabel(
                col, text=alt_name,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#60a5fa" if is_cur else "#f8fafc"
            ).pack(anchor="w")

            sub_txt = "🟢 Поточний вибраний акаунт" if is_cur else "Offline / Збережений акаунт"
            ctk.CTkLabel(
                col, text=sub_txt,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color="#38bdf8" if is_cur else TEXT_MUTED
            ).pack(anchor="w")

            btn_row = ctk.CTkFrame(c_in, fg_color="transparent")
            btn_row.pack(side="right")

            if not is_cur:
                ctk.CTkButton(
                    btn_row, text="✔ Обрати",
                    height=30, width=90,
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=8,
                    command=lambda u=alt_name: self._switch_alt_account(u)
                ).pack(side="left", padx=(0, 6))

            if len(alts) > 1 and not is_cur:
                ctk.CTkButton(
                    btn_row, text="🗑",
                    height=30, width=36,
                    font=ctk.CTkFont(size=12),
                    fg_color="#1e293b", hover_color="#ef4444", text_color="#f87171", corner_radius=8,
                    command=lambda u=alt_name: self._delete_alt_account(u)
                ).pack(side="left")

    def _switch_alt_account(self, username):
        self.config_data["username"] = username
        save_config(self.config_data)
        self.alt_switcher.set_username(username)
        self._refresh_game_state()
        self._load_alts_view()
        messagebox.showinfo("Альт Менеджер", f"Акаунт «{username}» успішно обрано для запуску гри!")

    def _delete_alt_account(self, username):
        alts = load_alts()
        if username in alts:
            alts.remove(username)
            save_alts(alts)
            self._load_alts_view()

    def _show_add_alt_modal(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Додати акаунт")
        popup.geometry("380x200")
        popup.configure(fg_color="#070e1c")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)

        self.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 380) // 2
        py = self.winfo_y() + (self.winfo_height() - 200) // 2
        popup.geometry(f"+{px}+{py}")

        ctk.CTkLabel(popup, text="ДОДАТИ НОВИЙ АКАУНТ", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#60a5fa").pack(pady=(18, 4))
        ctk.CTkLabel(popup, text="Введіть нікнейм для гри та синхронізації", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED).pack(pady=(0, 12))

        entry = ctk.CTkEntry(popup, height=36, font=ctk.CTkFont(family="Segoe UI", size=12), placeholder_text="Нікнейм гравця", corner_radius=10, fg_color="#040914", border_color="#1e3a5f")
        entry.pack(fill="x", padx=24, pady=(0, 14))
        entry.focus()

        def _add():
            name = entry.get().strip()
            if not name or len(name) < 3:
                messagebox.showwarning("Помилка", "Нікнейм має містити щонайменше 3 символи!", parent=popup)
                return
            alts = load_alts()
            if name not in alts:
                alts.append(name)
                save_alts(alts)
            popup.destroy()
            self._load_alts_view()

        entry.bind("<Return>", lambda e: _add())
        ctk.CTkButton(popup, text="ДОДАТИ", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, height=36, corner_radius=10, command=_add).pack(fill="x", padx=24)

    # ══════════════════════════════════════════════════════════════════════════
    #  1.6 GLOBAL CHAT VIEW
    # ══════════════════════════════════════════════════════════════════════════
    def _init_chat_view(self):
        self.chat_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")

        top = ctk.CTkFrame(self.chat_frame, fg_color="transparent", corner_radius=16, border_width=1, border_color="#1e3a5f")
        top.pack(fill="x", pady=(0, 10))

        t_left = ctk.CTkFrame(top, fg_color="transparent")
        t_left.pack(side="left", padx=16, pady=10)
        ctk.CTkLabel(
            t_left, text="Глобальний Чат Lunarix",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#60a5fa"
        ).pack(anchor="w")
        ctk.CTkLabel(
            t_left, text="Онлайн спілкування між усіма користувачами Lunarix Client",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_MUTED
        ).pack(anchor="w")

        btn_refresh = ctk.CTkButton(
            top, text="🔄 Оновити",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#0b162c", hover_color="#162e54", corner_radius=10,
            border_width=1, border_color="#1e3a5f", width=100, height=34,
            command=self._load_chat_view
        )
        btn_refresh.pack(side="right", padx=16, pady=10)

        self.chat_scroll = ctk.CTkScrollableFrame(self.chat_frame, fg_color="transparent")
        self.chat_scroll.pack(fill="both", expand=True, pady=(0, 10))

        bar = ctk.CTkFrame(self.chat_frame, fg_color="#0b162c", corner_radius=14, border_width=1, border_color="#1e3a5f")
        bar.pack(fill="x", pady=(0, 2))

        self.chat_entry = ctk.CTkEntry(
            bar, height=40, font=ctk.CTkFont(family="Segoe UI", size=12),
            placeholder_text="Напишіть повідомлення в глобальний чат... (Enter для надсилання)",
            fg_color="#040914", border_color="#1e3a5f", corner_radius=10
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(10, 8), pady=8)
        self.chat_entry.bind("<Return>", lambda e: self._on_send_chat_message())

        self.btn_chat_send = ctk.CTkButton(
            bar, text="Надіслати ➤",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=10,
            height=40, width=120,
            command=self._on_send_chat_message
        )
        self.btn_chat_send.pack(side="right", padx=(0, 10), pady=8)

        self._chat_polling_job = None

    def _load_chat_view(self):
        loading = ctk.CTkLabel(self.chat_scroll, text="Завантаження чату...", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=TEXT_MUTED)
        loading.pack(pady=20)

        def worker():
            ok, msgs = fetch_global_chat_messages(limit=50)
            self.after(0, lambda: self._render_chat_messages(ok, msgs, loading))
        threading.Thread(target=worker, daemon=True).start()

    def _render_chat_messages(self, ok, msgs, loading_widget):
        try:
            loading_widget.destroy()
        except Exception:
            pass

        for w in self.chat_scroll.winfo_children():
            w.destroy()

        if not ok or not msgs:
            ctk.CTkLabel(self.chat_scroll, text="Повідомлень поки що немає. Будьте першим!", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=TEXT_MUTED).pack(pady=40)
            return

        my_user = (self.auth_user or {}).get("username") or self.alt_switcher.get_username()

        for m in msgs:
            author = m.get("author", "Player")
            content = m.get("content", {})
            text = content.get("message") or m.get("description", "")
            is_me = (author.lower() == my_user.lower())

            card = ctk.CTkFrame(
                self.chat_scroll,
                fg_color="#0e1f38" if is_me else "#0b162c",
                corner_radius=12,
                border_width=1,
                border_color="#2563eb" if is_me else "#142442"
            )
            card.pack(fill="x", pady=3, padx=4)

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=8)

            head_lbl = ctk.CTkLabel(row, text="", width=28, height=28)
            head_lbl.pack(side="left", padx=(0, 10))

            def _load_chat_head(u=author, lbl=head_lbl):
                img = fetch_skin_head(u, size=28)
                c_img = ctk.CTkImage(light_image=img, dark_image=img, size=(28, 28))
                try:
                    self.after(0, lambda: lbl.configure(image=c_img))
                except Exception:
                    pass
            threading.Thread(target=_load_chat_head, daemon=True).start()

            body = ctk.CTkFrame(row, fg_color="transparent")
            body.pack(side="left", fill="both", expand=True)

            meta_row = ctk.CTkFrame(body, fg_color="transparent")
            meta_row.pack(fill="x")

            auth_color = "#38bdf8" if is_me else "#60a5fa"
            auth_suffix = " (Ви)" if is_me else ""
            ctk.CTkLabel(
                meta_row, text=f"{author}{auth_suffix}",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=auth_color
            ).pack(side="left")

            t_str = m.get("created_at", "")[:16].replace("T", " ")
            ctk.CTkLabel(
                meta_row, text=t_str,
                font=ctk.CTkFont(family="Segoe UI", size=9),
                text_color=TEXT_MUTED
            ).pack(side="right")

            ctk.CTkLabel(
                body, text=text,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color="#f8fafc", wraplength=600, justify="left"
            ).pack(anchor="w", pady=(2, 0))

    def _on_send_chat_message(self):
        msg = self.chat_entry.get().strip()
        if not msg:
            return
        my_user = (self.auth_user or {}).get("username") or self.alt_switcher.get_username()
        self.chat_entry.delete(0, "end")
        self.btn_chat_send.configure(state="disabled", text="...")

        def worker():
            send_global_chat_message(my_user, msg)
            self.after(0, lambda: self.btn_chat_send.configure(state="normal", text="Надіслати ➤"))
            self.after(0, self._load_chat_view)
        threading.Thread(target=worker, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    #  2. MODS VIEW
    # ══════════════════════════════════════════════════════════════════════════
    def _init_mods_view(self):
        self.mods_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")

        self.mods_locked_card = ctk.CTkFrame(
            self.mods_frame, fg_color="transparent",
            corner_radius=20, border_width=1, border_color="#38bdf8"
        )
        l_in = ctk.CTkFrame(self.mods_locked_card, fg_color="transparent")
        l_in.pack(expand=True, padx=30, pady=40)

        ctk.CTkLabel(l_in, text="🔒", font=ctk.CTkFont(size=36)).pack(pady=(0, 6))
        self.lock_title_lbl = ctk.CTkLabel(
            l_in, text=self.tr("mods_locked_title"),
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=TEXT_WHITE
        )
        self.lock_title_lbl.pack(pady=(0, 6))

        self.lock_desc_lbl = ctk.CTkLabel(
            l_in, text=self.tr("mods_locked_desc"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_MUTED, justify="center"
        )
        self.lock_desc_lbl.pack(pady=(0, 16))

        self.lock_btn = ctk.CTkButton(
            l_in, text=self.tr("btn_go_home"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
            height=36, corner_radius=12, command=self._show_home
        )
        self.lock_btn.pack()

        self.mods_unlocked_container = ctk.CTkFrame(self.mods_frame, fg_color="transparent")

        self.mods_tabview = ctk.CTkTabview(
            self.mods_unlocked_container,
            fg_color="#081020",
            segmented_button_selected_color=ACCENT_BLUE,
            segmented_button_selected_hover_color=ACCENT_BLUE_HOVER,
            segmented_button_unselected_color=BG_GLASS_INNER,
            corner_radius=18
        )
        self.mods_tabview.pack(fill="both", expand=True)

        self.tab_installed = self.mods_tabview.add(self.tr("subtab_installed"))
        self.tab_modrinth = self.mods_tabview.add(self.tr("subtab_modrinth"))
        self.tab_curseforge = self.mods_tabview.add("CurseForge")

        inst_top = ctk.CTkFrame(self.tab_installed, fg_color="transparent")
        inst_top.pack(fill="x", padx=10, pady=(4, 8))
        self.lbl_inst_title = ctk.CTkLabel(
            inst_top, text="mods/",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        )
        self.lbl_inst_title.pack(side="left")

        self.btn_open_folder = ctk.CTkButton(
            inst_top, text=self.tr("btn_open_folder"), width=120, height=28,
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
            command=self._open_mods_folder
        )
        self.btn_open_folder.pack(side="right", padx=(6, 0))

        self.btn_refresh_list = ctk.CTkButton(
            inst_top, text=self.tr("btn_refresh_list"), width=90, height=28,
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
            command=self._refresh_installed_mods_list
        )
        self.btn_refresh_list.pack(side="right")

        self.installed_scroll = ctk.CTkScrollableFrame(
            self.tab_installed, fg_color="transparent", corner_radius=10
        )
        self.installed_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        mr_top = ctk.CTkFrame(self.tab_modrinth, fg_color="transparent")
        mr_top.pack(fill="x", padx=8, pady=(4, 6))

        self.mr_search_entry = ctk.CTkEntry(
            mr_top,
            placeholder_text=self.tr("search_placeholder"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS, height=34, corner_radius=10
        )
        self.mr_search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.mr_search_entry.bind("<Return>", lambda e: self._on_modrinth_search_submit())

        self.btn_mr_search = ctk.CTkButton(
            mr_top, text=self.tr("btn_search"), width=85, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
            corner_radius=10, command=self._on_modrinth_search_submit
        )
        self.btn_mr_search.pack(side="right")

        self.modrinth_scroll = ctk.CTkScrollableFrame(
            self.tab_modrinth, fg_color="transparent", corner_radius=10
        )
        self.modrinth_scroll.pack(fill="both", expand=True, padx=4, pady=(2, 4))

        self.mr_pag_bar = ctk.CTkFrame(self.tab_modrinth, fg_color="transparent", height=32)
        self.mr_pag_bar.pack(fill="x", padx=8, pady=(2, 2))

        self.btn_page_prev = ctk.CTkButton(
            self.mr_pag_bar, text=self.tr("page_prev"), width=80, height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
            command=self._on_page_prev
        )
        self.btn_page_prev.pack(side="left")

        self.lbl_page_info = ctk.CTkLabel(
            self.mr_pag_bar, text="Сторінка 1 з 1",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED
        )
        self.lbl_page_info.pack(side="left", expand=True)

        self.btn_page_next = ctk.CTkButton(
            self.mr_pag_bar, text=self.tr("page_next"), width=80, height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
            command=self._on_page_next
        )
        self.btn_page_next.pack(side="right")

        # ── CurseForge Mods Tab ─────────────────────────────────
        cf_top = ctk.CTkFrame(self.tab_curseforge, fg_color="transparent")
        cf_top.pack(fill="x", padx=8, pady=(4, 6))

        self.cf_search_entry = ctk.CTkEntry(
            cf_top,
            placeholder_text="🔍 Пошук модів на CurseForge...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS, height=34, corner_radius=10
        )
        self.cf_search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.cf_search_entry.bind("<Return>", lambda e: self._on_curseforge_mods_search_submit())

        self.btn_cf_search = ctk.CTkButton(
            cf_top, text=self.tr("btn_search"), width=85, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
            corner_radius=10, command=self._on_curseforge_mods_search_submit
        )
        self.btn_cf_search.pack(side="right")

        self.curseforge_scroll = ctk.CTkScrollableFrame(
            self.tab_curseforge, fg_color="transparent", corner_radius=10
        )
        self.curseforge_scroll.pack(fill="both", expand=True, padx=4, pady=(2, 4))

        self.cf_pag_bar = ctk.CTkFrame(self.tab_curseforge, fg_color="transparent", height=32)
        self.cf_pag_bar.pack(fill="x", padx=8, pady=(2, 2))

        self.btn_cf_page_prev = ctk.CTkButton(
            self.cf_pag_bar, text=self.tr("page_prev"), width=80, height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
            command=self._on_cf_page_prev
        )
        self.btn_cf_page_prev.pack(side="left")

        self.lbl_cf_page_info = ctk.CTkLabel(
            self.cf_pag_bar, text="Сторінка 1 з 1",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED
        )
        self.lbl_cf_page_info.pack(side="left", expand=True)

        self.btn_cf_page_next = ctk.CTkButton(
            self.cf_pag_bar, text=self.tr("page_next"), width=80, height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
            command=self._on_cf_page_next
        )
        self.btn_cf_page_next.pack(side="right")

    # ══════════════════════════════════════════════════════════════════════════
    #  2.5 CONFIGS VIEW (Cloud Configs)
    # ══════════════════════════════════════════════════════════════════════════
    def _init_configs_view(self):
        self.configs_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")

        # Top Control Bar (Search by code + Publish)
        bar = ctk.CTkFrame(self.configs_frame, fg_color="transparent", corner_radius=16, border_width=1, border_color="#38bdf8")
        bar.pack(fill="x", pady=(0, 10))

        bar_inner = ctk.CTkFrame(bar, fg_color="transparent")
        bar_inner.pack(fill="x", padx=12, pady=10)

        # Code search entry
        self.cfg_code_entry = ctk.CTkEntry(
            bar_inner, height=36, width=170,
            placeholder_text="Код конфігу (6 симв.)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS, corner_radius=10
        )
        self.cfg_code_entry.pack(side="left", padx=(0, 8))

        btn_fetch = ctk.CTkButton(
            bar_inner, text="Знайти", width=80, height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=10,
            command=self._find_cloud_config_by_code
        )
        btn_fetch.pack(side="left", padx=(0, 8))

        btn_refresh = ctk.CTkButton(
            bar_inner, text="Оновити", width=80, height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=10,
            command=self._load_cloud_configs
        )
        btn_refresh.pack(side="left", padx=(0, 8))

        # Publish Button
        btn_publish = ctk.CTkButton(
            bar_inner, text="☁ Опублікувати", width=140, height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#059669", hover_color="#10b981", corner_radius=10,
            command=self._publish_config_dialog
        )
        btn_publish.pack(side="right")

        # Scrollable Configs List
        self.configs_scroll = ctk.CTkScrollableFrame(self.configs_frame, fg_color="transparent")
        self.configs_scroll.pack(fill="both", expand=True)

    def _load_cloud_configs(self):
        for w in self.configs_scroll.winfo_children():
            w.destroy()

        loading = ctk.CTkLabel(self.configs_scroll, text="Завантаження хмарних конфігів...", font=ctk.CTkFont(family="Segoe UI", size=13))
        loading.pack(pady=30)

        def worker():
            ok, configs = list_cloud_configs()
            self.after(0, lambda: self._render_cloud_configs(ok, configs, loading))

        threading.Thread(target=worker, daemon=True).start()

    def _render_cloud_configs(self, ok, configs, loading_lbl):
        loading_lbl.destroy()
        if not ok or not configs:
            ctk.CTkLabel(self.configs_scroll, text="Хмарні конфіги відсутні або помилка з'єднання", font=ctk.CTkFont(family="Segoe UI", size=13)).pack(pady=30)
            return

        current_user = self.auth_user.get("username", "") if self.auth_user else self.alt_switcher.get_username()

        for item in configs:
            c_id = item.get("id", "")
            c_name = item.get("name", "Config")
            c_author = item.get("author", "Unknown")
            c_desc = item.get("description", "")
            c_dls = item.get("downloads", 0)
            content = item.get("content", {})

            card = ctk.CTkFrame(self.configs_scroll, fg_color="transparent", corner_radius=14, border_width=1, border_color="#38bdf8")
            card.pack(fill="x", padx=4, pady=5)

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(10, 2))

            # Code badge
            code_badge = ctk.CTkLabel(
                top, text=f" {c_id} ",
                font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                fg_color="#1e293b", text_color="#38bdf8", corner_radius=6
            )
            code_badge.pack(side="left", padx=(0, 10))

            title_box = ctk.CTkFrame(top, fg_color="transparent")
            title_box.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                title_box, text=c_name,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#60a5fa"
            ).pack(anchor="w")

            author_str = f"Автор: {c_author}"
            if current_user and c_author.lower() == current_user.lower():
                author_str += " (Ваш конфіг)"
            author_str += f"  ·  ⬇ {c_dls} завантажень"

            ctk.CTkLabel(
                title_box, text=author_str,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=TEXT_MUTED
            ).pack(anchor="w")

            if c_desc:
                ctk.CTkLabel(
                    card, text=c_desc,
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    text_color=TEXT_MUTED, wraplength=540, justify="left"
                ).pack(anchor="w", padx=12, pady=(4, 6))

            btn_box = ctk.CTkFrame(card, fg_color="transparent")
            btn_box.pack(fill="x", padx=12, pady=(4, 10))

            # Copy code button
            def copy_code(code=c_id):
                self.clipboard_clear()
                self.clipboard_append(code)
                messagebox.showinfo("Скопійовано", f"Код {code} скопійовано в буфер обміну!")

            ctk.CTkButton(
                btn_box, text="📋 Скопіювати код", width=120, height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
                command=copy_code
            ).pack(side="left", padx=(0, 8))

            # Install directly to client
            def install_to_client(name=c_name, data=content):
                self._save_config_to_client(name, data)

            ctk.CTkButton(
                btn_box, text="⚡ Завантажити в клієнт", width=140, height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=8,
                command=install_to_client
            ).pack(side="left", padx=(0, 8))

            # Download as file
            def download_as_file(name=c_name, data=content):
                self._export_config_file(name, data)

            ctk.CTkButton(
                btn_box, text="💾 Скачати як файл", width=130, height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                fg_color="#1e293b", hover_color="#334155", corner_radius=8,
                command=download_as_file
            ).pack(side="left")

    def _find_cloud_config_by_code(self):
        code = self.cfg_code_entry.get().strip().upper()
        if not code:
            messagebox.showwarning("Код", "Введіть 6-значний код конфігу!")
            return

        def worker():
            ok, res = get_cloud_config_by_id(code)
            if ok:
                self.after(0, lambda: self._show_single_config_modal(res))
            else:
                self.after(0, lambda: messagebox.showerror("Помилка", str(res)))

        threading.Thread(target=worker, daemon=True).start()

    def _show_single_config_modal(self, cfg_data):
        c_name = cfg_data.get("name", "Config")
        c_author = cfg_data.get("author", "Unknown")
        c_id = cfg_data.get("id", "")
        content = cfg_data.get("content", {})
        c_desc = cfg_data.get("description", "Без опису")

        resp = messagebox.askyesno(
            f"Конфіг [{c_id}]",
            f"Назва: {c_name}\nАвтор: {c_author}\nОпис: {c_desc}\n\nБажаєте встановити цей конфіг у клієнт?"
        )
        if resp:
            self._save_config_to_client(c_name, content)

    def _save_config_to_client(self, name, content):
        target_dir = r"C:\lunarix\client1_21_11\config"
        os.makedirs(target_dir, exist_ok=True)
        # Parse content if string and sanitize encoding
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                pass
        content = sanitize_config_encoding(content)
        clean_name = "".join(c for c in name if c.isalnum() or c in ("-", "_", " ")).strip() or "config"
        target_path = os.path.join(target_dir, f"{clean_name}.json")
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2, ensure_ascii=False)

            # Також зберігаємо у папку config активного game_dir (якщо налаштований)
            g_dir = self.config_data.get("game_dir")
            if g_dir and os.path.exists(g_dir):
                g_cfg_dir = os.path.join(g_dir, "config")
                try:
                    os.makedirs(g_cfg_dir, exist_ok=True)
                    with open(os.path.join(g_cfg_dir, f"{clean_name}.json"), "w", encoding="utf-8") as f2:
                        json.dump(content, f2, indent=2, ensure_ascii=False)
                except Exception:
                    pass

            messagebox.showinfo("Успіх", f"Конфіг '{clean_name}.json' успішно завантажено в клієнт (UTF-8)!\nШлях: {target_path}")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося зберегти: {e}")

    def _export_config_file(self, name, content):
        clean_name = "".join(c for c in name if c.isalnum() or c in ("-", "_", " ")).strip() or "config"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Config", "*.json")],
            initialfile=f"{clean_name}.json"
        )
        if file_path:
            try:
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except Exception:
                        pass
                content = sanitize_config_encoding(content)
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(content, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Збережено", f"Файл конфігу збережено у чистому форматі UTF-8:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Помилка", f"Помилка експорту: {e}")

    def _publish_config_dialog(self):
        f = filedialog.askopenfilename(
            initialdir=r"C:\lunarix\client1_21_11\config",
            title="Оберіть конфіг для публікації",
            filetypes=[("JSON Config", "*.json")]
        )
        if not f:
            return

        ok, data = load_json_file_safe(f)
        if not ok:
            messagebox.showerror("Помилка", f"Не вдалося прочитати JSON: {data}")
            return

        name = fix_mojibake_text(os.path.splitext(os.path.basename(f))[0])
        author = self.auth_user.get("username", "") if self.auth_user else self.alt_switcher.get_username()
        if not author:
            author = "Player"

        def worker():
            ok, res = publish_cloud_config(name, author, data, description="Published from Lunarix Launcher")
            if ok:
                self.after(0, lambda: messagebox.showinfo("Опубліковано!", f"Конфіг успішно опубліковано у чистому форматі UTF-8!\nКод для спільного доступу: {res}"))
                self.after(0, self._load_cloud_configs)
            else:
                self.after(0, lambda: messagebox.showerror("Помилка", f"Не вдалося опублікувати: {res}"))

        threading.Thread(target=worker, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    #  2.54 LOCAL CLIENT CONFIGS VIEW (files in client config dir)
    # ══════════════════════════════════════════════════════════════════════════
    def _init_localcfg_view(self):
        self.localcfg_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")

        # Top Control Bar
        bar = ctk.CTkFrame(self.localcfg_frame, fg_color="transparent", corner_radius=16,
                           border_width=1, border_color="#38bdf8")
        bar.pack(fill="x", pady=(0, 10))

        bar_inner = ctk.CTkFrame(bar, fg_color="transparent")
        bar_inner.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(
            bar_inner, text="⚙ Локальні конфіги клієнта",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#60a5fa"
        ).pack(side="left")

        ctk.CTkLabel(
            bar_inner, text=CLIENT_CONFIG_DIR,
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=TEXT_MUTED
        ).pack(side="left", padx=12)

        btn_dir = ctk.CTkButton(
            bar_inner, text="📂 Папка", width=80, height=32,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
            command=lambda: os.startfile(CLIENT_CONFIG_DIR) if os.path.isdir(CLIENT_CONFIG_DIR) else os.startfile(os.path.dirname(CLIENT_CONFIG_DIR))
        )
        btn_dir.pack(side="right", padx=(0, 8))

        ctk.CTkButton(
            bar_inner, text="🔄 Оновити", width=90, height=32,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
            command=self._load_localcfg_configs
        ).pack(side="right", padx=(0, 8))

        ctk.CTkButton(
            bar_inner, text="➕ Створити конфіг", width=140, height=32,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=8,
            command=self._localcfg_create_dialog
        ).pack(side="right")

        # Scrollable Configs List
        self.localcfg_scroll = ctk.CTkScrollableFrame(self.localcfg_frame, fg_color="transparent")
        self.localcfg_scroll.pack(fill="both", expand=True)

    def _load_localcfg_configs(self):
        for w in self.localcfg_scroll.winfo_children():
            w.destroy()

        configs = list_local_configs()
        if not configs:
            ctk.CTkLabel(
                self.localcfg_scroll,
                text="Конфігів не знайдено. Натисніть «➕ Створити конфіг» або створіть їх у грі через .cfg save.",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=TEXT_MUTED
            ).pack(pady=40)
            return

        for item in configs:
            name = item["name"]
            path = item["path"]
            size_kb = item["size"] / 1024.0
            mtime = time.strftime("%d.%m.%Y %H:%M", time.localtime(item["mtime"]))

            card = ctk.CTkFrame(self.localcfg_scroll, fg_color="transparent",
                                corner_radius=14, border_width=1, border_color="#38bdf8")
            card.pack(fill="x", padx=4, pady=5)

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(10, 2))

            title_box = ctk.CTkFrame(top, fg_color="transparent")
            title_box.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                title_box, text=name,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#60a5fa"
            ).pack(anchor="w")

            ctk.CTkLabel(
                title_box, text=f"{size_kb:.1f} KB  ·  змінено {mtime}",
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=TEXT_MUTED
            ).pack(anchor="w")

            btn_box = ctk.CTkFrame(card, fg_color="transparent")
            btn_box.pack(fill="x", padx=12, pady=(4, 10))

            def open_editor(n=name, p=path):
                ConfigEditorWindow(self, n, p)

            ctk.CTkButton(
                btn_box, text="✏️ Редагувати", width=110, height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=8,
                command=open_editor
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                btn_box, text="✏️ Перейменувати", width=120, height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
                command=lambda n=name: self._localcfg_rename_dialog(n)
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                btn_box, text="🗑 Видалити", width=90, height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                fg_color="#7f1d1d", hover_color="#991b1b", corner_radius=8,
                command=lambda n=name: self._localcfg_delete(n)
            ).pack(side="left")

    def _localcfg_create_dialog(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Створити конфіг")
        popup.geometry("400x210")
        popup.configure(fg_color="#070e1c")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)

        self.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 400) // 2
        py = self.winfo_y() + (self.winfo_height() - 210) // 2
        popup.geometry(f"+{px}+{py}")

        ctk.CTkLabel(
            popup, text="НОВИЙ КОНФІГ",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#60a5fa"
        ).pack(pady=(18, 4))

        ctk.CTkLabel(
            popup, text="Назва конфігу (без .json):",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_MUTED
        ).pack()

        entry = ctk.CTkEntry(
            popup, height=36, width=320,
            placeholder_text="my_config",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS, corner_radius=10
        )
        entry.pack(pady=(6, 14))

        def _create():
            name = entry.get().strip()
            try:
                path = create_config_file(name)
            except ValueError as e:
                messagebox.showwarning("Помилка", str(e), parent=popup)
                return
            popup.destroy()
            messagebox.showinfo("Успіх", f"Конфіг '{name}.json' створено!", parent=self)
            self._load_localcfg_configs()
            ConfigEditorWindow(self, name, path)

        entry.bind("<Return>", lambda e: _create())
        ctk.CTkButton(
            popup, text="СТВОРИТИ", width=320, height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=10,
            command=_create
        ).pack()

    def _localcfg_rename_dialog(self, old_name):
        popup = ctk.CTkToplevel(self)
        popup.title("Перейменувати конфіг")
        popup.geometry("400x210")
        popup.configure(fg_color="#070e1c")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)

        self.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 400) // 2
        py = self.winfo_y() + (self.winfo_height() - 210) // 2
        popup.geometry(f"+{px}+{py}")

        ctk.CTkLabel(
            popup, text="ПЕРЕЙМЕНУВАТИ КОНФІГ",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#60a5fa"
        ).pack(pady=(18, 4))

        ctk.CTkLabel(
            popup, text=f"Стара назва: {old_name}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_MUTED
        ).pack()

        entry = ctk.CTkEntry(
            popup, height=36, width=320,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS, corner_radius=10
        )
        entry.insert(0, old_name)
        entry.pack(pady=(6, 14))
        entry.select_range(0, "end")
        entry.focus_set()

        def _rename():
            new_name = entry.get().strip()
            if new_name == old_name:
                popup.destroy()
                return
            try:
                rename_config_file(old_name, new_name)
            except ValueError as e:
                messagebox.showwarning("Помилка", str(e), parent=popup)
                return
            except Exception as e:
                messagebox.showerror("Помилка", str(e), parent=popup)
                return
            popup.destroy()
            self._load_localcfg_configs()

        entry.bind("<Return>", lambda e: _rename())
        ctk.CTkButton(
            popup, text="ПЕРЕЙМЕНУВАТИ", width=320, height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=10,
            command=_rename
        ).pack()

    def _localcfg_delete(self, name):
        resp = messagebox.askyesno(
            "Видалення конфігу",
            f"Ви впевнені, що хочете видалити конфіг '{name}.json'?\nЦю дію неможливо скасувати.",
            icon="warning", parent=self
        )
        if not resp:
            return
        try:
            delete_config_file(name)
            self._load_localcfg_configs()
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося видалити: {e}", parent=self)

    def _show_localcfg(self):
        self._select_tab("localcfg")
        self._hide_all_tabs()
        self.localcfg_frame.pack(fill="both", expand=True)
        self._load_localcfg_configs()

    # ══════════════════════════════════════════════════════════════════════════
    #  2.55 RESOURCE PACKS VIEW (Community Uploads, Modrinth, CurseForge)
    # ══════════════════════════════════════════════════════════════════════════
    def _init_resourcepacks_view(self):
        self.resourcepacks_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")

        # Top Control Bar (Search & Catalog Selector)
        top_bar = ctk.CTkFrame(self.resourcepacks_frame, fg_color="transparent", corner_radius=16, border_width=1, border_color="#38bdf8")
        top_bar.pack(fill="x", pady=(0, 10))

        bar_in = ctk.CTkFrame(top_bar, fg_color="transparent")
        bar_in.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(
            bar_in, text="КАТАЛОГ РЕСУРСПАКІВ LUNARIX",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#60a5fa"
        ).pack(side="left")

        btn_open_rp_folder = ctk.CTkButton(
            bar_in, text="📁 Папка resourcepacks", width=160, height=32,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=10,
            command=self._open_resourcepacks_folder
        )
        btn_open_rp_folder.pack(side="right", padx=(8, 0))

        btn_publish_rp = ctk.CTkButton(
            bar_in, text="☁ Залити свій ресурспак", width=170, height=32,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#059669", hover_color="#10b981", corner_radius=10,
            command=self._show_publish_resourcepack_dialog
        )
        btn_publish_rp.pack(side="right")

        # Tabview for Resource Packs Sources: Community, Modrinth, CurseForge
        self.rp_tabview = ctk.CTkTabview(
            self.resourcepacks_frame,
            fg_color="#081020",
            segmented_button_selected_color=ACCENT_BLUE,
            segmented_button_selected_hover_color=ACCENT_BLUE_HOVER,
            segmented_button_unselected_color=BG_GLASS_INNER,
            corner_radius=18,
            command=self._on_rp_tab_changed
        )
        self.rp_tabview.pack(fill="both", expand=True)

        self.tab_rp_community = self.rp_tabview.add("👥 Спільнота (Хмарні)")
        self.tab_rp_modrinth = self.rp_tabview.add("🌿 Modrinth")
        self.tab_rp_curseforge = self.rp_tabview.add("🔥 CurseForge")

        # ── 1. COMMUNITY TAB ──────────────────────────────────
        comm_top = ctk.CTkFrame(self.tab_rp_community, fg_color="transparent")
        comm_top.pack(fill="x", padx=8, pady=(4, 6))

        self.rp_comm_search_entry = ctk.CTkEntry(
            comm_top, placeholder_text="🔍 Пошук серед завантажених гравцями...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS, height=34, corner_radius=10
        )
        self.rp_comm_search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.rp_comm_search_entry.bind("<KeyRelease>", lambda e: self._render_filtered_community_rps())

        btn_refresh_comm = ctk.CTkButton(
            comm_top, text="🔄 Оновити", width=95, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=10,
            command=self._load_community_resourcepacks
        )
        btn_refresh_comm.pack(side="right")

        self.rp_comm_scroll = ctk.CTkScrollableFrame(
            self.tab_rp_community, fg_color="transparent", corner_radius=10
        )
        self.rp_comm_scroll.pack(fill="both", expand=True, padx=4, pady=4)
        self._community_rps_cache = []

        # ── 2. MODRINTH RP TAB ────────────────────────────────
        mr_top = ctk.CTkFrame(self.tab_rp_modrinth, fg_color="transparent")
        mr_top.pack(fill="x", padx=8, pady=(4, 6))

        self.rp_mr_search_entry = ctk.CTkEntry(
            mr_top, placeholder_text="🔍 Пошук ресурспаків на Modrinth...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS, height=34, corner_radius=10
        )
        self.rp_mr_search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.rp_mr_search_entry.bind("<Return>", lambda e: self._on_rp_modrinth_search())

        btn_mr_search = ctk.CTkButton(
            mr_top, text="Пошук", width=85, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=10,
            command=self._on_rp_modrinth_search
        )
        btn_mr_search.pack(side="right")

        self.rp_mr_scroll = ctk.CTkScrollableFrame(
            self.tab_rp_modrinth, fg_color="transparent", corner_radius=10
        )
        self.rp_mr_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self.rp_mr_pag_bar = ctk.CTkFrame(self.tab_rp_modrinth, fg_color="transparent", height=32)
        self.rp_mr_pag_bar.pack(fill="x", padx=8, pady=(2, 2))

        self.btn_rp_mr_prev = ctk.CTkButton(
            self.rp_mr_pag_bar, text="◀ Назад", width=80, height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
            command=self._on_rp_mr_prev
        )
        self.btn_rp_mr_prev.pack(side="left")

        self.lbl_rp_mr_page = ctk.CTkLabel(
            self.rp_mr_pag_bar, text="Сторінка 1 з 1",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED
        )
        self.lbl_rp_mr_page.pack(side="left", expand=True)

        self.btn_rp_mr_next = ctk.CTkButton(
            self.rp_mr_pag_bar, text="Вперед ▶", width=80, height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
            command=self._on_rp_mr_next
        )
        self.btn_rp_mr_next.pack(side="right")

        # ── 3. CURSEFORGE RP TAB ──────────────────────────────
        cf_top = ctk.CTkFrame(self.tab_rp_curseforge, fg_color="transparent")
        cf_top.pack(fill="x", padx=8, pady=(4, 6))

        self.rp_cf_search_entry = ctk.CTkEntry(
            cf_top, placeholder_text="🔍 Пошук ресурспаків на CurseForge...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS, height=34, corner_radius=10
        )
        self.rp_cf_search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.rp_cf_search_entry.bind("<Return>", lambda e: self._on_rp_curseforge_search())

        btn_cf_search = ctk.CTkButton(
            cf_top, text="Пошук", width=85, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#ea580c", hover_color="#f97316", corner_radius=10,
            command=self._on_rp_curseforge_search
        )
        btn_cf_search.pack(side="right")

        self.rp_cf_scroll = ctk.CTkScrollableFrame(
            self.tab_rp_curseforge, fg_color="transparent", corner_radius=10
        )
        self.rp_cf_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self.rp_cf_pag_bar = ctk.CTkFrame(self.tab_rp_curseforge, fg_color="transparent", height=32)
        self.rp_cf_pag_bar.pack(fill="x", padx=8, pady=(2, 2))

        self.btn_rp_cf_prev = ctk.CTkButton(
            self.rp_cf_pag_bar, text="◀ Назад", width=80, height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
            command=self._on_rp_cf_prev
        )
        self.btn_rp_cf_prev.pack(side="left")

        self.lbl_rp_cf_page = ctk.CTkLabel(
            self.rp_cf_pag_bar, text="Сторінка 1 з 1",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED
        )
        self.lbl_rp_cf_page.pack(side="left", expand=True)

        self.btn_rp_cf_next = ctk.CTkButton(
            self.rp_cf_pag_bar, text="Вперед ▶", width=80, height=26,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=8,
            command=self._on_rp_cf_next
        )
        self.btn_rp_cf_next.pack(side="right")

    def _open_resourcepacks_folder(self):
        g_dir = self.config_data.get("game_dir", "")
        rp_dir = os.path.join(g_dir, "resourcepacks")
        os.makedirs(rp_dir, exist_ok=True)
        try:
            if os.name == 'nt':
                os.startfile(rp_dir)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', rp_dir])
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося відкрити папку: {e}")

    # ── Community Resource Packs Logic ────────────────────────
    def _load_community_resourcepacks(self):
        for w in self.rp_comm_scroll.winfo_children():
            w.destroy()

        loading = ctk.CTkLabel(self.rp_comm_scroll, text="Завантаження ресурспаків спільноти...", font=ctk.CTkFont(family="Segoe UI", size=13))
        loading.pack(pady=30)

        def worker():
            ok, packs = list_community_resourcepacks()
            self._community_rps_cache = packs if ok else []
            self.after(0, self._render_filtered_community_rps)

        threading.Thread(target=worker, daemon=True).start()

    def _render_filtered_community_rps(self):
        for w in self.rp_comm_scroll.winfo_children():
            w.destroy()

        search = self.rp_comm_search_entry.get().strip().lower()
        packs = self._community_rps_cache
        if search:
            packs = [p for p in packs if search in p.get("name", "").lower() or search in p.get("author", "").lower()]

        if not packs:
            card = ctk.CTkFrame(self.rp_comm_scroll, fg_color="transparent", corner_radius=14, border_width=1, border_color="#38bdf8")
            card.pack(fill="x", padx=4, pady=10)
            msg = "У каталозі спільноти ще немає ресурспаків.\nНатисніть '☁ Залити свій ресурспак' вище, щоб стати першим!"
            if search:
                msg = f"Ресурспаків за запитом '{search}' не знайдено."
            ctk.CTkLabel(card, text=msg, font=ctk.CTkFont(family="Segoe UI", size=13), text_color=TEXT_MUTED, justify="center").pack(pady=30)
            return

        for pack in packs:
            card = ctk.CTkFrame(self.rp_comm_scroll, fg_color=BG_GLASS_CARD, corner_radius=12, border_width=1, border_color=BORDER_GLASS)
            card.pack(fill="x", padx=4, pady=4)

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(10, 4))

            ctk.CTkLabel(top, text="🎨", font=ctk.CTkFont(size=20), width=36).pack(side="left", padx=(0, 8))

            info_box = ctk.CTkFrame(top, fg_color="transparent")
            info_box.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                info_box, text=pack.get("name", "Pack"),
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#60a5fa"
            ).pack(anchor="w")

            author_str = f"Автор: {pack.get('author', 'Unknown')}  ·  ⬇ {pack.get('downloads', 0)} завантажень"
            ctk.CTkLabel(
                info_box, text=author_str,
                font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_MUTED
            ).pack(anchor="w")

            desc = pack.get("description", "")
            if desc:
                ctk.CTkLabel(
                    card, text=desc,
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    text_color=TEXT_MUTED, wraplength=540, justify="left"
                ).pack(anchor="w", padx=14, pady=(2, 6))

            b_row = ctk.CTkFrame(card, fg_color="transparent")
            b_row.pack(fill="x", padx=12, pady=(0, 10))

            ctk.CTkButton(
                b_row, text="Встановити в клієнт", width=140, height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color="#059669", hover_color="#10b981", corner_radius=8,
                command=lambda p=pack: self._install_community_rp_action(p)
            ).pack(side="left")

    def _install_community_rp_action(self, pack_item):
        g_dir = self.config_data.get("game_dir", "")
        rp_dir = os.path.join(g_dir, "resourcepacks")
        name = pack_item.get("name", "Pack")
        self._update_progress(0.1, f"Завантаження {name}...")

        def worker():
            self._log(f"[*] Завантаження ресурспаку '{name}'...")
            ok, res = install_community_resourcepack(pack_item, rp_dir)
            if ok:
                self._log(f"[✓] Ресурспак '{res}' встановлено в resourcepacks/!")
                self.after(0, lambda: messagebox.showinfo("Ресурспаки", f"Ресурспак '{res}' успішно завантажено!\nВін доступний в налаштуваннях Minecraft."))
                self.after(0, self._load_community_resourcepacks)
            else:
                self._log(f"[-] Помилка завантаження ресурспаку: {res}")
                self.after(0, lambda: messagebox.showerror("Помилка", f"Не вдалося завантажити: {res}"))
            self.after(0, lambda: self._update_progress(0, ""))

        threading.Thread(target=worker, daemon=True).start()

    def _show_publish_resourcepack_dialog(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Публікація ресурспаку")
        modal.geometry("480x380")
        modal.resizable(False, False)
        modal.configure(fg_color=BG_MAIN)
        modal.transient(self)
        modal.grab_set()

        ctk.CTkLabel(
            modal, text="ОПУБЛІКУВАТИ РЕСУРСПАК",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#60a5fa"
        ).pack(pady=(16, 4))

        ctk.CTkLabel(
            modal, text="Поділіться власним текстурпаком чи ресурспаком з усіма гравцями",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED
        ).pack(pady=(0, 12))

        form = ctk.CTkFrame(modal, fg_color="transparent")
        form.pack(fill="x", padx=24)

        ctk.CTkLabel(form, text="Назва ресурспаку:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(4, 2))
        entry_name = ctk.CTkEntry(form, height=32, placeholder_text="Наприклад: Faithful PvP 64x", fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS)
        entry_name.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(form, text="Пряме посилання на .zip файл (Dropbox, GitHub тощо):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(4, 2))
        entry_url = ctk.CTkEntry(form, height=32, placeholder_text="https://.../pack.zip", fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS)
        entry_url.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(form, text="Опис / особливості:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(4, 2))
        entry_desc = ctk.CTkEntry(form, height=32, placeholder_text="Короткий опис або роздільна здатність...", fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS)
        entry_desc.pack(fill="x", pady=(0, 16))

        def on_publish():
            p_name = entry_name.get().strip()
            p_url = entry_url.get().strip()
            p_desc = entry_desc.get().strip()
            if not p_name:
                messagebox.showwarning("Помилка", "Вкажіть назву ресурспаку!", parent=modal)
                return
            if not p_url.startswith(("http://", "https://")):
                messagebox.showwarning("Помилка", "Вкажіть коректне посилання на файл .zip!", parent=modal)
                return

            author = self.auth_user.get("username", "") if self.auth_user else self.alt_switcher.get_username()
            if not author:
                author = "Player"

            def worker():
                ok, res = publish_community_resourcepack(p_name, author, p_url, description=p_desc)
                if ok:
                    self.after(0, lambda: messagebox.showinfo("Успіх", f"Ресурспак '{p_name}' опубліковано в каталозі спільноти!"))
                    self.after(0, modal.destroy)
                    self.after(0, self._load_community_resourcepacks)
                else:
                    self.after(0, lambda: messagebox.showerror("Помилка", f"Не вдалося опублікувати: {res}", parent=modal))

            threading.Thread(target=worker, daemon=True).start()

        ctk.CTkButton(
            modal, text="☁ Опублікувати для всіх", height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#059669", hover_color="#10b981", corner_radius=10,
            command=on_publish
        ).pack(fill="x", padx=24, pady=10)

    def _on_rp_tab_changed(self, tab_name):
        if "Modrinth" in tab_name:
            self._load_rp_modrinth_page()
        elif "CurseForge" in tab_name:
            self._load_rp_curseforge_page()
        else:
            self._load_community_resourcepacks()

    # ── Modrinth Resource Packs Logic ─────────────────────────
    def _on_rp_modrinth_search(self):
        self.rp_mr_query = self.rp_mr_search_entry.get().strip()
        self.rp_mr_page = 0
        self._load_rp_modrinth_page()

    def _on_rp_mr_prev(self):
        if self.rp_mr_page > 0:
            self.rp_mr_page -= 1
            self._load_rp_modrinth_page()

    def _on_rp_mr_next(self):
        max_page = max(0, (self.rp_mr_total - 1) // self.rp_mr_limit)
        if self.rp_mr_page < max_page:
            self.rp_mr_page += 1
            self._load_rp_modrinth_page()

    def _load_rp_modrinth_page(self):
        for w in self.rp_mr_scroll.winfo_children():
            w.destroy()

        loading = ctk.CTkLabel(self.rp_mr_scroll, text="Пошук на Modrinth...", font=ctk.CTkFont(family="Segoe UI", size=13))
        loading.pack(pady=30)

        offset = self.rp_mr_page * self.rp_mr_limit

        def worker():
            hits, total = search_modrinth_resourcepacks(query=self.rp_mr_query, limit=self.rp_mr_limit, offset=offset)
            self.after(0, lambda: self._render_rp_modrinth_page(hits, total, loading))

        threading.Thread(target=worker, daemon=True).start()

    def _render_rp_modrinth_page(self, hits, total, loading_lbl):
        loading_lbl.destroy()
        self.rp_mr_total = total
        max_page = max(1, (total + self.rp_mr_limit - 1) // self.rp_mr_limit)

        self.lbl_rp_mr_page.configure(text=f"Сторінка {self.rp_mr_page + 1} з {max_page}")
        self.btn_rp_mr_prev.configure(state="normal" if self.rp_mr_page > 0 else "disabled")
        self.btn_rp_mr_next.configure(state="normal" if self.rp_mr_page < max_page - 1 else "disabled")

        if not hits:
            ctk.CTkLabel(self.rp_mr_scroll, text="Ресурспаків не знайдено на Modrinth", font=ctk.CTkFont(family="Segoe UI", size=13)).pack(pady=30)
            return

        for item in hits:
            title = item.get("title", "Без назви")
            slug = item.get("slug", "")
            desc = item.get("description", "")
            dls = item.get("downloads", 0)
            icon_url = item.get("icon_url")

            card = ctk.CTkFrame(self.rp_mr_scroll, fg_color=BG_GLASS_CARD, corner_radius=12, border_width=1, border_color=BORDER_GLASS)
            card.pack(fill="x", padx=4, pady=4)

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=(8, 2))

            icon_box = ctk.CTkLabel(top_row, text="🌿", width=40, height=40)
            icon_box.pack(side="left", padx=(0, 10))

            if icon_url:
                def load_async(url=icon_url, lbl=icon_box):
                    pil_img = load_mod_icon_pil(url, size=(38, 38))
                    if pil_img:
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(38, 38))
                        self.after(0, lambda: lbl.configure(image=ctk_img))
                threading.Thread(target=load_async, daemon=True).start()

            title_box = ctk.CTkFrame(top_row, fg_color="transparent")
            title_box.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(title_box, text=title, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color="#10b981").pack(anchor="w")
            ctk.CTkLabel(title_box, text=f"🌿 Modrinth · ⬇ {dls:,} downloads", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_MUTED).pack(anchor="w")

            ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED, wraplength=540, justify="left").pack(anchor="w", padx=10, pady=(4, 6))

            b_row = ctk.CTkFrame(card, fg_color="transparent")
            b_row.pack(fill="x", padx=10, pady=(0, 8))

            ctk.CTkButton(
                b_row, text="Встановити", width=120, height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color="#059669", hover_color="#10b981", corner_radius=10,
                command=lambda s=slug: self._install_modrinth_rp_action(s)
            ).pack(side="left")

    def _install_modrinth_rp_action(self, slug):
        g_dir = self.config_data.get("game_dir", "")
        rp_dir = os.path.join(g_dir, "resourcepacks")
        self._update_progress(0.1, f"Завантаження {slug}...")

        def worker():
            self._log(f"[*] Завантаження ресурспаку з Modrinth '{slug}'...")
            ok, msg = install_resourcepack_from_modrinth(slug, rp_dir)
            if ok:
                self._log(f"[✓] Встановлено ресурспак: {msg}")
                self.after(0, lambda: messagebox.showinfo("Ресурспаки", f"Ресурспак '{msg}' успішно завантажено в resourcepacks/!"))
            else:
                self._log(f"[-] Помилка Modrinth: {msg}")
                self.after(0, lambda: messagebox.showerror("Помилка", f"Не вдалося завантажити: {msg}"))
            self.after(0, lambda: self._update_progress(0, ""))

        threading.Thread(target=worker, daemon=True).start()

    # ── CurseForge Resource Packs Logic ───────────────────────
    def _on_rp_curseforge_search(self):
        self.rp_cf_query = self.rp_cf_search_entry.get().strip()
        self.rp_cf_page = 0
        self._load_rp_curseforge_page()

    def _on_rp_cf_prev(self):
        if self.rp_cf_page > 0:
            self.rp_cf_page -= 1
            self._load_rp_curseforge_page()

    def _on_rp_cf_next(self):
        max_page = max(0, (self.rp_cf_total - 1) // self.rp_cf_limit)
        if self.rp_cf_page < max_page:
            self.rp_cf_page += 1
            self._load_rp_curseforge_page()

    def _load_rp_curseforge_page(self):
        for w in self.rp_cf_scroll.winfo_children():
            w.destroy()

        loading = ctk.CTkLabel(self.rp_cf_scroll, text="Пошук ресурспаків на CurseForge...", font=ctk.CTkFont(family="Segoe UI", size=13))
        loading.pack(pady=30)

        offset = self.rp_cf_page * self.rp_cf_limit

        def worker():
            hits, total = search_curseforge_resourcepacks(query=self.rp_cf_query, limit=self.rp_cf_limit, offset=offset)
            self.after(0, lambda: self._render_rp_curseforge_page(hits, total, loading))

        threading.Thread(target=worker, daemon=True).start()

    def _render_rp_curseforge_page(self, hits, total, loading_lbl):
        loading_lbl.destroy()
        self.rp_cf_total = total
        max_page = max(1, (total + self.rp_cf_limit - 1) // self.rp_cf_limit)

        self.lbl_rp_cf_page.configure(text=f"Сторінка {self.rp_cf_page + 1} з {max_page}")
        self.btn_rp_cf_prev.configure(state="normal" if self.rp_cf_page > 0 else "disabled")
        self.btn_rp_cf_next.configure(state="normal" if self.rp_cf_page < max_page - 1 else "disabled")

        if not hits:
            ctk.CTkLabel(self.rp_cf_scroll, text="Ресурспаків не знайдено на CurseForge", font=ctk.CTkFont(family="Segoe UI", size=13)).pack(pady=30)
            return

        for item in hits:
            mod_id = item.get("id")
            title = item.get("name", "Без назви")
            desc = item.get("summary", "")
            dls = item.get("downloadCount", 0)
            logo_info = item.get("logo", {})
            icon_url = logo_info.get("thumbnailUrl") if isinstance(logo_info, dict) else None

            card = ctk.CTkFrame(self.rp_cf_scroll, fg_color=BG_GLASS_CARD, corner_radius=12, border_width=1, border_color=BORDER_GLASS)
            card.pack(fill="x", padx=4, pady=4)

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=(8, 2))

            icon_box = ctk.CTkLabel(top_row, text="🔥", width=40, height=40)
            icon_box.pack(side="left", padx=(0, 10))

            if icon_url:
                def load_async(url=icon_url, lbl=icon_box):
                    pil_img = load_curseforge_icon_pil(url, size=(38, 38))
                    if pil_img:
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(38, 38))
                        self.after(0, lambda: lbl.configure(image=ctk_img))
                threading.Thread(target=load_async, daemon=True).start()

            title_box = ctk.CTkFrame(top_row, fg_color="transparent")
            title_box.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(title_box, text=title, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color="#f97316").pack(anchor="w")
            ctk.CTkLabel(title_box, text=f"🔥 CurseForge · ⬇ {dls:,} downloads", font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_MUTED).pack(anchor="w")

            ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED, wraplength=540, justify="left").pack(anchor="w", padx=10, pady=(4, 6))

            b_row = ctk.CTkFrame(card, fg_color="transparent")
            b_row.pack(fill="x", padx=10, pady=(0, 8))

            ctk.CTkButton(
                b_row, text="Встановити", width=120, height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color="#ea580c", hover_color="#f97316", corner_radius=10,
                command=lambda mid=mod_id, t=title: self._install_curseforge_rp_action(mid, t)
            ).pack(side="left")

    def _install_curseforge_rp_action(self, mod_id, title):
        g_dir = self.config_data.get("game_dir", "")
        rp_dir = os.path.join(g_dir, "resourcepacks")
        self._update_progress(0.1, f"Завантаження {title}...")

        def worker():
            self._log(f"[*] Завантаження ресурспаку з CurseForge: '{title}'...")
            ok, msg = install_file_from_curseforge(mod_id, rp_dir, file_extension=".zip")
            if ok:
                self._log(f"[✓] Встановлено ресурспак: {msg}")
                self.after(0, lambda: messagebox.showinfo("CurseForge", f"Ресурспак '{msg}' успішно завантажено в resourcepacks/!"))
            else:
                self._log(f"[-] Помилка CurseForge: {msg}")
                self.after(0, lambda: messagebox.showerror("Помилка", f"Не вдалося завантажити: {msg}"))
            self.after(0, lambda: self._update_progress(0, ""))

        threading.Thread(target=worker, daemon=True).start()
    def _init_friends_view(self):
        self.friends_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self._friends_data = None
        self._friends_active_subtab = "cloud"  # "cloud", "local", "requests", "users"

        # 1. Top Header Bar
        top_bar = ctk.CTkFrame(self.friends_frame, fg_color="transparent", corner_radius=16, border_width=1, border_color="#38bdf8")
        top_bar.pack(fill="x", pady=(0, 8))

        bar_in = ctk.CTkFrame(top_bar, fg_color="transparent")
        bar_in.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(
            bar_in, text="СПІЛЬНОТА ТА ДРУЗІ LUNARIX",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#60a5fa"
        ).pack(side="left")

        btn_refresh = ctk.CTkButton(
            bar_in, text="🔄 Оновити", width=90, height=32,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=10,
            command=self._load_friends_view
        )
        btn_refresh.pack(side="right")

        # 2. Sub-Tabs Bar (4 Dedicated Sections)
        tabs_bar = ctk.CTkFrame(self.friends_frame, fg_color="transparent", corner_radius=14, border_width=1, border_color="#1d3557")
        tabs_bar.pack(fill="x", pady=(0, 8))

        tabs_in = ctk.CTkFrame(tabs_bar, fg_color="transparent")
        tabs_in.pack(fill="x", padx=10, pady=6)

        self.friends_subtab_seg = ctk.CTkSegmentedButton(
            tabs_in,
            values=["👥 Друзі софту", "🎮 Ігрові (Minecraft)", "📩 Заявки", "🌐 Усі користувачі"],
            selected_color=ACCENT_BLUE,
            selected_hover_color=ACCENT_BLUE_HOVER,
            command=self._on_friends_subtab_select
        )
        self.friends_subtab_seg.set("👥 Друзі софту")
        self.friends_subtab_seg.pack(fill="x")

        # 3. Action & Filter Bar
        action_bar = ctk.CTkFrame(self.friends_frame, fg_color="transparent", corner_radius=14, border_width=1, border_color="#1d3557")
        action_bar.pack(fill="x", pady=(0, 8))

        act_in = ctk.CTkFrame(action_bar, fg_color="transparent")
        act_in.pack(fill="x", padx=14, pady=8)

        self.friends_search_entry = ctk.CTkEntry(
            act_in, height=32, width=220,
            placeholder_text="🔍 Пошук нікнейму...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS, corner_radius=8
        )
        self.friends_search_entry.pack(side="left", padx=(0, 14))
        self.friends_search_entry.bind("<KeyRelease>", lambda e: self._render_current_friends_subtab())

        self.friend_direct_entry = ctk.CTkEntry(
            act_in, height=32, width=180,
            placeholder_text="Нікнейм гравця...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS, corner_radius=8
        )
        self.friend_direct_entry.pack(side="left", padx=(0, 6))

        self.btn_direct_action = ctk.CTkButton(
            act_in, text="+ Додати за ніком", width=140, height=32,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#059669", hover_color="#10b981", corner_radius=8,
            command=self._send_direct_friend_request
        )
        self.btn_direct_action.pack(side="left")

        # 4. Scroll Container for Cards
        self.friends_scroll = ctk.CTkScrollableFrame(self.friends_frame, fg_color="transparent")
        self.friends_scroll.pack(fill="both", expand=True)

    def _on_friends_subtab_select(self, choice):
        if "софту" in choice:
            self._friends_active_subtab = "cloud"
            self.friend_direct_entry.configure(placeholder_text="Нікнейм гравця...")
            self.btn_direct_action.configure(text="+ Додати за ніком", command=self._send_direct_friend_request, fg_color="#059669", hover_color="#10b981")
        elif "Ігрові" in choice:
            self._friends_active_subtab = "local"
            self.friend_direct_entry.configure(placeholder_text="Нікнейм у Minecraft...")
            self.btn_direct_action.configure(text="+ Додати в гру", command=self._add_direct_minecraft_friend, fg_color="#2563eb", hover_color="#1d4ed8")
        elif "Заявки" in choice:
            self._friends_active_subtab = "requests"
            self.friend_direct_entry.configure(placeholder_text="Нікнейм гравця...")
            self.btn_direct_action.configure(text="+ Додати за ніком", command=self._send_direct_friend_request, fg_color="#059669", hover_color="#10b981")
        else:
            self._friends_active_subtab = "users"
            self.friend_direct_entry.configure(placeholder_text="Нікнейм гравця...")
            self.btn_direct_action.configure(text="+ Додати за ніком", command=self._send_direct_friend_request, fg_color="#059669", hover_color="#10b981")
        self._render_current_friends_subtab()

    def _get_local_minecraft_friends(self):
        f_path = r"C:\lunarix\client1_21_11\friends.json"
        if os.path.exists(f_path):
            try:
                with open(f_path, "r", encoding="utf-8") as f:
                    arr = json.load(f)
                    if isinstance(arr, list):
                        return [str(x).strip() for x in arr if str(x).strip()]
            except Exception:
                pass
        return []

    def _save_local_minecraft_friends(self, friends_list):
        f_path = r"C:\lunarix\client1_21_11\friends.json"
        try:
            os.makedirs(os.path.dirname(f_path), exist_ok=True)
            with open(f_path, "w", encoding="utf-8") as f:
                json.dump(friends_list, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося зберегти friends.json: {e}")

    def _add_direct_minecraft_friend(self):
        fname = self.friend_direct_entry.get().strip()
        if not fname:
            messagebox.showwarning("Ігрові друзі", "Введіть нікнейм гравця для додавання в гру!")
            return
        cur = self._get_local_minecraft_friends()
        if fname.lower() in [x.lower() for x in cur]:
            messagebox.showinfo("Ігрові друзі", f"Гравець '{fname}' вже є у списку ігрових друзів!")
            return
        cur.append(fname)
        self._save_local_minecraft_friends(cur)
        self.friend_direct_entry.delete(0, "end")
        messagebox.showinfo("Успіх", f"Гравця '{fname}' додано у friends.json клієнту!")
        self._load_friends_view()

    def _remove_local_friend_action(self, fname):
        resp = messagebox.askyesno("Видалення з гри", f"Видалити нікнейм '{fname}' з ігрового файлу friends.json?")
        if not resp:
            return
        cur = self._get_local_minecraft_friends()
        new_cur = [x for x in cur if x.lower() != fname.lower()]
        self._save_local_minecraft_friends(new_cur)
        self._load_friends_view()

    def _add_cloud_friend_to_local(self, fname):
        cur = self._get_local_minecraft_friends()
        if fname.lower() not in [x.lower() for x in cur]:
            cur.append(fname)
            self._save_local_minecraft_friends(cur)
            messagebox.showinfo("Ігрові друзі", f"Друга '{fname}' додано до ігрового файлу friends.json!")
            self._load_friends_view()

    def _load_friends_view(self):
        for w in self.friends_scroll.winfo_children():
            w.destroy()

        loading = ctk.CTkLabel(self.friends_scroll, text="Завантаження списків друзів...", font=ctk.CTkFont(family="Segoe UI", size=13))
        loading.pack(pady=30)

        current_user = self.auth_user.get("username", "") if self.auth_user else self.alt_switcher.get_username()
        if not current_user:
            current_user = "Player"

        def worker():
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                f_all = executor.submit(list_all_registered_users)
                f_cloud = executor.submit(list_accepted_friends, current_user)
                f_in = executor.submit(list_pending_incoming_requests, current_user)
                f_out = executor.submit(list_pending_outgoing_requests, current_user)
                f_presence = executor.submit(fetch_players_presence)

                all_users = f_all.result()
                cloud_friends = f_cloud.result()
                incoming = f_in.result()
                outgoing = f_out.result()
                presence_map = f_presence.result()

            local_friends = self._get_local_minecraft_friends()

            self._friends_data = {
                "current_user": current_user,
                "all_users": all_users,
                "cloud_friends": cloud_friends,
                "local_friends": local_friends,
                "incoming": incoming,
                "outgoing": outgoing,
                "presence": presence_map
            }
            self.after(0, self._render_current_friends_subtab)

        threading.Thread(target=worker, daemon=True).start()

    def _render_current_friends_subtab(self):
        if self._friends_data is None:
            self._load_friends_view()
            return

        for w in self.friends_scroll.winfo_children():
            w.destroy()

        search = self.friends_search_entry.get().strip().lower()

        if self._friends_active_subtab == "cloud":
            self._render_subtab_cloud_friends(search)
        elif self._friends_active_subtab == "local":
            self._render_subtab_local_friends(search)
        elif self._friends_active_subtab == "requests":
            self._render_subtab_requests(search)
        else:
            self._render_subtab_all_users(search)

    def _render_subtab_cloud_friends(self, search):
        cloud_friends = self._friends_data.get("cloud_friends", [])
        local_set = {x.lower() for x in self._friends_data.get("local_friends", [])}
        if search:
            cloud_friends = [f for f in cloud_friends if search in f.lower()]

        hdr = ctk.CTkFrame(self.friends_scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=4, pady=(2, 6))
        ctk.CTkLabel(
            hdr, text=f"Друзі акаунту Lunarix (Cloud Friends) — {len(cloud_friends)}",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#60a5fa"
        ).pack(side="left")

        if not cloud_friends:
            card = ctk.CTkFrame(self.friends_scroll, fg_color="transparent", corner_radius=16, border_width=1, border_color="#38bdf8")
            card.pack(fill="x", padx=4, pady=10)
            msg = "У вас ще немає підтверджених друзів у софті.\nПерейдіть у вкладку '🌐 Усі користувачі', щоб надіслати запит!"
            if search:
                msg = f"Друзів за запитом '{search}' не знайдено."
            ctk.CTkLabel(
                card, text=msg,
                font=ctk.CTkFont(family="Segoe UI", size=13), text_color=TEXT_MUTED, justify="center"
            ).pack(pady=30)
            return

        presence_map = self._friends_data.get("presence", {})

        for fname in cloud_friends:
            card = ctk.CTkFrame(self.friends_scroll, fg_color="transparent", corner_radius=14, border_width=1, border_color="#38bdf8")
            card.pack(fill="x", padx=4, pady=4)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=10)

            # Determine online / activity status
            p_info = presence_map.get(fname.lower(), {})
            is_on = p_info.get("is_online", False)
            st_text = p_info.get("text", "Офлайн")
            st_color = p_info.get("color", "#64748b")
            dot_color = "#22c55e" if is_on else "#64748b"

            head_lbl = ctk.CTkLabel(
                inner, text="👤",
                font=ctk.CTkFont(family="Segoe UI", size=16),
                width=34, height=34,
                fg_color="#1e293b", corner_radius=8
            )
            head_lbl.pack(side="left", padx=(0, 12))

            name_box = ctk.CTkFrame(inner, fg_color="transparent")
            name_box.pack(side="left", fill="x", expand=True)

            name_row = ctk.CTkFrame(name_box, fg_color="transparent")
            name_row.pack(anchor="w")

            ctk.CTkLabel(
                name_row, text="●",
                font=ctk.CTkFont(size=11),
                text_color=dot_color, width=12
            ).pack(side="left", padx=(0, 5))

            ctk.CTkLabel(
                name_row, text=fname,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#60a5fa"
            ).pack(side="left")

            in_game = fname.lower() in local_set
            ctk.CTkLabel(
                name_box,
                text=f"Статус: {st_text}" + ("  ·  🎮 Є в friends.json" if in_game else ""),
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=st_color
            ).pack(anchor="w", pady=(1, 0))

            btn_box = ctk.CTkFrame(inner, fg_color="transparent")
            btn_box.pack(side="right")

            if not in_game:
                def add_to_mc(target=fname):
                    self._add_cloud_friend_to_local(target)

                ctk.CTkButton(
                    btn_box, text="+ В гру", width=75, height=28,
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    fg_color="#059669", hover_color="#10b981", corner_radius=8,
                    command=add_to_mc
                ).pack(side="left", padx=(0, 8))

            def del_f(target=fname):
                self._remove_friend_action(target)

            ctk.CTkButton(
                btn_box, text="Видалити", width=85, height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color="#dc2626", hover_color="#ef4444", corner_radius=8,
                command=del_f
            ).pack(side="left")

    def _render_subtab_local_friends(self, search):
        local_friends = self._friends_data.get("local_friends", [])
        cloud_set = {x.lower() for x in self._friends_data.get("cloud_friends", [])}
        if search:
            local_friends = [f for f in local_friends if search in f.lower()]

        hdr = ctk.CTkFrame(self.friends_scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=4, pady=(2, 6))
        ctk.CTkLabel(
            hdr, text=f"Ігрові друзі Minecraft (friends.json) — {len(local_friends)}",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#38bdf8"
        ).pack(side="left")

        ctk.CTkLabel(
            hdr, text="Файл: C:/lunarix/client1_21_11/friends.json",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=TEXT_MUTED
        ).pack(side="right")

        if not local_friends:
            card = ctk.CTkFrame(self.friends_scroll, fg_color="transparent", corner_radius=16, border_width=1, border_color="#38bdf8")
            card.pack(fill="x", padx=4, pady=10)
            msg = "У файлі friends.json немає збережених нікнеймів.\nВведіть нікнейм вище, щоб додати гравця в ігрові друзі!"
            if search:
                msg = f"Нікнеймів за запитом '{search}' не знайдено."
            ctk.CTkLabel(
                card, text=msg,
                font=ctk.CTkFont(family="Segoe UI", size=13), text_color=TEXT_MUTED, justify="center"
            ).pack(pady=30)
            return

        presence_map = self._friends_data.get("presence", {})

        for fname in local_friends:
            card = ctk.CTkFrame(self.friends_scroll, fg_color="transparent", corner_radius=14, border_width=1, border_color="#1d3557")
            card.pack(fill="x", padx=4, pady=4)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=10)

            p_info = presence_map.get(fname.lower(), {})
            is_on = p_info.get("is_online", False)
            st_text = p_info.get("text", "Офлайн")
            st_color = p_info.get("color", "#64748b")
            dot_color = "#22c55e" if is_on else "#64748b"

            head_lbl = ctk.CTkLabel(
                inner, text="🎮",
                font=ctk.CTkFont(family="Segoe UI", size=16),
                width=34, height=34,
                fg_color="#1e293b", corner_radius=8
            )
            head_lbl.pack(side="left", padx=(0, 12))

            name_box = ctk.CTkFrame(inner, fg_color="transparent")
            name_box.pack(side="left", fill="x", expand=True)

            name_row = ctk.CTkFrame(name_box, fg_color="transparent")
            name_row.pack(anchor="w")

            ctk.CTkLabel(
                name_row, text="●",
                font=ctk.CTkFont(size=11),
                text_color=dot_color, width=12
            ).pack(side="left", padx=(0, 5))

            ctk.CTkLabel(
                name_row, text=fname,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#38bdf8"
            ).pack(side="left")

            status_str = f"Статус: {st_text}"
            if fname.lower() in cloud_set:
                status_str += "  ·  👥 Друг у софті"

            ctk.CTkLabel(
                name_box, text=status_str,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=st_color if is_on else TEXT_MUTED
            ).pack(anchor="w", pady=(1, 0))

            def del_local(target=fname):
                self._remove_local_friend_action(target)

            ctk.CTkButton(
                inner, text="Видалити з гри", width=115, height=30,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color="#dc2626", hover_color="#ef4444", corner_radius=8,
                command=del_local
            ).pack(side="right")

    def _render_subtab_requests(self, search):
        incoming = self._friends_data.get("incoming", [])
        outgoing = self._friends_data.get("outgoing", [])

        if search:
            incoming = [r for r in incoming if search in r.get("sender", "").lower()]
            outgoing = [r for r in outgoing if search in r.get("receiver", "").lower()]

        # ── 1. Incoming Section ─────────────────────────────
        hdr_in = ctk.CTkFrame(self.friends_scroll, fg_color="transparent")
        hdr_in.pack(fill="x", padx=4, pady=(2, 6))
        ctk.CTkLabel(
            hdr_in, text=f"Вхідні заявки у друзі ({len(incoming)})",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#fbbf24"
        ).pack(side="left")

        if not incoming:
            card_none = ctk.CTkFrame(self.friends_scroll, fg_color="transparent", corner_radius=12, border_width=1, border_color="#1d3557")
            card_none.pack(fill="x", padx=4, pady=(0, 10))
            ctk.CTkLabel(card_none, text="Немає нових вхідних заявок.", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED).pack(pady=12)
        else:
            for req in incoming:
                req_id = req.get("id")
                sender = req.get("sender", "")

                card = ctk.CTkFrame(self.friends_scroll, fg_color="transparent", corner_radius=14, border_width=1, border_color="#fbbf24")
                card.pack(fill="x", padx=4, pady=4)

                inner = ctk.CTkFrame(card, fg_color="transparent")
                inner.pack(fill="x", padx=14, pady=10)

                ctk.CTkLabel(
                    inner, text="📩",
                    font=ctk.CTkFont(family="Segoe UI", size=16),
                    width=34, height=34, fg_color="#1e293b", corner_radius=8
                ).pack(side="left", padx=(0, 12))

                box = ctk.CTkFrame(inner, fg_color="transparent")
                box.pack(side="left", fill="x", expand=True)

                ctk.CTkLabel(
                    box, text=sender,
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                    text_color="#f8fafc"
                ).pack(anchor="w")

                ctk.CTkLabel(
                    box, text="Хоче додати вас у друзі Lunarix",
                    font=ctk.CTkFont(family="Segoe UI", size=10),
                    text_color="#fbbf24"
                ).pack(anchor="w")

                btn_box = ctk.CTkFrame(inner, fg_color="transparent")
                btn_box.pack(side="right")

                def accept_cmd(rid=req_id, sname=sender):
                    self._accept_request_action(rid, sname)

                ctk.CTkButton(
                    btn_box, text="✓ Прийняти", width=95, height=30,
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    fg_color="#059669", hover_color="#10b981", corner_radius=8,
                    command=accept_cmd
                ).pack(side="left", padx=(0, 6))

                def decline_cmd(rid=req_id):
                    self._decline_request_action(rid)

                ctk.CTkButton(
                    btn_box, text="✕ Відхилити", width=95, height=30,
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    fg_color="#334155", hover_color="#dc2626", corner_radius=8,
                    command=decline_cmd
                ).pack(side="left")

        # ── 2. Outgoing Section ─────────────────────────────
        hdr_out = ctk.CTkFrame(self.friends_scroll, fg_color="transparent")
        hdr_out.pack(fill="x", padx=4, pady=(16, 6))
        ctk.CTkLabel(
            hdr_out, text=f"Надіслані заявки ({len(outgoing)})",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#38bdf8"
        ).pack(side="left")

        if not outgoing:
            card_none = ctk.CTkFrame(self.friends_scroll, fg_color="transparent", corner_radius=12, border_width=1, border_color="#1d3557")
            card_none.pack(fill="x", padx=4, pady=(0, 10))
            ctk.CTkLabel(card_none, text="Немає очікуючих надісланих заявок.", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED).pack(pady=12)
        else:
            for req in outgoing:
                req_id = req.get("id")
                receiver = req.get("receiver", "")

                card = ctk.CTkFrame(self.friends_scroll, fg_color="transparent", corner_radius=14, border_width=1, border_color="#1d3557")
                card.pack(fill="x", padx=4, pady=4)

                inner = ctk.CTkFrame(card, fg_color="transparent")
                inner.pack(fill="x", padx=14, pady=10)

                ctk.CTkLabel(
                    inner, text="⏳",
                    font=ctk.CTkFont(family="Segoe UI", size=16),
                    width=34, height=34, fg_color="#1e293b", corner_radius=8
                ).pack(side="left", padx=(0, 12))

                box = ctk.CTkFrame(inner, fg_color="transparent")
                box.pack(side="left", fill="x", expand=True)

                ctk.CTkLabel(
                    box, text=receiver,
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                    text_color="#f8fafc"
                ).pack(anchor="w")

                ctk.CTkLabel(
                    box, text="Заявку надіслано · Очікує підтвердження",
                    font=ctk.CTkFont(family="Segoe UI", size=10),
                    text_color="#38bdf8"
                ).pack(anchor="w")

                def cancel_cmd(rid=req_id):
                    self._decline_request_action(rid)

                ctk.CTkButton(
                    inner, text="Скасувати", width=100, height=30,
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    fg_color="#1e293b", hover_color="#dc2626", corner_radius=8,
                    command=cancel_cmd
                ).pack(side="right")

    def _render_subtab_all_users(self, search):
        all_users = self._friends_data.get("all_users", [])
        current_u = self._friends_data.get("current_user", "").strip().lower()

        other_users = [u for u in all_users if u.strip().lower() != current_u]
        if search:
            other_users = [u for u in other_users if search in u.lower()]

        accepted_set = {x.lower() for x in self._friends_data.get("cloud_friends", [])}
        incoming_map = {r.get("sender", "").lower(): r.get("id") for r in self._friends_data.get("incoming", [])}
        outgoing_map = {r.get("receiver", "").lower(): r.get("id") for r in self._friends_data.get("outgoing", [])}

        hdr = ctk.CTkFrame(self.friends_scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=4, pady=(2, 6))
        ctk.CTkLabel(
            hdr, text=f"Усі зареєстровані користувачі Lunarix ({len(other_users)})",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#38bdf8"
        ).pack(side="left")

        if not other_users:
            card = ctk.CTkFrame(self.friends_scroll, fg_color="transparent", corner_radius=16, border_width=1, border_color="#38bdf8")
            card.pack(fill="x", padx=4, pady=10)
            ctk.CTkLabel(
                card, text="Користувачів не знайдено.",
                font=ctk.CTkFont(family="Segoe UI", size=13), text_color=TEXT_MUTED
            ).pack(pady=30)
            return

        presence_map = self._friends_data.get("presence", {})

        for uname in other_users:
            u_low = uname.lower()
            card = ctk.CTkFrame(self.friends_scroll, fg_color="transparent", corner_radius=14, border_width=1, border_color="#1d3557")
            card.pack(fill="x", padx=4, pady=4)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=10)

            p_info = presence_map.get(u_low, {})
            is_on = p_info.get("is_online", False)
            st_text = p_info.get("text", "Офлайн")
            st_color = p_info.get("color", "#64748b")
            dot_color = "#22c55e" if is_on else "#64748b"

            head_lbl = ctk.CTkLabel(
                inner, text="👤",
                font=ctk.CTkFont(family="Segoe UI", size=16),
                width=34, height=34,
                fg_color="#1e293b", corner_radius=8
            )
            head_lbl.pack(side="left", padx=(0, 12))

            box = ctk.CTkFrame(inner, fg_color="transparent")
            box.pack(side="left", fill="x", expand=True)

            name_row = ctk.CTkFrame(box, fg_color="transparent")
            name_row.pack(anchor="w")

            ctk.CTkLabel(
                name_row, text="●",
                font=ctk.CTkFont(size=11),
                text_color=dot_color, width=12
            ).pack(side="left", padx=(0, 5))

            ctk.CTkLabel(
                name_row, text=uname,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#f8fafc"
            ).pack(side="left")

            ctk.CTkLabel(
                box, text=f"Статус: {st_text}",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=st_color
            ).pack(anchor="w", pady=(1, 0))

            if u_low in accepted_set:
                ctk.CTkLabel(
                    inner, text="✓ У друзях",
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    text_color="#10b981"
                ).pack(side="right", padx=(0, 8))

                def del_cmd(target=uname):
                    self._remove_friend_action(target)

                ctk.CTkButton(
                    inner, text="Видалити", width=80, height=28,
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    fg_color="#1e293b", hover_color="#dc2626", corner_radius=8,
                    command=del_cmd
                ).pack(side="right")

            elif u_low in incoming_map:
                req_id = incoming_map[u_low]
                def acc_cmd(rid=req_id, sname=uname):
                    self._accept_request_action(rid, sname)

                ctk.CTkButton(
                    inner, text="✓ Прийняти заявку", width=130, height=28,
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    fg_color="#059669", hover_color="#10b981", corner_radius=8,
                    command=acc_cmd
                ).pack(side="right")

            elif u_low in outgoing_map:
                req_id = outgoing_map[u_low]
                ctk.CTkLabel(
                    inner, text="⏳ Запит надіслано",
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    text_color="#38bdf8"
                ).pack(side="right", padx=(0, 8))

                def can_cmd(rid=req_id):
                    self._decline_request_action(rid)

                ctk.CTkButton(
                    inner, text="Скасувати", width=85, height=28,
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    fg_color="#1e293b", hover_color="#dc2626", corner_radius=8,
                    command=can_cmd
                ).pack(side="right")

            else:
                def send_cmd(target=uname):
                    self._send_friend_request_to(target)

                ctk.CTkButton(
                    inner, text="+ Додати в друзі", width=125, height=28,
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=8,
                    command=send_cmd
                ).pack(side="right")

    def _send_friend_request_to(self, target):
        current_user = self.auth_user.get("username", "") if self.auth_user else self.alt_switcher.get_username()
        if not current_user:
            current_user = "Player"

        def worker():
            ok, res = send_friend_request(current_user, target)
            if ok:
                self.after(0, lambda: messagebox.showinfo("Запит надіслано", f"Запит у друзі гравцю '{target}' успішно надіслано!"))
                self.after(0, self._load_friends_view)
            else:
                self.after(0, lambda: messagebox.showwarning("Друзі", str(res)))

        threading.Thread(target=worker, daemon=True).start()

    def _send_direct_friend_request(self):
        target = self.friend_direct_entry.get().strip()
        if not target:
            messagebox.showwarning("Друзі", "Введіть нікнейм гравця для додавання!")
            return
        self.friend_direct_entry.delete(0, "end")
        self._send_friend_request_to(target)

    def _accept_request_action(self, req_id, sender_name):
        def worker():
            ok, res = accept_friend_request(req_id)
            if ok:
                self.after(0, lambda: messagebox.showinfo("Успіх", f"Гравця '{sender_name}' додано у ваші друзі софту!"))
                self.after(0, self._load_friends_view)
            else:
                self.after(0, lambda: messagebox.showerror("Помилка", f"Не вдалося прийняти запит: {res}"))

        threading.Thread(target=worker, daemon=True).start()

    def _decline_request_action(self, req_id):
        def worker():
            ok, res = decline_or_cancel_request(req_id)
            self.after(0, self._load_friends_view)

        threading.Thread(target=worker, daemon=True).start()

    def _remove_friend_action(self, fname):
        resp = messagebox.askyesno("Видалення з друзів", f"Ви впевнені, що бажаєте видалити '{fname}' з друзів софту?")
        if not resp:
            return

        current_user = self.auth_user.get("username", "") if self.auth_user else self.alt_switcher.get_username()
        if not current_user:
            current_user = "Player"

        def worker():
            remove_friendship(current_user, fname)
            self.after(0, self._load_friends_view)

        threading.Thread(target=worker, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    #  2.7 CHANGELOG VIEW
    # ══════════════════════════════════════════════════════════════════════════
    def _init_changelog_view(self):
        self.changelog_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")

        top_bar = ctk.CTkFrame(self.changelog_frame, fg_color="transparent", corner_radius=16, border_width=1, border_color="#38bdf8")
        top_bar.pack(fill="x", pady=(0, 10))

        t_in = ctk.CTkFrame(top_bar, fg_color="transparent")
        t_in.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(
            t_in, text="ІСТОРІЯ ОНОВЛЕНЬ LUNARIX CLIENT",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#60a5fa"
        ).pack(side="left")

        ctk.CTkLabel(
            t_in, text=f"Поточна версія: v{LAUNCHER_VERSION}",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=ACCENT_CYAN
        ).pack(side="right")

        scroll = ctk.CTkScrollableFrame(self.changelog_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        changelogs = [
            {
                "ver": "v1.0.1",
                "date": "14.11.2026",
                "tag": "LATEST UPDATE & HOTFIX",
                "color": "#38bdf8",
                "items": [
                    "🚀 Оновлено Fabric Loader до останньої стабільної версії 0.20.1 та Sponge-Mixin 0.17.5.",
                    "⚡ Оновлено Sodium (0.8.15-beta.1): виправлено сумісність із Sodium Extra, Fabric Language Kotlin та іншими модами 1.21.11.",
                    "👥 Окрема вкладка «Альт Менеджер»: зручне керування акаунтами безпосередньо в софті, швидке перемикання зі скінами.",
                    "💬 Окрема вкладка «Глобальний чат»: спілкування між усіма користувачами клієнта в реальному часі.",
                    "📜 Додано зручний повзунок (скролбар) для швидкого гортання вкладок сайдбару.",
                    "🛡️ Захист від мультиакаунтингу: обмеження реєстрацій за HWID (максимум 3 акаунти на одне залізо).",
                    "✉️ Прив'язка електронної пошти під час реєстрації через перевірочний код.",
                    "🏷️ Профіль: кнопка подачі запиту до адміністратора на зміну системного юзернейма.",
                    "🗑️ Самостійне видалення акаунта з обов'язковим підтвердженням кодом із пошти.",
                    "☁️ Розширено меню навігації та оновлено векторні іконки («Хмарні конфіги» тощо) для ідеального відображення.",
                    "🎬 Відео-фон за замовчуванням вимкнено для максимального FPS та швидкодії інтерфейсу.",
                    "🎮 Modrinth: гарантоване завантаження модів суворо під Fabric 1.21.11.",
                    "🦋 Покращено рендеринг крил Wings (усунено тремтіння, плавний rotLerp) та синхронізацію косметики."
                ]
            },
            {
                "ver": "v1.0.0",
                "date": "14.11.2026",
                "tag": "GLOBAL UPDATE",
                "color": "#38bdf8",
                "items": [
                    "✨ Повноцінна інтеграція з Globals на базі Supabase Cloud.",
                    "⚡ Система Actions: встановлення міток у світі по бінду клавіші з ніком, головою скіна та відстанню.",
                    "🎯 Авто-видалення мітки Actions при наближенні ближче 5 метрів або за таймером (5с – 60с).",
                    "🎭 Синхронізація емоцій між усіма користувачами Lunarix Client онлайн.",
                    "🏷️ Іконки клієнту (Lunar, Star, Crown тощо) біля нікнеймів у NameTags та Scoreboard.",
                    "💬 Глобальний чат клієнтерів (історія останніх 100 повідомлень).",
                    "👥 Хмарна система друзів (Friends) із швидким керуванням.",
                    "☁️ Хмарні конфіги (Cloud Configs) через 6-значні шеринг-коди.",
                    "🧩 Виправлено роботу та пагінацію каталогу Modrinth у лаунчері.",
                    "🔒 Авторизація без Email — лише нікнейм та пароль."
                ]
            },
            {
                "ver": "v1.0.0",
                "date": "13.11.2026",
                "tag": "RELEASE",
                "color": "#10b981",
                "items": [
                    "🚀 Офіційний реліз Lunarix Client для Fabric 1.21.11.",
                    "💎 Преміальний дизайн інтерфейсу в стилі Glassmorphism (матове скло).",
                    "🎬 Живий відео-фон та кастомні скляні компоненти інтерфейсу.",
                    "👤 Менеджер альт-акаунтів (Alt Switcher) з локальним збереженням.",
                    "📊 Прокачаний прогрес-бар запуску з неоновим підсвічуванням."
                ]
            }
        ]

        for entry in changelogs:
            card = ctk.CTkFrame(scroll, fg_color="transparent", corner_radius=16, border_width=1, border_color="#38bdf8")
            card.pack(fill="x", padx=4, pady=6)

            ch_top = ctk.CTkFrame(card, fg_color="transparent")
            ch_top.pack(fill="x", padx=16, pady=(12, 6))

            ctk.CTkLabel(
                ch_top, text=entry["ver"],
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#60a5fa"
            ).pack(side="left", padx=(0, 10))

            tag_lbl = ctk.CTkLabel(
                ch_top, text=f" {entry['tag']} ",
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                fg_color="#1e293b", text_color=entry["color"], corner_radius=6
            )
            tag_lbl.pack(side="left", padx=(0, 10))

            ctk.CTkLabel(
                ch_top, text=entry["date"],
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=TEXT_MUTED
            ).pack(side="right")

            ch_body = ctk.CTkFrame(card, fg_color="transparent")
            ch_body.pack(fill="x", padx=16, pady=(0, 12))

            for item in entry["items"]:
                ctk.CTkLabel(
                    ch_body, text=f"•  {item}",
                    font=ctk.CTkFont(family="Segoe UI", size=12),
                    text_color="#e2e8f0", wraplength=640, justify="left"
                ).pack(anchor="w", pady=2)

    # ══════════════════════════════════════════════════════════════════════════
    #  2.5 PROFILE VIEW
    # ══════════════════════════════════════════════════════════════════════════
    def _init_profile_view(self):
        self.profile_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        scroll = ctk.CTkScrollableFrame(self.profile_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        header = ctk.CTkFrame(scroll, fg_color="transparent")
        header.pack(fill="x", pady=(2, 8))
        ctk.CTkLabel(
            header, text=self.tr("profile_title"),
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=TEXT_WHITE
        ).pack(anchor="w")
        ctk.CTkLabel(
            header, text=self.tr("profile_subtitle"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_MUTED, wraplength=640, justify="left"
        ).pack(anchor="w", pady=(2, 0))

        card = ctk.CTkFrame(
            scroll, fg_color="transparent",
            corner_radius=18, border_width=1, border_color=BORDER_GLOW
        )
        card.pack(fill="x", pady=6)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(16, 8))

        self.profile_avatar_lbl = ctk.CTkLabel(top, text="", width=96, height=96)
        self.profile_avatar_lbl.pack(side="left", padx=(0, 16))

        top_right = ctk.CTkFrame(top, fg_color="transparent")
        top_right.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            top_right, text=self.tr("profile_display_name"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        ).pack(anchor="w")
        self.profile_name_entry = ctk.CTkEntry(
            top_right, height=36, font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=BG_GLASS_CARD, border_color=BORDER_GLASS, corner_radius=10,
            placeholder_text=self.tr("profile_display_name")
        )
        self.profile_name_entry.pack(fill="x", pady=(4, 10))

        self.profile_account_lbl = ctk.CTkLabel(
            top_right, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_MUTED, anchor="w", justify="left"
        )
        self.profile_account_lbl.pack(fill="x")

        avatar_row = ctk.CTkFrame(card, fg_color="transparent")
        avatar_row.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(
            avatar_row, text=self.tr("profile_pick_avatar"), width=160, height=34,
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, corner_radius=10,
            command=self._profile_pick_avatar
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            avatar_row, text=self.tr("profile_remove_avatar"), width=120, height=34,
            fg_color=BG_GLASS_CARD, hover_color="#16304f", corner_radius=10,
            border_width=1, border_color=BORDER_GLASS,
            command=self._profile_remove_avatar
        ).pack(side="left")

        cos_card = ctk.CTkFrame(
            scroll, fg_color="transparent",
            corner_radius=18, border_width=1, border_color=BORDER_GLOW
        )
        cos_card.pack(fill="x", pady=6)
        ctk.CTkLabel(
            cos_card, text=self.tr("profile_cosmetics"),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        ).pack(anchor="w", padx=16, pady=(12, 6))

        self.profile_share_cb = ctk.CTkCheckBox(
            cos_card, text=self.tr("profile_share_cosmetics"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_BRIGHT
        )
        self.profile_share_cb.pack(anchor="w", padx=16, pady=4)

        self.profile_see_cb = ctk.CTkCheckBox(
            cos_card, text=self.tr("profile_see_cosmetics"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_BRIGHT
        )
        self.profile_see_cb.pack(anchor="w", padx=16, pady=(4, 12))

        # ── ACCOUNT ADMIN & SECURITY CARD ────────────────────────────────────
        sec_card = ctk.CTkFrame(
            scroll, fg_color="#0b162c",
            corner_radius=18, border_width=1, border_color="#1e3a5f"
        )
        sec_card.pack(fill="x", pady=6)

        ctk.CTkLabel(
            sec_card, text="Керування системним акаунтом",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#f8fafc"
        ).pack(anchor="w", padx=16, pady=(12, 4))

        self.profile_rename_status_lbl = ctk.CTkLabel(
            sec_card, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#38bdf8", wraplength=600, justify="left"
        )
        self.profile_rename_status_lbl.pack(anchor="w", padx=16, pady=(0, 6))

        admin_btns_row = ctk.CTkFrame(sec_card, fg_color="transparent")
        admin_btns_row.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkButton(
            admin_btns_row, text="🔑 Змінити пароль",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#142c54", hover_color="#1e4078", corner_radius=10, height=36,
            command=self._show_change_password_modal
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            admin_btns_row, text="📝 Запросити зміну юзернейма в адміна",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#142c54", hover_color="#1e4078", corner_radius=10, height=36,
            command=self._show_rename_request_modal
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            admin_btns_row, text="🗑️ Видалити акаунт (код з пошти)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#3f1319", hover_color="#dc2626", text_color="#f87171", corner_radius=10, height=36,
            command=self._start_account_deletion_flow
        ).pack(side="left")

        ctk.CTkButton(
            scroll, text=self.tr("profile_save"),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
            height=42, corner_radius=12,
            command=self._profile_save
        ).pack(fill="x", pady=(10, 14))

        self._refresh_profile_view()

    def _show_change_password_modal(self):
        curr_user = (self.auth_user or {}).get("username") or self.config_data.get("username")
        if not curr_user or curr_user == "Player":
            messagebox.showwarning("LUNARIX", "Для зміни паролю необхідно спочатку увійти в акаунт!")
            return

        popup = ctk.CTkToplevel(self)
        popup.title("Зміна паролю акаунта")
        popup.geometry("380x300")
        popup.configure(fg_color="#070e1c")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)

        self.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 380) // 2
        py = self.winfo_y() + (self.winfo_height() - 300) // 2
        popup.geometry(f"+{px}+{py}")

        ctk.CTkLabel(popup, text="ЗМІНА ПАРОЛЮ", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#60a5fa").pack(pady=(16, 2))
        ctk.CTkLabel(popup, text=f"Акаунт: {curr_user}\n(Введіть новий пароль для збереження)", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED, justify="center").pack(pady=(0, 12))

        f = ctk.CTkFrame(popup, fg_color="transparent")
        f.pack(fill="x", padx=24)

        ctk.CTkLabel(f, text="Новий пароль (від 4 символів)", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", pady=(0, 2))
        p1_row = ctk.CTkFrame(f, fg_color="transparent")
        p1_row.pack(fill="x", pady=(0, 8))
        p1 = ctk.CTkEntry(p1_row, height=34, show="•", font=ctk.CTkFont(family="Segoe UI", size=12), placeholder_text="Введіть новий пароль", corner_radius=10, fg_color="#040914", border_color="#1e3a5f")
        p1.pack(side="left", fill="x", expand=True, padx=(0, 6))

        eye_btn1 = ctk.CTkButton(p1_row, text="👁", width=34, height=34, fg_color="#142c54", hover_color="#1e4078", corner_radius=8,
                                 command=lambda: p1.configure(show="" if p1.cget("show") == "•" else "•"))
        eye_btn1.pack(side="right")

        ctk.CTkLabel(f, text="Повторіть новий пароль", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", pady=(0, 2))
        p2 = ctk.CTkEntry(f, height=34, show="•", font=ctk.CTkFont(family="Segoe UI", size=12), placeholder_text="Повторіть новий пароль", corner_radius=10, fg_color="#040914", border_color="#1e3a5f")
        p2.pack(fill="x", pady=(0, 14))

        def _do_change():
            v1 = p1.get().strip()
            v2 = p2.get().strip()
            if len(v1) < 4:
                messagebox.showwarning("Помилка", "Пароль має містити щонайменше 4 символи!", parent=popup)
                return
            if v1 != v2:
                messagebox.showwarning("Помилка", "Паролі не збігаються!", parent=popup)
                return
            ok, msg = update_user_password(curr_user, v1)
            if ok:
                messagebox.showinfo("LUNARIX", f"Пароль акаунту «{curr_user}» успішно оновлено!", parent=popup)
                popup.destroy()
            else:
                messagebox.showerror("Помилка", str(msg), parent=popup)

        ctk.CTkButton(popup, text="ЗБЕРЕГТИ ПАРОЛЬ", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, height=36, corner_radius=10, command=_do_change).pack(fill="x", padx=24)

    def _show_rename_request_modal(self):
        curr_user = (self.auth_user or {}).get("username") or self.config_data.get("username")
        if not curr_user or curr_user == "Player":
            messagebox.showwarning("LUNARIX", "Для запиту зміни юзернейма необхідно спочатку увійти в акаунт!")
            return

        popup = ctk.CTkToplevel(self)
        popup.title("Запит на зміну юзернейма")
        popup.geometry("420x280")
        popup.configure(fg_color="#070e1c")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)

        self.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 420) // 2
        py = self.winfo_y() + (self.winfo_height() - 280) // 2
        popup.geometry(f"+{px}+{py}")

        ctk.CTkLabel(popup, text="ЗАПИТ НА ЗМІНУ ЮЗЕРНЕЙМА", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#60a5fa").pack(pady=(16, 2))
        ctk.CTkLabel(popup, text=f"Поточний нікнейм акаунта: {curr_user}\n(Адміністратор розгляне та підтвердить запит)", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED, justify="center").pack(pady=(0, 12))

        f = ctk.CTkFrame(popup, fg_color="transparent")
        f.pack(fill="x", padx=24)

        ctk.CTkLabel(f, text="Бажаний новий юзернейм", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", pady=(0, 2))
        new_entry = ctk.CTkEntry(f, height=34, font=ctk.CTkFont(family="Segoe UI", size=12), placeholder_text="Новий нікнейм (від 3 символів)", corner_radius=10, fg_color="#040914", border_color="#1e3a5f")
        new_entry.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(f, text="Причина зміни (для адміна)", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", pady=(0, 2))
        reason_entry = ctk.CTkEntry(f, height=34, font=ctk.CTkFont(family="Segoe UI", size=12), placeholder_text="Чому бажаєте змінити нікнейм", corner_radius=10, fg_color="#040914", border_color="#1e3a5f")
        reason_entry.pack(fill="x", pady=(0, 14))

        def _submit():
            new_u = new_entry.get().strip()
            reason = reason_entry.get().strip()
            if not new_u or len(new_u) < 3:
                messagebox.showwarning("Помилка", "Введіть новий нікнейм від 3 символів!", parent=popup)
                return
            ok, msg = request_username_rename(curr_user, new_u, reason)
            if ok:
                messagebox.showinfo("LUNARIX", f"Запит на зміну юзернейма на «{new_u}» надіслано адміністратору!", parent=popup)
                popup.destroy()
                self._refresh_profile_view()
            else:
                messagebox.showerror("Помилка", str(msg), parent=popup)

        ctk.CTkButton(popup, text="НАДІСЛАТИ ЗАПИТ АДМІНІСТРАТОРУ", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, height=36, corner_radius=10, command=_submit).pack(fill="x", padx=24)

    def _start_account_deletion_flow(self):
        curr_user = (self.auth_user or {}).get("username")
        if not curr_user or curr_user == "Player":
            messagebox.showwarning("LUNARIX", "Ви не увійшли в зареєстрований акаунт!")
            return

        confirm = messagebox.askyesno(
            "Видалення акаунта",
            f"Ви справді бажаєте остаточно видалити акаунт «{curr_user}»?\n\nДля безпеки на вашу прив'язану електронну пошту буде надіслано 6-значний код підтвердження.",
            icon="warning"
        )
        if not confirm:
            return

        # Trigger code send
        ok, code = request_account_deletion_code(curr_user)

        popup = ctk.CTkToplevel(self)
        popup.title("Підтвердження видалення акаунта")
        popup.geometry("380x240")
        popup.configure(fg_color="#070e1c")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)

        self.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 380) // 2
        py = self.winfo_y() + (self.winfo_height() - 240) // 2
        popup.geometry(f"+{px}+{py}")

        ctk.CTkLabel(popup, text="ПІДТВЕРДЖЕННЯ ВИДАЛЕННЯ", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#f87171").pack(pady=(18, 4))
        ctk.CTkLabel(popup, text=f"Код підтвердження надіслано на вашу пошту.\nВведіть 6 цифр для остаточного видалення {curr_user}:", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_MUTED, justify="center").pack(pady=(0, 14))

        code_entry = ctk.CTkEntry(popup, height=36, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), placeholder_text="Введіть 6-значний код", corner_radius=10, fg_color="#040914", border_color="#f87171")
        code_entry.pack(fill="x", padx=24, pady=(0, 16))
        code_entry.focus()

        def _do_del():
            inp = code_entry.get().strip()
            if not inp:
                return
            del_ok, del_msg = confirm_account_deletion(curr_user, inp)
            if del_ok:
                popup.destroy()
                messagebox.showinfo("LUNARIX", "Акаунт успішно видалено з системи!")
                self._on_logout()
            else:
                messagebox.showerror("Помилка", str(del_msg), parent=popup)

        ctk.CTkButton(popup, text="ОСТАТОЧНО ВИДАЛИТИ АКАУНТ", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), fg_color="#dc2626", hover_color="#b91c1c", height=38, corner_radius=10, command=_do_del).pack(fill="x", padx=24)

    def _profile_avatar_image(self, path, size=96):
        try:
            if path and os.path.exists(path):
                img = Image.open(path).convert("RGBA")
            else:
                img = generate_steve_avatar(size * 4).convert("RGBA")
            img = ImageOps.fit(img, (size, size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=max(6, size // 5), fill=255)
            img.putalpha(mask)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        except Exception:
            return None

    def _refresh_profile_view(self):
        if not hasattr(self, "profile_name_entry"):
            return
        cfg = self.config_data
        name = cfg.get("display_name") or profile_display_name(cfg)
        self.profile_name_entry.delete(0, "end")
        self.profile_name_entry.insert(0, name)

        avatar = profile_avatar_path(cfg)
        self._profile_avatar_img = self._profile_avatar_image(avatar)
        self.profile_avatar_lbl.configure(image=self._profile_avatar_img, text="" if self._profile_avatar_img else "—")

        account = (self.auth_user or {}).get("username") or cfg.get("username") or "Player"
        email = get_account_email(account)
        email_info = f"  ·  ✉ {email}" if email else ""
        self.profile_account_lbl.configure(text=f"{self.tr('profile_account', account=account)}{email_info}")

        if cfg.get("share_cosmetics", True):
            self.profile_share_cb.select()
        else:
            self.profile_share_cb.deselect()
        if cfg.get("see_other_cosmetics", True):
            self.profile_see_cb.select()
        else:
            self.profile_see_cb.deselect()

        if hasattr(self, 'profile_rename_status_lbl'):
            def _check_req():
                try:
                    acc = (self.auth_user or {}).get("username")
                    if acc:
                        req = get_pending_rename_request(acc)
                        if req:
                            r_name = req.get("requested_username", "")
                            self.after(0, lambda: self.profile_rename_status_lbl.configure(
                                text=f"📌 Активний запит на зміну нікнейма на «{r_name}» (В очікуванні розгляду адміном)"
                            ))
                        else:
                            self.after(0, lambda: self.profile_rename_status_lbl.configure(text=""))
                    else:
                        self.after(0, lambda: self.profile_rename_status_lbl.configure(text=""))
                except Exception:
                    pass
            threading.Thread(target=_check_req, daemon=True).start()

    def _profile_pick_avatar(self):
        picked = filedialog.askopenfilename(
            title=self.tr("profile_pick_avatar"),
            filetypes=[
                ("Зображення", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
                ("Усі файли", "*.*"),
            ]
        )
        if not picked:
            return
        try:
            rel = profile_set_avatar(picked)
        except Exception as exc:
            messagebox.showerror("LUNARIX", f"{self.tr('profile_avatar_error')}\n{exc}")
            return
        self.config_data["avatar_path"] = rel
        save_config(self.config_data)
        self._refresh_profile_view()

    def _profile_remove_avatar(self):
        profile_clear_avatar()
        self.config_data["avatar_path"] = ""
        save_config(self.config_data)
        self._refresh_profile_view()

    def _profile_save(self):
        name = self.profile_name_entry.get().strip()
        if len(name) > 24:
            messagebox.showwarning("LUNARIX", self.tr("profile_name_long"))
            return
        self.config_data["display_name"] = name
        self.config_data["share_cosmetics"] = bool(self.profile_share_cb.get())
        self.config_data["see_other_cosmetics"] = bool(self.profile_see_cb.get())
        if save_config(self.config_data):
            profile_export(self.config_data)
            self._refresh_profile_view()
            messagebox.showinfo("LUNARIX", self.tr("profile_saved"))

    # ══════════════════════════════════════════════════════════════════════════
    #  3. SETTINGS VIEW
    # ══════════════════════════════════════════════════════════════════════════
    def _init_settings_view(self):
        self.settings_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        scroll = ctk.CTkScrollableFrame(self.settings_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        def glass_card(parent):
            return ctk.CTkFrame(
                parent, fg_color="transparent",
                corner_radius=18, border_width=1, border_color="#38bdf8"
            )

        card_lang = glass_card(scroll)
        card_lang.pack(fill="x", pady=5)
        self.lbl_s_lang = ctk.CTkLabel(
            card_lang, text=self.tr("settings_lang"),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.lbl_s_lang.pack(anchor="w", padx=16, pady=(12, 4))

        current_lang_str = LANG_MAP_REV.get(self.lang, "Українська")
        self.lang_seg = ctk.CTkSegmentedButton(
            card_lang,
            values=["Українська", "English", "Русский"],
            selected_color=ACCENT_BLUE,
            selected_hover_color=ACCENT_BLUE_HOVER,
            command=self._on_language_select
        )
        self.lang_seg.set(current_lang_str)
        self.lang_seg.pack(anchor="w", padx=16, pady=(0, 12))

        card_dir = glass_card(scroll)
        card_dir.pack(fill="x", pady=5)
        self.lbl_s_gamedir = ctk.CTkLabel(
            card_dir, text=self.tr("settings_gamedir"),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.lbl_s_gamedir.pack(anchor="w", padx=16, pady=(12, 4))

        d_row = ctk.CTkFrame(card_dir, fg_color="transparent")
        d_row.pack(fill="x", padx=16, pady=(0, 12))
        self.gamedir_entry = ctk.CTkEntry(
            d_row, height=34, font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS, corner_radius=10
        )
        self.gamedir_entry.insert(0, self.config_data.get("game_dir", ""))
        self.gamedir_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.btn_s_browse_dir = ctk.CTkButton(
            d_row, text=self.tr("browse"), width=80, height=34,
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=10,
            command=self._browse_gamedir
        )
        self.btn_s_browse_dir.pack(side="right")

        card_ram = glass_card(scroll)
        card_ram.pack(fill="x", pady=5)

        top_ram = ctk.CTkFrame(card_ram, fg_color="transparent")
        top_ram.pack(fill="x", padx=16, pady=(12, 4))
        self.lbl_s_ram = ctk.CTkLabel(
            top_ram, text=self.tr("settings_ram"),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.lbl_s_ram.pack(side="left")
        self.ram_val_badge = ctk.CTkLabel(
            top_ram, text=f"{self.config_data.get('ram_gb', 4)} GB",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=ACCENT_CYAN
        )
        self.ram_val_badge.pack(side="right")

        self.ram_slider = ctk.CTkSlider(
            card_ram, from_=2, to=24, number_of_steps=22, height=16,
            button_color=ACCENT_BLUE, progress_color=ACCENT_BLUE,
            command=self._on_ram_slider_change
        )
        self.ram_slider.set(self.config_data.get("ram_gb", 4))
        self.ram_slider.pack(fill="x", padx=16, pady=(2, 12))

        card_java = glass_card(scroll)
        card_java.pack(fill="x", pady=5)
        self.lbl_s_java = ctk.CTkLabel(
            card_java, text=self.tr("settings_java"),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.lbl_s_java.pack(anchor="w", padx=16, pady=(12, 4))

        j_row = ctk.CTkFrame(card_java, fg_color="transparent")
        j_row.pack(fill="x", padx=16, pady=(0, 12))
        self.java_entry = ctk.CTkEntry(
            j_row, height=34, font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS, corner_radius=10
        )
        self.java_entry.insert(0, self.config_data.get("java_path", ""))
        self.java_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.btn_s_auto_java = ctk.CTkButton(
            j_row, text=self.tr("auto"), width=55, height=34,
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=10,
            command=self._autodetect_java
        )
        self.btn_s_auto_java.pack(side="right")
        self.btn_s_browse_java = ctk.CTkButton(
            j_row, text=self.tr("browse"), width=80, height=34,
            fg_color=BG_GLASS_INNER, hover_color="#182c4d", corner_radius=10,
            command=self._browse_java
        )
        self.btn_s_browse_java.pack(side="right", padx=(0, 6))

        card_disp = glass_card(scroll)
        card_disp.pack(fill="x", pady=5)
        self.lbl_s_display = ctk.CTkLabel(
            card_disp, text=self.tr("settings_display"),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.lbl_s_display.pack(anchor="w", padx=16, pady=(12, 4))

        r_row = ctk.CTkFrame(card_disp, fg_color="transparent")
        r_row.pack(fill="x", padx=16, pady=(0, 6))
        self.lbl_s_width = ctk.CTkLabel(r_row, text=self.tr("settings_width"))
        self.lbl_s_width.pack(side="left", padx=(0, 4))
        self.width_entry = ctk.CTkEntry(
            r_row, width=70, height=30, fg_color=BG_GLASS_INNER,
            border_color=BORDER_GLASS, corner_radius=8
        )
        self.width_entry.insert(0, str(self.config_data.get("width", 1280)))
        self.width_entry.pack(side="left", padx=(0, 12))

        self.lbl_s_height = ctk.CTkLabel(r_row, text=self.tr("settings_height"))
        self.lbl_s_height.pack(side="left", padx=(0, 4))
        self.height_entry = ctk.CTkEntry(
            r_row, width=70, height=30, fg_color=BG_GLASS_INNER,
            border_color=BORDER_GLASS, corner_radius=8
        )
        self.height_entry.insert(0, str(self.config_data.get("height", 720)))
        self.height_entry.pack(side="left", padx=(0, 14))

        self.fullscreen_cb = ctk.CTkCheckBox(r_row, text=self.tr("settings_fullscreen"), text_color=TEXT_MUTED)
        if self.config_data.get("fullscreen"):
            self.fullscreen_cb.select()
        self.fullscreen_cb.pack(side="left")

        self.lbl_s_jvm = ctk.CTkLabel(
            card_disp, text=self.tr("settings_jvm"),
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.lbl_s_jvm.pack(anchor="w", padx=16, pady=(2, 1))
        self.jvm_entry = ctk.CTkEntry(
            card_disp, height=32, font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=BG_GLASS_INNER, border_color=BORDER_GLASS, corner_radius=10
        )
        self.jvm_entry.insert(0, self.config_data.get("jvm_args", ""))
        self.jvm_entry.pack(fill="x", padx=16, pady=(0, 12))

        card_perf = glass_card(scroll)
        card_perf.pack(fill="x", pady=5)
        self.lbl_s_perf = ctk.CTkLabel(
            card_perf, text="Продуктивність лаунчера",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.lbl_s_perf.pack(anchor="w", padx=16, pady=(12, 4))

        perf_row = ctk.CTkFrame(card_perf, fg_color="transparent")
        perf_row.pack(fill="x", padx=16, pady=(0, 12))

        self.anim_bg_cb = ctk.CTkCheckBox(
            perf_row, text="Живий анімований фон (відео)",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        if self.config_data.get("animated_background", False):
            self.anim_bg_cb.select()
        else:
            self.anim_bg_cb.deselect()
        self.anim_bg_cb.pack(side="left")

        self.btn_save_settings = ctk.CTkButton(
            scroll,
            text=self.tr("settings_save"),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
            height=42, corner_radius=12,
            command=self._save_settings_action
        )
        self.btn_save_settings.pack(fill="x", pady=(10, 10))

        # Clear launcher data & cache card
        card_clear = glass_card(scroll)
        card_clear.pack(fill="x", pady=(5, 14))

        ctk.CTkLabel(
            card_clear, text="Сховище даних (Program Files / lunarix launcher)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#f87171"
        ).pack(anchor="w", padx=16, pady=(12, 2))

        ctk.CTkLabel(
            card_clear, text=self.tr("settings_clear_data_desc"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_MUTED, wraplength=520, justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 10))

        self.btn_clear_data = ctk.CTkButton(
            card_clear,
            text=self.tr("settings_clear_data"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#991b1b", hover_color="#dc2626",
            height=38, corner_radius=10,
            command=self._clear_data_action
        )
        self.btn_clear_data.pack(anchor="w", padx=16, pady=(0, 12))



    # ══════════════════════════════════════════════════════════════════════════
    #  Language Switcher
    # ══════════════════════════════════════════════════════════════════════════
    def _on_language_select(self, val):
        new_lang = LANG_MAP.get(val, "uk")
        if new_lang != self.lang:
            self.lang = new_lang
            self.config_data["lang"] = new_lang
            save_config(self.config_data)
            self._retranslate_ui()

    def _retranslate_ui(self):
        for tab_id, lang_key, _ in self.tab_defs:
            if tab_id in self.nav_btns:
                self.nav_btns[tab_id].configure(text=self.tr(lang_key))

        self.lock_title_lbl.configure(text=self.tr("mods_locked_title"))
        self.lock_desc_lbl.configure(text=self.tr("mods_locked_desc"))
        self.lock_btn.configure(text=self.tr("btn_go_home"))

        self.btn_open_folder.configure(text=self.tr("btn_open_folder"))
        self.btn_refresh_list.configure(text=self.tr("btn_refresh_list"))
        self.mr_search_entry.configure(placeholder_text=self.tr("search_placeholder"))
        self.btn_mr_search.configure(text=self.tr("btn_search"))
        self.btn_page_prev.configure(text=self.tr("page_prev"))
        self.btn_page_next.configure(text=self.tr("page_next"))

        self.lbl_s_lang.configure(text=self.tr("settings_lang"))
        self.lbl_s_gamedir.configure(text=self.tr("settings_gamedir"))
        self.btn_s_browse_dir.configure(text=self.tr("browse"))
        self.lbl_s_ram.configure(text=self.tr("settings_ram"))
        self.lbl_s_java.configure(text=self.tr("settings_java"))
        self.btn_s_browse_java.configure(text=self.tr("browse"))
        self.btn_s_auto_java.configure(text=self.tr("auto"))
        self.lbl_s_display.configure(text=self.tr("settings_display"))
        self.lbl_s_width.configure(text=self.tr("settings_width"))
        self.lbl_s_height.configure(text=self.tr("settings_height"))
        self.fullscreen_cb.configure(text=self.tr("settings_fullscreen"))
        self.lbl_s_jvm.configure(text=self.tr("settings_jvm"))
        self.btn_save_settings.configure(text=self.tr("settings_save"))

        self._refresh_game_state()

    # ══════════════════════════════════════════════════════════════════════════
    #  Navigation
    # ══════════════════════════════════════════════════════════════════════════
    def _hide_all_tabs(self):
        frames = [
            getattr(self, 'home_frame', None),
            getattr(self, 'profile_frame', None),
            getattr(self, 'alts_frame', None),
            getattr(self, 'chat_frame', None),
            getattr(self, 'configs_frame', None),
            getattr(self, 'localcfg_frame', None),
            getattr(self, 'resourcepacks_frame', None),
            getattr(self, 'friends_frame', None),
            getattr(self, 'mods_frame', None),
            getattr(self, 'changelog_frame', None),
            getattr(self, 'settings_frame', None)
        ]
        for f in frames:
            if f is not None:
                try:
                    f.pack_forget()
                except Exception:
                    pass

    def _show_home(self):
        self._select_tab("home")
        self._hide_all_tabs()
        self.home_frame.pack(fill="both", expand=True)

    def _show_profile(self):
        self._select_tab("profile")
        self._hide_all_tabs()
        self._refresh_profile_view()
        self.profile_frame.pack(fill="both", expand=True)

    def _show_alts(self):
        self._select_tab("alts")
        self._hide_all_tabs()
        self.alts_frame.pack(fill="both", expand=True)
        self._load_alts_view()

    def _show_chat(self):
        self._select_tab("chat")
        self._hide_all_tabs()
        self.chat_frame.pack(fill="both", expand=True)
        self._load_chat_view()

    def _show_mods(self):
        self._select_tab("mods")
        self._hide_all_tabs()
        self.mods_frame.pack(fill="both", expand=True)
        self._refresh_game_state()
        self._load_modrinth_page()
        self._load_curseforge_mods_page()

    def _show_configs(self):
        self._select_tab("configs")
        self._hide_all_tabs()
        self.configs_frame.pack(fill="both", expand=True)
        self._load_cloud_configs()

    def _show_resourcepacks(self):
        self._select_tab("resourcepacks")
        self._hide_all_tabs()
        self.resourcepacks_frame.pack(fill="both", expand=True)
        self._load_community_resourcepacks()
        self._load_rp_modrinth_page()
        self._load_rp_curseforge_page()

    def _show_friends(self):
        self._select_tab("friends")
        self._hide_all_tabs()
        self.friends_frame.pack(fill="both", expand=True)
        self._load_friends_view()

    def _show_changelog(self):
        self._select_tab("changelog")
        self._hide_all_tabs()
        self.changelog_frame.pack(fill="both", expand=True)

    def _show_settings(self):
        self._select_tab("settings")
        self._hide_all_tabs()
        self.settings_frame.pack(fill="both", expand=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  Actions & Game State (Supabase Protected)
    # ══════════════════════════════════════════════════════════════════════════
    def _log(self, msg):
        pass

    def _on_ram_slider_change(self, val):
        self.ram_val_badge.configure(text=f"{int(val)} GB")

    def _browse_gamedir(self):
        d = filedialog.askdirectory(initialdir=self.gamedir_entry.get())
        if d:
            self.gamedir_entry.delete(0, "end")
            self.gamedir_entry.insert(0, d)
            self._refresh_game_state()

    def _browse_java(self):
        f = filedialog.askopenfilename(filetypes=[("Executables", "*.exe"), ("All files", "*.*")])
        if f:
            self.java_entry.delete(0, "end")
            self.java_entry.insert(0, f)

    def _autodetect_java(self):
        j = detect_java()
        self.java_entry.delete(0, "end")
        self.java_entry.insert(0, j)
        messagebox.showinfo("Java", f"Знайдено: {j}")

    def _save_settings_action(self):
        self.config_data["username"] = self.alt_switcher.get_username()
        self.config_data["game_dir"] = self.gamedir_entry.get().strip()
        self.config_data["ram_gb"] = int(self.ram_slider.get())
        self.config_data["java_path"] = self.java_entry.get().strip()
        self.config_data["jvm_args"] = self.jvm_entry.get().strip()
        self.config_data["fullscreen"] = bool(self.fullscreen_cb.get())
        if hasattr(self, 'anim_bg_cb'):
            was_animated = self.config_data.get("animated_background", False)
            new_animated = bool(self.anim_bg_cb.get())
            self.config_data["animated_background"] = new_animated
            if new_animated and not was_animated:
                self._start_video_playback()
            elif not new_animated and was_animated:
                self._stop_video_playback()
        self.config_data["lang"] = self.lang
        try:
            self.config_data["width"] = int(self.width_entry.get())
            self.config_data["height"] = int(self.height_entry.get())
        except Exception:
            pass

        if save_config(self.config_data):
            self._refresh_game_state()
            messagebox.showinfo(self.tr("tab_settings"), self.tr("saved_msg"))

    def _clear_data_action(self):
        resp = messagebox.askyesno(
            "Очищення даних LUNARIX",
            self.tr("settings_clear_confirm"),
            icon="warning"
        )
        if resp:
            clear_all_launcher_data()
            restart_launcher()

    def _open_mods_folder(self):
        md = os.path.join(self.config_data.get("game_dir", ""), "mods")
        os.makedirs(md, exist_ok=True)
        os.startfile(md)

    def _refresh_game_state(self):
        g_dir = self.config_data.get("game_dir", "")
        installed = is_game_installed(g_dir)

        # Protect launch button if not authenticated!
        if not self.is_authenticated:
            self.home_main_btn.configure(
                state="normal",
                text="🔒  УВІЙДІТЬ ДЛЯ ЗАПУСКУ",
                fg_color="#334155",
                hover_color="#475569"
            )
            self._update_progress(0, "Потрібно увійти в Supabase акаунт")
            return

        if installed:
            if not self.is_busy:
                self.home_main_btn.configure(
                    state="normal",
                    text=self.tr("btn_play"),
                    fg_color=ACCENT_BLUE,
                    hover_color=ACCENT_BLUE_HOVER
                )
                self._update_progress(0, "")

            self.mods_locked_card.pack_forget()
            self.mods_unlocked_container.pack(fill="both", expand=True)
            self._refresh_installed_mods_list()
        else:
            if not self.is_busy:
                self.home_main_btn.configure(
                    state="normal",
                    text=self.tr("btn_download"),
                    fg_color="#0284c7",
                    hover_color="#0369a1"
                )
                self._update_progress(0, self.tr("status_need_dl"))

            self.mods_unlocked_container.pack_forget()
            self.mods_locked_card.pack(fill="both", expand=True)

    def _refresh_installed_mods_list(self):
        for widget in self.installed_scroll.winfo_children():
            widget.destroy()

        mods_dir = os.path.join(self.config_data.get("game_dir", ""), "mods")
        if not os.path.exists(mods_dir):
            ctk.CTkLabel(self.installed_scroll, text=self.tr("empty_mods")).pack(pady=20)
            return

        jars = [f for f in os.listdir(mods_dir) if f.endswith(".jar")]
        if not jars:
            ctk.CTkLabel(self.installed_scroll, text=self.tr("empty_mods")).pack(pady=20)
            return

        for jar in sorted(jars):
            row = ctk.CTkFrame(
                self.installed_scroll, fg_color=BG_GLASS_CARD,
                corner_radius=10, border_width=1, border_color=BORDER_GLASS
            )
            row.pack(fill="x", padx=4, pady=3)

            f_path = os.path.join(mods_dir, jar)
            sz_mb = f"{os.path.getsize(f_path) / (1024 * 1024):.1f} MB"

            ctk.CTkLabel(
                row, text="🧩  " + jar,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=TEXT_WHITE
            ).pack(side="left", padx=12, pady=8)

            ctk.CTkLabel(
                row, text=sz_mb,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=TEXT_MUTED
            ).pack(side="right", padx=12)

    # ══════════════════════════════════════════════════════════════════════════
    #  Modrinth Search & Install
    # ══════════════════════════════════════════════════════════════════════════
    def _on_modrinth_search_submit(self):
        self.mr_query = self.mr_search_entry.get().strip()
        self.mr_page = 0
        self._load_modrinth_page()

    def _on_page_prev(self):
        if self.mr_page > 0:
            self.mr_page -= 1
            self._load_modrinth_page()

    def _on_page_next(self):
        max_page = max(0, (self.mr_total - 1) // self.mr_limit)
        if self.mr_page < max_page:
            self.mr_page += 1
            self._load_modrinth_page()

    def _load_modrinth_page(self):
        for widget in self.modrinth_scroll.winfo_children():
            widget.destroy()

        loading_lbl = ctk.CTkLabel(
            self.modrinth_scroll, text="Завантаження каталогу...",
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        loading_lbl.pack(pady=30)

        offset = self.mr_page * self.mr_limit

        def worker():
            hits, total = search_modrinth_mods(query=self.mr_query, limit=self.mr_limit, offset=offset)
            self.after(0, lambda: self._render_modrinth_page(hits, total, loading_lbl))

        threading.Thread(target=worker, daemon=True).start()

    def _render_modrinth_page(self, hits, total, loading_lbl):
        loading_lbl.destroy()
        self.mr_total = total
        max_page = max(1, (total + self.mr_limit - 1) // self.mr_limit)

        self.lbl_page_info.configure(text=self.tr("page_indicator", page=self.mr_page + 1, total=max_page))
        self.btn_page_prev.configure(state="normal" if self.mr_page > 0 else "disabled")
        self.btn_page_next.configure(state="normal" if self.mr_page < max_page - 1 else "disabled")

        if not hits:
            ctk.CTkLabel(
                self.modrinth_scroll, text="Нічого не знайдено",
                font=ctk.CTkFont(family="Segoe UI", size=13)
            ).pack(pady=30)
            return

        for item in hits:
            title = item.get("title", "Без назви")
            slug = item.get("slug", "")
            desc = item.get("description", "")
            dls = item.get("downloads", 0)
            icon_url = item.get("icon_url")

            card = ctk.CTkFrame(
                self.modrinth_scroll, fg_color=BG_GLASS_CARD,
                corner_radius=12, border_width=1, border_color=BORDER_GLASS
            )
            card.pack(fill="x", padx=4, pady=4)

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=(8, 2))

            icon_box = ctk.CTkLabel(top_row, text="", width=40, height=40)
            icon_box.pack(side="left", padx=(0, 10))

            if icon_url:
                def load_async(url=icon_url, lbl=icon_box):
                    pil_img = load_mod_icon_pil(url, size=(38, 38))
                    if pil_img:
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(38, 38))
                        self.after(0, lambda: lbl.configure(image=ctk_img))
                threading.Thread(target=load_async, daemon=True).start()

            title_box = ctk.CTkFrame(top_row, fg_color="transparent")
            title_box.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                title_box, text=title,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#60a5fa"
            ).pack(anchor="w")
            ctk.CTkLabel(
                title_box, text=f"⬇ {dls:,} downloads",
                font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_MUTED
            ).pack(anchor="w")

            ctk.CTkLabel(
                card, text=desc,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=TEXT_MUTED, wraplength=540, justify="left"
            ).pack(anchor="w", padx=10, pady=(4, 6))

            b_row = ctk.CTkFrame(card, fg_color="transparent")
            b_row.pack(fill="x", padx=10, pady=(0, 8))

            ctk.CTkButton(
                b_row,
                text=self.tr("btn_install"),
                width=120, height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
                corner_radius=10,
                command=lambda s=slug: self._install_modrinth_mod(s)
            ).pack(side="left")

    def _install_modrinth_mod(self, slug):
        mods_dir = os.path.join(self.config_data.get("game_dir", ""), "mods")
        self._update_progress(0.1, f"Завантаження {slug}...")

        def worker():
            self._log(f"[*] Завантаження моду '{slug}'...")
            success, msg = install_mod_from_modrinth(slug, mods_dir)
            if success:
                self._log(f"[✓] Встановлено: {msg}")
                self.after(0, lambda: messagebox.showinfo(self.tr("tab_mods"), self.tr("mod_installed_ok", name=msg)))
                self.after(0, self._refresh_installed_mods_list)
            else:
                self._log(f"[-] Помилка встановлення {slug}: {msg}")
                self.after(0, lambda: messagebox.showerror("Error", f"Failed: {msg}"))
            self.after(0, lambda: self._update_progress(0, ""))

        threading.Thread(target=worker, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    #  CurseForge Mods Search & Install
    # ══════════════════════════════════════════════════════════════════════════
    def _on_curseforge_mods_search_submit(self):
        self.cf_query = self.cf_search_entry.get().strip()
        self.cf_page = 0
        self._load_curseforge_mods_page()

    def _on_cf_page_prev(self):
        if self.cf_page > 0:
            self.cf_page -= 1
            self._load_curseforge_mods_page()

    def _on_cf_page_next(self):
        max_page = max(0, (self.cf_total - 1) // self.cf_limit)
        if self.cf_page < max_page:
            self.cf_page += 1
            self._load_curseforge_mods_page()

    def _load_curseforge_mods_page(self):
        for widget in self.curseforge_scroll.winfo_children():
            widget.destroy()

        loading_lbl = ctk.CTkLabel(
            self.curseforge_scroll, text="Завантаження CurseForge...",
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        loading_lbl.pack(pady=30)

        offset = self.cf_page * self.cf_limit

        def worker():
            hits, total = search_curseforge_mods(query=self.cf_query, limit=self.cf_limit, offset=offset)
            self.after(0, lambda: self._render_curseforge_mods_page(hits, total, loading_lbl))

        threading.Thread(target=worker, daemon=True).start()

    def _render_curseforge_mods_page(self, hits, total, loading_lbl):
        loading_lbl.destroy()
        self.cf_total = total
        max_page = max(1, (total + self.cf_limit - 1) // self.cf_limit)

        self.lbl_cf_page_info.configure(text=f"Сторінка {self.cf_page + 1} з {max_page}")
        self.btn_cf_page_prev.configure(state="normal" if self.cf_page > 0 else "disabled")
        self.btn_cf_page_next.configure(state="normal" if self.cf_page < max_page - 1 else "disabled")

        if not hits:
            ctk.CTkLabel(
                self.curseforge_scroll, text="Нічого не знайдено на CurseForge",
                font=ctk.CTkFont(family="Segoe UI", size=13)
            ).pack(pady=30)
            return

        for item in hits:
            mod_id = item.get("id")
            title = item.get("name", "Без назви")
            desc = item.get("summary", "")
            dls = item.get("downloadCount", 0)
            logo_info = item.get("logo", {})
            icon_url = logo_info.get("thumbnailUrl") if isinstance(logo_info, dict) else None

            card = ctk.CTkFrame(
                self.curseforge_scroll, fg_color=BG_GLASS_CARD,
                corner_radius=12, border_width=1, border_color=BORDER_GLASS
            )
            card.pack(fill="x", padx=4, pady=4)

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=(8, 2))

            icon_box = ctk.CTkLabel(top_row, text="🔥", width=40, height=40)
            icon_box.pack(side="left", padx=(0, 10))

            if icon_url:
                def load_async(url=icon_url, lbl=icon_box):
                    pil_img = load_curseforge_icon_pil(url, size=(38, 38))
                    if pil_img:
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(38, 38))
                        self.after(0, lambda: lbl.configure(image=ctk_img))
                threading.Thread(target=load_async, daemon=True).start()

            title_box = ctk.CTkFrame(top_row, fg_color="transparent")
            title_box.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                title_box, text=title,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#f97316"
            ).pack(anchor="w")
            ctk.CTkLabel(
                title_box, text=f"🔥 CurseForge · ⬇ {dls:,} downloads",
                font=ctk.CTkFont(family="Segoe UI", size=10), text_color=TEXT_MUTED
            ).pack(anchor="w")

            ctk.CTkLabel(
                card, text=desc,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=TEXT_MUTED, wraplength=540, justify="left"
            ).pack(anchor="w", padx=10, pady=(4, 6))

            b_row = ctk.CTkFrame(card, fg_color="transparent")
            b_row.pack(fill="x", padx=10, pady=(0, 8))

            ctk.CTkButton(
                b_row,
                text="Встановити",
                width=120, height=28,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color="#ea580c", hover_color="#f97316",
                corner_radius=10,
                command=lambda mid=mod_id, t=title: self._install_curseforge_mod(mid, t)
            ).pack(side="left")

    def _install_curseforge_mod(self, mod_id, mod_name):
        mods_dir = os.path.join(self.config_data.get("game_dir", ""), "mods")
        self._update_progress(0.1, f"Завантаження {mod_name}...")

        def worker():
            self._log(f"[*] Завантаження з CurseForge: '{mod_name}'...")
            success, msg = install_file_from_curseforge(mod_id, mods_dir, file_extension=".jar")
            if success:
                self._log(f"[✓] Встановлено: {msg}")
                self.after(0, lambda: messagebox.showinfo("CurseForge Моди", f"Мод '{msg}' успішно встановлено в mods/!"))
                self.after(0, self._refresh_installed_mods_list)
            else:
                self._log(f"[-] Помилка CurseForge: {msg}")
                self.after(0, lambda: messagebox.showerror("Помилка", f"Не вдалося встановити: {msg}"))
            self.after(0, lambda: self._update_progress(0, ""))

        threading.Thread(target=worker, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    #  Launch & Download Flow
    # ══════════════════════════════════════════════════════════════════════════
    def _on_home_main_btn_click(self):
        if not self.is_authenticated:
            self._show_auth_modal()
            return

        if getattr(self, "game_proc", None) is not None and self.game_proc.poll() is None:
            # Гра вже запущена — закриваємо/зупиняємо гру за запитом користувача
            self._log("[*] Зупинка клієнта...")
            try:
                self.game_proc.terminate()
            except Exception:
                try:
                    self.game_proc.kill()
                except Exception:
                    pass
            self.home_main_btn.configure(state="disabled", text="⏳  ЗУПИНКА...")
            return

        if self.is_busy:
            return

        g_dir = self.config_data.get("game_dir", "")
        installed = is_game_installed(g_dir)
        if not installed:
            self._start_download_flow()
        else:
            self._start_launch_flow()

    def _start_download_flow(self):
        self.is_busy = True
        self.home_main_btn.configure(state="disabled", text=self.tr("btn_downloading"))

        def worker():
            try:
                g_dir = self.config_data.get("game_dir", "")
                self._log("[*] Початок автоматичного завантаження...")
                install_or_update_game(g_dir, progress_cb=self._update_progress, log_cb=self._log)
                self.after(0, lambda: messagebox.showinfo("Готово", self.tr("download_done")))
            except Exception as e:
                self._log(f"[-] Помилка завантаження: {e}")
                self.after(0, lambda: messagebox.showerror("Помилка", f"{e}"))
            finally:
                self.is_busy = False
                self.after(0, lambda: self._update_progress(0, ""))
                self.after(0, self._refresh_game_state)

        threading.Thread(target=worker, daemon=True).start()

    def _start_launch_flow(self):
        self.is_busy = True
        self.home_main_btn.configure(state="disabled", text=self.tr("btn_launching"))

        uname = self.alt_switcher.get_username()
        self.config_data["username"] = uname
        save_config(self.config_data)

        def on_started(proc=None):
            self.game_proc = proc
            def _set_running():
                self.home_main_btn.configure(
                    state="normal",
                    text=self.tr("btn_running"),
                    fg_color="#dc2626",
                    hover_color="#b91c1c"
                )
                self._update_progress(0, self.tr("status_client_running"))
            self.after(0, _set_running)

        def worker():
            try:
                g_dir = self.config_data.get("game_dir", "")
                self._update_progress(0.3, "Перевірка файлів...")
                install_or_update_game(g_dir, progress_cb=self._update_progress, log_cb=self._log)

                self._update_progress(0.9, "Запуск клієнта...")
                self._log("[*] Запуск гри...")
                started = launch_minecraft(
                    self.config_data,
                    log_cb=self._log,
                    on_exit_cb=self._on_game_exit,
                    on_start_cb=on_started
                )
                if not started:
                    self._log("[-] Запуск скасовано — перевірте шлях до Java у налаштуваннях.")
                    self.after(0, lambda: self._update_progress(0, "Помилка запуску: перевірте Java"))
                    self.after(0, self._on_game_exit)
                    return
                # launch_minecraft міг підібрати інший шлях до Java — зберігаємо його
                if self.config_data.get("java_path"):
                    save_config(self.config_data)
            except Exception as e:
                self._log(f"[-] Помилка: {e}")
                self.after(0, lambda: self._update_progress(0, f"Помилка: {e}"))
                self.after(0, self._on_game_exit)

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress(self, pct, text):
        def _update():
            self.glass_progress.set(pct)
            if pct > 0:
                pct_str = f"{int(pct * 100)}%"
                self.status_stage_lbl.configure(text=text)
                self.status_pct_lbl.configure(text=pct_str)
            else:
                self.status_stage_lbl.configure(text=text if text else "")
                self.status_pct_lbl.configure(text="")
        self.after(0, _update)

    def _on_game_exit(self):
        def _reset():
            self.game_proc = None
            self.is_busy = False
            self._update_progress(0, "")
            self._refresh_game_state()
        self.after(0, _reset)


if __name__ == "__main__":
    cleanup_launcher_update_leftovers()
    app = LunarixLauncherApp()
    app.mainloop()
