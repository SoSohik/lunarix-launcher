# -*- coding: utf-8 -*-
"""
Local Lunarix client configs management.

Configs live in the client's config directory (C:\\lunarix\\client1_21_11\\config)
as plain JSON files. Format (written by ru.mentions.config.ConfigManager):

{
  "modules": {
    "ModuleName": {"enabled": bool, "key": int, "settings": {name: value, ...}},
    ...
  },
  "menuBg": int,
  "guiState": {...}
}

Setting values are typed by the client setting class:
  BooleanSetting -> bool, SliderSetting -> float, ModeSetting/StringSetting -> str,
  BindSetting -> int (GLFW keycode, -1 = none, 0-7 = mouse buttons),
  ColorSetting -> int (ARGB), DragSetting -> {"x": f, "y": f},
  MultiBooleanSetting -> {name: bool}, BlockList/PixelGrid -> [str]
"""

import os
import re
import json
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, Menu

CLIENT_CONFIG_DIR = r"C:\lunarix\client1_21_11\config"

RESERVED_NAMES = {"cosmetics", "draggables", "proxy", "theme"}
WINDOWS_RESERVED = (
    {"con", "prn", "aux", "nul"}
    | {f"com{i}" for i in range(1, 10)}
    | {f"lpt{i}" for i in range(1, 10)}
)
_NAME_RE = re.compile(r"^[^\\/:*?\"<>|]+$")

BG = "#070e1c"
CARD = "#0b162c"
INNER = "#081020"
BORDER = "#1e3a5f"
BLUE = "#2563eb"
BLUE_H = "#1d4ed8"
CYAN = "#38bdf8"
TXT = "#f8fafc"
MUTED = "#8aa4c8"


# ──────────────────────────────────────────────────────────────────────────────
#  File operations
# ──────────────────────────────────────────────────────────────────────────────
def get_config_dir():
    return CLIENT_CONFIG_DIR


def validate_config_name(name):
    """Mirror of ConfigManager.validateName(). Returns error string or None."""
    name = (name or "").strip()
    if not name:
        return "Назва не може бути порожньою"
    if len(name) > 64:
        return "Назва занадто довга (макс. 64 символи)"
    if not _NAME_RE.match(name):
        return 'Назва містить заборонені символи \\ / : * ? " < > |'
    if ".." in name:
        return "Назва не може містити '..'"
    if name.startswith(".") or name.endswith("."):
        return "Назва не може починатися або закінчуватися крапкою"
    if name.lower().endswith(".json"):
        return "Назва не може закінчуватися на '.json'"
    if name.lower() in RESERVED_NAMES or name.lower() in WINDOWS_RESERVED:
        return "Ця назва зарезервована системою"
    return None


def _config_path(directory, name):
    return os.path.join(directory, f"{name}.json")


def list_local_configs(directory=None):
    """Returns list of dicts: name, path, size, mtime (sorted by name)."""
    directory = directory or CLIENT_CONFIG_DIR
    result = []
    if not os.path.isdir(directory):
        return result
    for fname in os.listdir(directory):
        if not fname.lower().endswith(".json"):
            continue
        name = fname[:-5]
        if name.lower() in RESERVED_NAMES:
            continue
        path = os.path.join(directory, fname)
        if not os.path.isfile(path):
            continue
        try:
            st = os.stat(path)
        except OSError:
            continue
        result.append({
            "name": name,
            "path": path,
            "size": st.st_size,
            "mtime": st.st_mtime,
        })
    result.sort(key=lambda c: c["name"].lower())
    return result


def create_config_file(name, directory=None):
    """Creates a new empty config. Returns path. Raises ValueError on bad name."""
    err = validate_config_name(name)
    if err:
        raise ValueError(err)
    directory = directory or CLIENT_CONFIG_DIR
    os.makedirs(directory, exist_ok=True)
    path = _config_path(directory, name.strip())
    if os.path.exists(path):
        raise ValueError(f"Конфіг '{name}' вже існує")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"modules": {}}, f, indent=2, ensure_ascii=False)
    return path


