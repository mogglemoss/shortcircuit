# brands.py
"""
Brand packs: a corp's look, in the same brand.json format the Tripwire fork
uses, so one pack themes a corp's map and its router alike.

A pack is a folder holding brand.json (plus images). Short Circuit reads
its names, accents and both palettes and maps them onto the theme's UI
tokens. Data colors (security, classes, status) are never taken from a
pack: they carry meaning and stay the same in every brand.

Packs come from two places:

- bundled: src/shortcircuit/brand_packs/<slug>/, git-ignored except its README.
  The public app ships none; a corp's private build copies its pack in.
- imported: a pilot picks a pack folder from the Appearance menu and it is
  copied to their user data directory.

brand.json is untrusted input (a corp leader hands it around), and its
colors end up in Qt stylesheets and rich text, so only plain #rrggbb
values are accepted and names are treated as plain text.
"""

import json
import os
import re
import shutil
import sys

from appdirs import AppDirs

from shortcircuit import __appslug__

from .model.logger import Logger

BRAND_FILE = "brand.json"
SLUG_RE = re.compile(r"^[a-z0-9-]{1,40}$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
# What import copies besides brand.json: images the pack's logos/icons use.
ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
MAX_ASSET_BYTES = 2 * 1024 * 1024
MAX_BRAND_JSON_BYTES = 256 * 1024
MIN_TEXT_CONTRAST = 4.5


# ----- where packs live -----

def bundled_dir():
  if getattr(sys, "frozen", False):
    return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "brand_packs")
  return os.path.join(os.path.dirname(os.path.abspath(__file__)), "brand_packs")


def user_dir():
  return os.path.join(AppDirs(__appslug__, "secondfry").user_data_dir, "brands")


def list_packs():
  """Available packs as [{slug, name, path, imported}], sorted by name.
  An imported pack overrides a bundled one with the same slug."""
  found = {}
  for base, imported in ((bundled_dir(), False), (user_dir(), True)):
    if not os.path.isdir(base):
      continue
    for slug in sorted(os.listdir(base)):
      path = os.path.join(base, slug)
      if not SLUG_RE.match(slug) or not os.path.isfile(os.path.join(path, BRAND_FILE)):
        continue
      pack = load_pack(path)
      if pack is None:
        continue
      found[slug] = {"slug": slug, "name": pack["name"], "path": path, "imported": imported}
  return sorted(found.values(), key=lambda p: p["name"].lower())


def find_pack(slug):
  for pack in list_packs():
    if pack["slug"] == slug:
      return pack
  return None


# ----- reading a pack -----

def _read_brand_json(path):
  file = os.path.join(path, BRAND_FILE)
  if os.path.getsize(file) > MAX_BRAND_JSON_BYTES:
    raise ValueError("brand.json is too large")
  with open(file, "r", encoding="utf-8") as f:
    data = json.load(f)
  if not isinstance(data, dict):
    raise ValueError("brand.json must contain a JSON object")
  return data


def _hex(value):
  return value if isinstance(value, str) and HEX_RE.match(value) else None


def _rgb(h):
  return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _to_hex(rgb):
  return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c))) for c in rgb))


def _mix(a, b, t):
  ra, rb = _rgb(a), _rgb(b)
  return _to_hex([x + (y - x) * t for x, y in zip(ra, rb)])


