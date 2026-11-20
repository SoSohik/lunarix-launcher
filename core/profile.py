"""Launcher profile: display name, avatar and game-side export.

The account username (nickname) is never changed here. Only the display name
and the avatar are user-editable; both are exported for the game client into
``<game_dir>/lunarix/profile`` and passed through ``-Dlunarix.*`` properties.
"""

import json
import os
import shutil

from core.config import get_base_dir, get_data_dir

AVATAR_RELATIVE = os.path.join("profile", "avatar.png")
AVATAR_SIZE = 256


def profile_dir():
    new_dir = os.path.join(get_data_dir(), "profile")
    old_dir = os.path.join(get_base_dir(), "profile")
    if not os.path.exists(new_dir) and os.path.isdir(old_dir):
        try:
            shutil.copytree(old_dir, new_dir)
        except OSError:
            pass
    return new_dir


def avatar_file():
    return os.path.join(profile_dir(), "avatar.png")


def avatar_path(cfg=None):
    """Return an absolute path to the saved avatar, or ``None``."""
    if cfg is not None:
        rel = (cfg.get("avatar_path") or "").strip()
        if not rel:
            return None
        path = rel if os.path.isabs(rel) else os.path.join(get_data_dir(), rel)
        return path if os.path.exists(path) else None
    path = avatar_file()
    return path if os.path.exists(path) else None


def display_name(cfg):
    name = (cfg.get("display_name") or "").strip()
    if not name:
        name = (cfg.get("username") or "").strip()
    return name or "Player"


def set_avatar_from_file(source_path):
    """Crop the picked image to a centred square, resize and store as PNG."""
    from PIL import Image, ImageOps

    os.makedirs(profile_dir(), exist_ok=True)
    with Image.open(source_path) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGBA")
        side = min(image.width, image.height)
        left = (image.width - side) // 2
        top = (image.height - side) // 2
        image = image.crop((left, top, left + side, top + side))
        image = image.resize((AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)
        image.save(avatar_file(), "PNG")
    return AVATAR_RELATIVE


def clear_avatar():
    path = avatar_file()
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def export_profile(cfg):
    """Copy the profile into the game directory so the client can read it."""
    game_dir = (cfg.get("game_dir") or "").strip()
    if not game_dir:
        return None

    out_dir = os.path.join(game_dir, "lunarix", "profile")
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError:
        return None

    avatar_rel = ""
    source = avatar_path(cfg)
    if source:
        try:
            shutil.copy2(source, os.path.join(out_dir, "avatar.png"))
            avatar_rel = "lunarix/profile/avatar.png"
        except OSError:
            avatar_rel = ""

    data = {
        "username": (cfg.get("username") or "Player"),
        "displayName": display_name(cfg),
        "avatar": avatar_rel,
        "shareCosmetics": bool(cfg.get("share_cosmetics", True)),
        "seeOtherCosmetics": bool(cfg.get("see_other_cosmetics", True)),
    }
    target = os.path.join(out_dir, "profile.json")
    try:
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
    except OSError:
        return None
    return target