def rename_config_file(old_name, new_name, directory=None):
    directory = directory or CLIENT_CONFIG_DIR
    err = validate_config_name(new_name)
    if err:
        raise ValueError(err)
    old_path = _config_path(directory, old_name)
    new_path = _config_path(directory, new_name.strip())
    if not os.path.exists(old_path):
        raise ValueError("Конфіг не знайдено")
    if os.path.exists(new_path):
        raise ValueError(f"Конфіг '{new_name}' вже існує")
    os.rename(old_path, new_path)
    return new_path


def delete_config_file(name, directory=None):
    directory = directory or CLIENT_CONFIG_DIR
    path = _config_path(directory, name)
    if os.path.exists(path):
        os.remove(path)


def load_config_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


# ──────────────────────────────────────────────────────────────────────────────
#  GLFW key codes <-> names (subset used by Lunarix client)
# ──────────────────────────────────────────────────────────────────────────────
GLFW_NAMES = {
    32: "Space", 39: "Apostrophe", 44: "Comma", 45: "Minus", 46: "Period",
    47: "Slash", 59: "Semicolon", 61: "Equal", 91: "LeftBracket",
    92: "Backslash", 93: "RightBracket", 96: "GraveAccent",
    256: "Escape", 257: "Enter", 258: "Tab", 259: "Backspace", 260: "Insert",
    261: "Delete", 262: "Right", 263: "Left", 264: "Down", 265: "Up",
    266: "PageUp", 267: "PageDown", 268: "Home", 269: "End",
    280: "CapsLock", 281: "ScrollLock", 282: "NumLock", 283: "PrintScreen",
    284: "Pause", 340: "LeftShift", 341: "LeftControl", 342: "LeftAlt",
    343: "LeftSuper", 344: "RightShift", 345: "RightControl", 346: "RightAlt",
    347: "RightSuper", 348: "Menu", 161: "World1", 162: "World2",
}
for i in range(26):
    GLFW_NAMES[65 + i] = chr(ord("A") + i)
for i in range(10):
    GLFW_NAMES[48 + i] = str(i)
for i in range(25):
    GLFW_NAMES[290 + i] = f"F{i + 1}"
for i in range(10):
    GLFW_NAMES[320 + i] = f"KP_{i}"
GLFW_NAMES.update({
    330: "KP_Decimal", 331: "KP_Divide", 332: "KP_Multiply", 333: "KP_Subtract",
    334: "KP_Add", 335: "KP_Enter", 336: "KP_Equal",
})
MOUSE_NAMES = {0: "LMB", 1: "RMB", 2: "MMB", 3: "Mouse4", 4: "Mouse5",
               5: "Mouse6", 6: "Mouse7", 7: "Mouse8"}


def key_name(code):
    if code is None or code == -1:
        return "n/a"
    if isinstance(code, int) and 0 <= code <= 7:
        return MOUSE_NAMES.get(code, f"Mouse{code + 1}")
    return GLFW_NAMES.get(code, f"Key {code}")


# tkinter keysym -> GLFW keycode (used while capturing a bind)
_SYM = {}
for ch in "abcdefghijklmnopqrstuvwxyz":
    _SYM[ch] = ord(ch.upper())
for d in "0123456789":
    _SYM[d] = ord(d)
_SYM.update({
    "space": 32, "apostrophe": 39, "comma": 44, "minus": 45, "period": 46,
    "slash": 47, "semicolon": 59, "equal": 61, "bracketleft": 91,
    "bracketright": 93, "backslash": 92, "grave": 96,
    "escape": 256, "return": 257, "enter": 257, "tab": 258, "backspace": 259,
    "insert": 260, "delete": 261, "right": 262, "left": 263, "down": 264,
    "up": 265, "prior": 266, "next": 267, "page_up": 266, "page_down": 267,
    "home": 268, "end": 269, "caps_lock": 280, "scroll_lock": 281,
    "num_lock": 282, "print": 283, "pause": 284, "pause_break": 284,
    "iso_left_tab": 258, "backtab": 258,
    "shift_l": 340, "shift_r": 344, "control_l": 341, "control_r": 345,
    "alt_l": 342, "alt_r": 346, "super_l": 343, "super_r": 347,
    "win_l": 343, "win_r": 347, "menu": 348,
    "kp_0": 320, "kp_1": 321, "kp_2": 322, "kp_3": 323, "kp_4": 324,
    "kp_5": 325, "kp_6": 326, "kp_7": 327, "kp_8": 328, "kp_9": 329,
    "kp_decimal": 330, "kp_divide": 331, "kp_multiply": 332,
    "kp_subtract": 333, "kp_add": 334, "kp_enter": 335, "kp_equal": 336,
    # shifted symbols -> base key
    "exclam": 49, "at": 50, "numbersign": 51, "dollar": 52, "percent": 53,
    "asciicircum": 54, "ampersand": 55, "asterisk": 56, "parenleft": 57,
    "parenright": 48, "underscore": 45, "plus": 61, "braceleft": 91,
    "braceright": 93, "bar": 92, "asciitilde": 96, "quotedbl": 39,
    "less": 44, "greater": 46, "question": 47, "colon": 59,
})
for i in range(1, 26):
    _SYM[f"f{i}"] = 289 + i