def _luminance(h):
  def channel(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
  r, g, b = (channel(c) for c in _rgb(h))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
  hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
  return (hi + 0.05) / (lo + 0.05)


def _readable_on(color, background):
  """`color`, nudged toward black or white just enough to read as text
  on `background`; the corp's hue survives, only the shade moves."""
  if contrast(color, background) >= MIN_TEXT_CONTRAST:
    return color
  target = "#000000" if _luminance(background) > 0.18 else "#ffffff"
  for step in range(1, 21):
    candidate = _mix(color, target, step / 20)
    if contrast(candidate, background) >= MIN_TEXT_CONTRAST:
      return candidate
  return target


def _label_on(fill, preferred):
  """Text color for a button filled with `fill`: the pack's choice if it
  reads, else whichever of near-black / white reads better."""
  if preferred and contrast(preferred, fill) >= MIN_TEXT_CONTRAST:
    return preferred
  return max(("#111111", "#ffffff"), key=lambda c: contrast(c, fill))


def _mode_tokens(palette, accent, on_accent, mode):
  """Map one mode of a Tripwire palette onto Short Circuit's UI tokens.
  Returns only the tokens the pack can supply; the theme's defaults fill
  the rest."""
  p = {k: _hex(v) for k, v in (palette or {}).items()}
  bg, card, muted = p.get("background"), p.get("card"), p.get("muted")
  if not (bg and card and p.get("foreground")):
    return {}

  out = {
    "window": bg,
    "panel": card,
    "field": p.get("input") or muted,
    "sidebar_edge": p.get("border-soft"),
    "border": p.get("border"),
    "divider": p.get("border-soft"),
    "hover_surface": p.get("accent-surface") or muted,
    "scroll_handle": p.get("border-strong"),
    "text": p.get("foreground"),
    "text_strong": p.get("foreground"),
    "text_secondary": p.get("text-body"),
    "text_faint": p.get("muted-foreground"),
    "on_button": p.get("foreground"),
  }
  if muted:
    out["row_alt"] = _mix(card, muted, 0.5)
  if mode == "dark":
    out.update({
      "button": p.get("border"),
      "button_hover": p.get("border-strong"),
      "button_pressed": p.get("border-soft"),
      "button_disabled": p.get("border-soft"),
      "selection": p.get("border"),
    })
  else:
    out.update({
      "button": p.get("border-soft"),
      "button_hover": p.get("border"),
      "button_pressed": p.get("border-strong"),
      "button_disabled": muted,
      "selection": p.get("border-soft"),
    })

  accent = _hex(accent)
  if accent:
    out.update({
      "focus": accent,
      "primary_top": accent,
      "primary_bottom": _mix(accent, "#000000", 0.15),
      "primary_hover": _mix(accent, "#ffffff", 0.12),
      "on_primary": _label_on(accent, _hex(on_accent)),
      # Links are text: same hue, but always legible on the panels.
      "link": _readable_on(accent, card),
    })
  return {k: v for k, v in out.items() if v}


def load_pack(path):
  """Parse a pack folder into {slug, name, short, ui: {dark, light}}, or
  None (logged) when it can't be used."""
  try:
    data = _read_brand_json(path)
  except (OSError, ValueError) as e:
    Logger.warning("Brand pack {} unreadable: {}".format(path, e))
    return None

  palette = data.get("palette") if isinstance(data.get("palette"), dict) else {}
  accent = data.get("accent") if isinstance(data.get("accent"), dict) else {}
  ui = {
    mode: _mode_tokens(palette.get(mode), accent.get(mode), accent.get("on-" + mode), mode)
    for mode in ("dark", "light")
  }
  if not ui["dark"] and not ui["light"]:
    Logger.warning("Brand pack {} has no usable palette".format(path))
    return None

  slug = os.path.basename(os.path.normpath(path))
  corp = data.get("corp") if isinstance(data.get("corp"), str) else ""
  short = data.get("short") if isinstance(data.get("short"), str) else ""
  name = (corp or short or slug).strip()[:60]
  return {"slug": slug, "name": name, "short": (short or name).strip()[:40], "ui": ui}


# ----- importing and removing -----

def slug_for(folder):
  slug = re.sub(r"[^a-z0-9-]+", "-", os.path.basename(os.path.normpath(folder)).lower()).strip("-")
  return slug[:40] or "brand"


def import_pack(folder):
  """Copy a pack folder into the user's brand directory. Only brand.json
  and image files are copied, never anything else in the folder. Returns
  the slug; raises ValueError with a message for the pilot otherwise."""
  if not os.path.isfile(os.path.join(folder, BRAND_FILE)):
    raise ValueError("That folder has no brand.json in it.")
  if load_pack(folder) is None:
    raise ValueError("brand.json in that folder has no usable colors.")

  slug = slug_for(folder)
  dest = os.path.join(user_dir(), slug)
  staging = dest + ".importing"
  shutil.rmtree(staging, ignore_errors=True)
  os.makedirs(staging)
  try:
    shutil.copyfile(os.path.join(folder, BRAND_FILE), os.path.join(staging, BRAND_FILE))
    for name in os.listdir(folder):
      src = os.path.join(folder, name)
      if (
        os.path.splitext(name)[1].lower() in ASSET_EXTENSIONS
        and os.path.isfile(src)
        and not os.path.islink(src)
        and os.path.getsize(src) <= MAX_ASSET_BYTES
      ):
        shutil.copyfile(src, os.path.join(staging, name))
    shutil.rmtree(dest, ignore_errors=True)
    os.replace(staging, dest)
  except OSError:
    shutil.rmtree(staging, ignore_errors=True)
    raise
  Logger.info("Imported brand pack '{}' from {}".format(slug, folder))
  return slug


def remove_pack(slug):
  """Delete an imported pack. Bundled packs can't be removed."""
  if not SLUG_RE.match(slug or ""):
    return False
  path = os.path.join(user_dir(), slug)
  if not os.path.isdir(path):
    return False
  shutil.rmtree(path)
  Logger.info("Removed brand pack '{}'".format(slug))
  return True