_MOUSE_BUTTON_GLVF = {"<Button-1>": 0, "<Button-2>": 1, "<Button-3>": 2,
                      "<Button-8>": 3, "<Button-9>": 4}


def _keysym_to_glfw(keysym):
    return _SYM.get((keysym or "").lower())


# ──────────────────────────────────────────────────────────────────────────────
#  Setting type inference (JSON has no type tags, so we guess + allow override)
# ──────────────────────────────────────────────────────────────────────────────
def infer_kind(value):
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        if -1 <= value <= 348:
            return "bind"
        if value < 0 or value > 0xFFFFFF:
            return "color"
        return "number"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "text"
    if isinstance(value, dict):
        if value and all(isinstance(v, bool) for v in value.values()):
            return "multibool"
        if set(value.keys()) == {"x", "y"} and all(
            isinstance(value.get(k), (int, float)) and not isinstance(value.get(k), bool)
            for k in ("x", "y")
        ):
            return "drag"
        return "json"
    if isinstance(value, list):
        return "jsonlist"
    return "json"


def _hex_to_int_argb(text):
    t = text.strip().lstrip("#")
    if len(t) == 6:
        v = 0xFF000000 | int(t, 16)
        return v - 0x100000000 if v >= 0x80000000 else v
    if len(t) == 8:
        v = int(t, 16)
        return v - 0x100000000 if v >= 0x80000000 else v
    raise ValueError


# ──────────────────────────────────────────────────────────────────────────────
#  Config editor window (text + graphical modes)
# ──────────────────────────────────────────────────────────────────────────────
class ConfigEditorWindow(ctk.CTkToplevel):
    """Editor for a single Lunarix client config JSON file."""

    def __init__(self, parent, name, path):
        super().__init__(parent)
        self.parent_app = parent
        self.name = name
        self.path = path
        self.data = None
        self.dirty = False
        self.mode = "gui"
        self._type_overrides = {}    # (module, setting) -> forced kind
        self._expanded = set()       # module names with open settings panel
        self._capturing = None       # callback(code) while waiting for a key
        self._capture_seqs = []      # (seq, func) pairs to remove
        self._module_switches = {}
        self._module_panels = {}
        self._module_chips = {}

        self.title(f"Конфіг: {name}")
        self.geometry("960x680")
        self.minsize(760, 520)
        self.configure(fg_color=BG)
        self.attributes("-topmost", True)

        self._center_on_parent()
        self._build_header()
        self._build_body()
        self._load_file()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── window chrome ──────────────────────────────────────────────────────
    def _center_on_parent(self):
        try:
            self.update_idletasks()
            px = self.parent_app.winfo_x() + (self.parent_app.winfo_width() - 960) // 2
            py = self.parent_app.winfo_y() + (self.parent_app.winfo_height() - 680) // 2
            self.geometry(f"960x680+{max(px, 0)}+{max(py, 0)}")
        except Exception:
            pass

    def _build_header(self):
        head = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDER)
        head.pack(fill="x", padx=14, pady=(14, 8))

        left = ctk.CTkFrame(head, fg_color="transparent")
        left.pack(side="left", padx=14, pady=12)
        ctk.CTkLabel(left, text=self.name,
                     font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                     text_color=CYAN).pack(anchor="w")
        ctk.CTkLabel(left, text=self.path,
                     font=ctk.CTkFont(family="Consolas", size=10),
                     text_color=MUTED).pack(anchor="w")

        self.mode_switch = ctk.CTkSegmentedButton(
            head, values=["Графічний", "Текст"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            selected_color=BLUE, selected_hover_color=BLUE_H,
            command=self._on_mode_change,
        )
        self.mode_switch.set("Графічний")
        self.mode_switch.pack(side="right", padx=(0, 8), pady=12)

        ctk.CTkButton(
            head, text="💾  Зберегти", width=110, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=BLUE, hover_color=BLUE_H, corner_radius=10,
            command=self._save,
        ).pack(side="right", padx=(0, 8), pady=12)

        ctk.CTkButton(
            head, text="↺  Перечитати", width=110, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=INNER, hover_color="#182c4d", text_color=TXT,
            corner_radius=10, command=self._reload_prompt,
        ).pack(side="right", padx=(0, 8), pady=12)

        ctk.CTkButton(
            head, text="✕  Закрити", width=90, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=INNER, hover_color="#182c4d", text_color=MUTED,
            corner_radius=10, command=self._on_close,
        ).pack(side="right", pady=12)

        self.hint = ctk.CTkLabel(
            self,
            text="ЛКМ на модулі — увімкнути/вимкнути · ПКМ на модулі — налаштування · "
                 "ЛКМ на клавіші — бинд (натисніть клавішу/кнопку миші, ESC або Backspace = скинути) · "
                 "ПКМ на назві налаштування — змінити тип поля",
            font=ctk.CTkFont(family="Segoe UI", size=10), text_color=MUTED,
        )
        self.hint.pack(fill="x", padx=18)

    def _build_body(self):
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=14, pady=(4, 14))

        self.text_box = ctk.CTkTextbox(
            self.body, font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=INNER, text_color=TXT, corner_radius=12,
            border_width=1, border_color=BORDER,
        )
        self.gui_scroll = ctk.CTkScrollableFrame(self.body, fg_color="transparent")

    # ── data load / save ───────────────────────────────────────────────────
    def _load_file(self):
        try:
            self.data = load_config_json(self.path)
            if not isinstance(self.data, dict):
                self.data = {"modules": {}}
        except Exception as e:
            self.data = {"modules": {}}
            messagebox.showwarning(
                "Увага",
                f"Не вдалося прочитати конфіг JSON:\n{e}\n\nВідкрито порожній документ.",
                parent=self)
        self.dirty = False
        self._show_mode(self.mode)

    def _on_mode_change(self, value):
        new_mode = "text" if value == "Текст" else "gui"
        if new_mode == "gui" and self.mode == "text":
            # pick up edits made in the text editor before switching
            raw = self.text_box.get("1.0", "end").strip()
            try:
                data = json.loads(raw) if raw else {"modules": {}}
                if isinstance(data, dict):
                    self.data = data
                else:
                    raise ValueError("root is not object")
            except Exception as e:
                messagebox.showerror("Помилка JSON",
                                     f"Виправте JSON у текстовому режимі перед перемиканням:\n{e}",
                                     parent=self)
                self.mode_switch.set("Текст")
                return
        self.mode = new_mode
        self._show_mode(self.mode)

    def _show_mode(self, mode):
        for w in (self.text_box, self.gui_scroll):
            try:
                w.pack_forget()
            except Exception:
                pass
        if mode == "text":
            self.text_box.pack(fill="both", expand=True)
            try:
                self.text_box.delete("1.0", "end")
                self.text_box.insert("1.0", json.dumps(self.data, indent=2, ensure_ascii=False))
            except Exception:
                pass
        else:
            self.gui_scroll.pack(fill="both", expand=True)
            self._render_gui()

    def _mark_dirty(self):
        self.dirty = True
        try:
            self.title(f"Конфіг: {self.name} *")
        except Exception:
            pass

    def _save(self):
        if self.mode == "text":
            raw = self.text_box.get("1.0", "end").strip()
            try:
                data = json.loads(raw) if raw else {"modules": {}}
            except Exception as e:
                messagebox.showerror("Помилка JSON", f"Некоректний JSON:\n{e}", parent=self)
                return
            if not isinstance(data, dict):
                messagebox.showerror("Помилка JSON", "Корінь конфігу має бути об'єктом {}", parent=self)
                return
            self.data = data
        try:
            save_config_json(self.path, self.data)
        except Exception as e:
            messagebox.showerror("Помилка збереження", str(e), parent=self)
            return
        self.dirty = False
        try:
            self.title(f"Конфіг: {self.name}")
        except Exception:
            pass
        messagebox.showinfo("Збережено", f"Конфіг '{self.name}' збережено.", parent=self)

    def _reload_prompt(self):
        if self.dirty and not messagebox.askyesno(
                "Перечитати", "Є незбережені зміни. Перечитати файл з диска і втратити їх?",
                parent=self):
            return
        self._load_file()

    def _on_close(self):
        if self.dirty:
            ans = messagebox.askyesnocancel(
                "Незбережені зміни", "Зберегти зміни перед закриттям?", parent=self)
            if ans is None:
                return
            if ans:
                self._save()
        self.destroy()

    # ── graphical mode ─────────────────────────────────────────────────────
    def _render_gui(self):
        for w in self.gui_scroll.winfo_children():
            w.destroy()
        self._module_switches = {}
        self._module_panels = {}
        self._module_chips = {}

        modules = self.data.get("modules")
        if not isinstance(modules, dict):
            modules = {}
            self.data["modules"] = modules

        if not modules:
            ctk.CTkLabel(
                self.gui_scroll, text="У конфізі немає модулів.",
                font=ctk.CTkFont(family="Segoe UI", size=13), text_color=MUTED,
            ).pack(pady=30)

        for mod_name in sorted(modules.keys(), key=str.lower):
            mod = modules.get(mod_name)
            if isinstance(mod, dict):
                self._build_module_card(mod_name, mod)

        extra_keys = [k for k in self.data.keys() if k != "modules"]
        if extra_keys:
            sep = ctk.CTkFrame(self.gui_scroll, height=1, fg_color=BORDER)
            sep.pack(fill="x", padx=6, pady=10)
            ctk.CTkLabel(
                self.gui_scroll, text="ПАРАМЕТРИ",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=MUTED,
            ).pack(anchor="w", padx=10)
            for key in extra_keys:
                self._build_setting_row(
                    self.gui_scroll, f"@{key}", str(key), self.data.get(key),
                    lambda v, k=key: self._set_top(k, v))

    def _set_top(self, key, value):
        self.data[key] = value
        self._mark_dirty()

    # ── module card ────────────────────────────────────────────────────────
    def _build_module_card(self, mod_name, mod):
        card = ctk.CTkFrame(self.gui_scroll, fg_color=CARD, corner_radius=12,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=6, pady=4)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 4))

        sw = ctk.CTkSwitch(header, text="", width=34, progress_color=BLUE,
                           command=lambda m=mod_name: self._toggle_module(m))
        if bool(mod.get("enabled", False)):
            sw.select()
        else:
            sw.deselect()
        self._module_switches[mod_name] = sw
        sw.pack(side="left", padx=(0, 8))

        name_lbl = ctk.CTkLabel(
            header, text=str(mod_name),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TXT, anchor="w",
        )
        name_lbl.pack(side="left", fill="x", expand=True)

        arrow = ctk.CTkLabel(
            header, text="▾" if mod_name in self._expanded else "▸",
            font=ctk.CTkFont(size=12), text_color=MUTED, width=16,
        )
        arrow.pack(side="right")

        key_val = mod.get("key", -1)
        chip = ctk.CTkButton(
            header, text=key_name(key_val), width=86, height=26,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            fg_color=INNER, hover_color="#1d3f78", text_color=CYAN,
            corner_radius=8, anchor="center",
            command=lambda m=mod_name, b=None: self._start_capture(
                self._module_chips[m],
                lambda code, mm=m, cc=self._module_chips[m]: self._set_module_key(mm, code, cc)),
        )
        chip.bind("<Button-3>", lambda e, m=mod_name, c=None: self._set_module_key(m, -1, None))
        chip.pack(side="right", padx=(6, 0))
        self._module_chips[mod_name] = chip

        for w in (header, name_lbl):
            w.bind("<Button-1>", lambda e, m=mod_name: self._toggle_module(m))
            w.bind("<Button-3>", lambda e, m=mod_name, a=arrow: self._toggle_expand(m, a))

        panel = ctk.CTkFrame(card, fg_color=INNER, corner_radius=10)
        self._module_panels[mod_name] = panel
        if mod_name in self._expanded:
            panel.pack(fill="x", padx=8, pady=(0, 8))
            self._fill_settings_panel(mod_name, mod, panel)

    def _toggle_module(self, mod_name):
        modules = self.data.get("modules") or {}
        mod = modules.get(mod_name)
        if not isinstance(mod, dict):
            return
        mod["enabled"] = not bool(mod.get("enabled", False))
        sw = self._module_switches.get(mod_name)
        if sw is not None:
            if mod["enabled"]:
                sw.select()
            else:
                sw.deselect()
        self._mark_dirty()

    def _toggle_expand(self, mod_name, arrow):
        modules = self.data.get("modules") or {}
        mod = modules.get(mod_name)
        if not isinstance(mod, dict):
            return
        panel = self._module_panels.get(mod_name)
        if panel is None:
            return
        if mod_name in self._expanded:
            self._expanded.discard(mod_name)
            panel.pack_forget()
            for w in panel.winfo_children():
                w.destroy()
            arrow.configure(text="▸")
        else:
            self._expanded.add(mod_name)
            arrow.configure(text="▾")
            panel.pack(fill="x", padx=8, pady=(0, 8))
            self._fill_settings_panel(mod_name, mod, panel)

    def _set_module_key(self, mod_name, code, chip=None):
        modules = self.data.get("modules") or {}
        mod = modules.get(mod_name)
        if not isinstance(mod, dict):
            return
        mod["key"] = int(code) if code is not None else -1
        self._mark_dirty()
        target = chip if chip is not None else self._module_chips.get(mod_name)
        if target is not None:
            try:
                target.configure(text=key_name(mod["key"]))
            except Exception:
                pass

    def _fill_settings_panel(self, mod_name, mod, panel):
        settings = mod.get("settings")
        if not isinstance(settings, dict) or not settings:
            ctk.CTkLabel(panel, text="Немає налаштувань",
                         font=ctk.CTkFont(size=11), text_color=MUTED).pack(anchor="w", padx=10, pady=8)
            return
        for sname in sorted(settings.keys(), key=str.lower):
            value = settings.get(sname)
            self._build_setting_row(
                panel, (mod_name, sname), str(sname), value,
                lambda v, m=mod_name, s=sname: self._set_setting(m, s, v),
            )

    def _set_setting(self, mod_name, sname, value):
        modules = self.data.get("modules") or {}
        mod = modules.get(mod_name)
        if isinstance(mod, dict) and isinstance(mod.get("settings"), dict):
            mod["settings"][sname] = value
            self._mark_dirty()

    # ── generic setting row ────────────────────────────────────────────────
    def _build_setting_row(self, parent, key, label, value, setter):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=3)

        kind = self._type_overrides.get(key) or infer_kind(value)

        lbl = ctk.CTkLabel(
            row, text=label,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=MUTED, anchor="w",
        )
        lbl.pack(side="left", fill="x", expand=True)

        holder = ctk.CTkFrame(row, fg_color="transparent")
        holder.pack(side="right")

        if kind == "bool":
            var = tk.BooleanVar(value=bool(value))
            ctk.CTkSwitch(holder, text="", width=90, variable=var,
                          progress_color=BLUE,
                          command=lambda: setter(bool(var.get()))).pack()

        elif kind == "bind":
            chip = ctk.CTkButton(
                holder, text=key_name(value), width=86, height=24,
                font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                fg_color=CARD, hover_color="#1d3f78", text_color=CYAN,
                corner_radius=8,
                command=lambda: self._start_capture(
                    chip, lambda code: self._apply_bind(chip, code, setter)),
            )
            chip.bind("<Button-3>", lambda e: self._apply_bind(chip, -1, setter))
            chip.pack()

        elif kind == "color":
            frame = ctk.CTkFrame(holder, fg_color="transparent")
            frame.pack()
            preview = ctk.CTkFrame(frame, width=34, height=20, corner_radius=6,
                                   fg_color=self._argb_to_hex(value) or CARD,
                                   border_width=1, border_color=BORDER)
            preview.pack(side="left", padx=(0, 6))
            entry = ctk.CTkEntry(frame, width=110, height=24,
                                 font=ctk.CTkFont(family="Consolas", size=11),
                                 fg_color=CARD, border_color=BORDER, text_color=TXT,
                                 corner_radius=8)
            entry.insert(0, self._argb_to_hex(value) or "#FFFFFFFF")
            entry.pack(side="left")

            def commit_color(e=None, ent=entry, pv=preview, st=setter, orig=value):
                try:
                    code = _hex_to_int_argb(ent.get())
                except Exception:
                    messagebox.showwarning("Колір", "Формат: #RRGGBB або #AARRGGBB",
                                           parent=self)
                    ent.delete(0, "end")
                    ent.insert(0, self._argb_to_hex(orig) or "#FFFFFFFF")
                    return
                st(code)
                pv.configure(fg_color=self._argb_to_hex(code) or CARD)

            entry.bind("<Return>", commit_color)
            entry.bind("<FocusOut>", commit_color)

        elif kind == "drag":
            frame = ctk.CTkFrame(holder, fg_color="transparent")
            frame.pack()
            xv = ctk.CTkEntry(frame, width=56, height=24, fg_color=CARD,
                              border_color=BORDER, text_color=TXT, corner_radius=8,
                              font=ctk.CTkFont(family="Consolas", size=11))
            yv = ctk.CTkEntry(frame, width=56, height=24, fg_color=CARD,
                              border_color=BORDER, text_color=TXT, corner_radius=8,
                              font=ctk.CTkFont(family="Consolas", size=11))
            xv.insert(0, str(value.get("x", 0)))
            yv.insert(0, str(value.get("y", 0)))
            xv.pack(side="left", padx=(0, 4))
            ctk.CTkLabel(frame, text="x", font=ctk.CTkFont(size=10),
                         text_color=MUTED).pack(side="left", padx=(0, 4))
            yv.pack(side="left", padx=(0, 4))
            ctk.CTkLabel(frame, text="y", font=ctk.CTkFont(size=10),
                         text_color=MUTED).pack(side="left")

            def commit_drag(e=None, xe=xv, ye=yv, st=setter):
                try:
                    st({"x": float(xe.get()), "y": float(ye.get())})
                except Exception:
                    pass

            xv.bind("<Return>", commit_drag)
            yv.bind("<Return>", commit_drag)
            xv.bind("<FocusOut>", commit_drag)
            yv.bind("<FocusOut>", commit_drag)

        elif kind == "number":
            is_float = isinstance(value, float)
            num = float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0
            frame = ctk.CTkFrame(holder, fg_color="transparent")
            frame.pack()
            ent = ctk.CTkEntry(frame, width=90, height=24, fg_color=CARD,
                               border_color=BORDER, text_color=TXT, corner_radius=8,
                               font=ctk.CTkFont(family="Consolas", size=11),
                               justify="right")
            ent.insert(0, "%g" % num)
            ent.pack(side="left", padx=(0, 6))

            if num >= 0:
                top = max(num * 1.5, num + 5.0, 10.0)
                slider = ctk.CTkSlider(
                    frame, from_=0.0, to=top, number_of_steps=200,
                    width=110, height=16, progress_color=BLUE,
                    button_color=CYAN, button_hover_color=TXT,
                    fg_color=BORDER,
                )
                slider.set(num)
                slider.pack(side="left")

                def on_slide(v, e=ent, st=setter, isf=is_float):
                    e.delete(0, "end")
                    e.insert(0, "%g" % v)
                    st(float(v) if isf else int(round(v)))

                slider.configure(command=on_slide)

            def commit_num(e=None, ent=ent, st=setter, isf=is_float, orig=value):
                try:
                    v = float(ent.get().strip())
                    st(v if isf else (int(v) if v == int(v) else v))
                except Exception:
                    ent.delete(0, "end")
                    ent.insert(0, str(orig))

            ent.bind("<Return>", commit_num)
            ent.bind("<FocusOut>", commit_num)

        elif kind == "multibool":
            frame = ctk.CTkFrame(holder, fg_color="transparent")
            frame.pack()
            inner = ctk.CTkFrame(frame, fg_color="transparent")
            inner.pack()
            toggles = {}
            for sub_name, sub_val in (value or {}).items():
                var = tk.BooleanVar(value=bool(sub_val))
                ctk.CTkSwitch(inner, text=str(sub_name), width=140,
                              font=ctk.CTkFont(family="Segoe UI", size=10),
                              progress_color=BLUE, variable=var).pack(anchor="w", pady=1)
                toggles[sub_name] = var

            def commit_multi(st=setter, tv=toggles):
                st({k: bool(v.get()) for k, v in tv.items()})

            for var in toggles.values():
                var.trace_add("write", lambda *a, c=commit_multi: c())

        else:  # text / json / jsonlist
            ent = ctk.CTkEntry(holder, width=150, height=24, fg_color=CARD,
                               border_color=BORDER, text_color=TXT, corner_radius=8,
                               font=ctk.CTkFont(family="Consolas", size=11))
            if kind in ("json", "jsonlist"):
                ent.insert(0, json.dumps(value, ensure_ascii=False))
            else:
                ent.insert(0, "" if value is None else str(value))
            ent.pack()

            def commit_text(e=None, ent=ent, st=setter, k=kind, orig=value):
                raw = ent.get()
                if k in ("json", "jsonlist"):
                    try:
                        st(json.loads(raw))
                    except Exception:
                        messagebox.showwarning(
                            "JSON", "Некоректний JSON — значення не збережено",
                            parent=self)
                        ent.delete(0, "end")
                        ent.insert(0, json.dumps(orig, ensure_ascii=False))
                else:
                    st(raw)

            ent.bind("<Return>", commit_text)
            ent.bind("<FocusOut>", commit_text)

        # RMB on the label opens a type-override menu for module settings
        if isinstance(key, tuple):
            def show_type_menu(event, k=key):
                auto_kind = infer_kind(value)
                current = self._type_overrides.get(k) or auto_kind
                menu = Menu(self, tearoff=0)
                for label, kind_val in [
                    ("Авто (за значенням)", "__auto__"),
                    ("Число", "number"), ("Бинд", "bind"), ("Колір", "color"),
                    ("Текст", "text"), ("JSON", "json"),
                ]:
                    effective = auto_kind if kind_val == "__auto__" else kind_val
                    mark = "● " if effective == current else "   "
                    menu.add_command(
                        label=mark + label,
                        command=lambda kv=kind_val, kk=k: self._set_type_override(
                            kk, None if kv == "__auto__" else kv),
                    )
                try:
                    menu.tk_popup(event.x_root, event.y_root)
                finally:
                    menu.grab_release()

            lbl.bind("<Button-3>", show_type_menu)

    def _set_type_override(self, key, kind):
        if kind is None:
            self._type_overrides.pop(key, None)
        else:
            self._type_overrides[key] = kind
        for mod_name in list(self._expanded):
            panel = self._module_panels.get(mod_name)
            if panel is not None:
                for w in panel.winfo_children():
                    w.destroy()
                mod = (self.data.get("modules") or {}).get(mod_name)
                if isinstance(mod, dict):
                    self._fill_settings_panel(mod_name, mod, panel)

    # ── bind capture ───────────────────────────────────────────────────────
    def _apply_bind(self, chip, code, setter):
        setter(code)
        try:
            chip.configure(text=key_name(code))
        except Exception:
            pass

    def _start_capture(self, chip, on_code):
        if self._capturing is not None:
            return
        self._capturing = on_code
        try:
            chip.configure(text="...")
        except Exception:
            pass

        def finish(code):
            cb = self._capturing
            self._capturing = None
            for seq in self._capture_seqs:
                try:
                    self.unbind(seq)
                except Exception:
                    pass
            self._capture_seqs = []
            if cb:
                cb(code)

        def on_key(event):
            if event.keysym in ("Escape", "BackSpace"):
                finish(-1)
                return "break"
            code = _keysym_to_glfw(event.keysym)
            if code is not None:
                finish(code)
                return "break"
            return None

        handlers = {"<Key>": on_key}
        for seq, code in _MOUSE_BUTTON_GLVF.items():
            handlers[seq] = (lambda c: lambda e: finish(c))(code)

        for seq, fn in handlers.items():
            self.bind(seq, fn)
            self._capture_seqs.append(seq)
        self.focus_force()

    def _argb_to_hex(self, v):
        if not isinstance(v, int) or isinstance(v, bool):
            return None
        h = f"#{(v & 0xFFFFFFFF):08X}"
        if h[1:3].upper() == "FF":
            return "#" + h[3:9]
        return h
