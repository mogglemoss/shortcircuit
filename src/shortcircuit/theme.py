# theme.py
"""
Color tokens and light/dark mode.

Every color the UI paints comes from here, by name. Two kinds of token:

- UI tokens (surfaces, text, borders, buttons, accents) describe the
  look. A future brand pack overrides these and only these.
- Data tokens (security classes, wormhole classes, status) encode meaning
  and stay fixed whatever the brand: HS is green in every pack. They still
  differ by mode, because a color readable on dark is often unreadable on
  light.

Stylesheets reference tokens as @name (see qss()). The dark set reproduces
the One Dark look the app had before tokens existed, value for value.
"""

import re

from PySide6 import QtCore, QtGui, QtWidgets

MODES = ("system", "light", "dark")

DARK = {
  "window": "#1b1e23",
  "panel": "#21252b",
  "sidebar_edge": "#181a1f",
  "field": "#282c34",
  "border": "#3e4451",
  "divider": "#2c313a",
  "row_alt": "#242933",
  "hover_surface": "#232830",
  "selection": "#3e4451",
  "scroll_handle": "#4b5263",
  "button": "#3e4451",
  "button_hover": "#4b5263",
  "button_pressed": "#2c313a",
  "button_disabled": "#2c313a",
  "on_button": "#ffffff",
  "text": "#dcdcdc",
  "text_strong": "#ffffff",
  "text_secondary": "#abb2bf",
  "text_faint": "#5c6370",
  "focus": "#00aaff",
  "link": "#61afef",
  "primary_top": "#007acc",
  "primary_bottom": "#005c99",
  "primary_hover": "#008ae6",
  "on_primary": "#ffffff",
  "action": "#b38600",
  "action_hover": "#e6ac00",
  "on_action": "#1b1e23",
}

# Soft light: no surface is pure white. The app sits beside a very dark
# game client, often at night, where a #ffffff window glares; off-white
# panels read calm while text keeps ~15:1 contrast.
LIGHT = {
  "window": "#e2e5ea",
  "panel": "#f4f5f7",
  "sidebar_edge": "#cfd4db",
  "field": "#eaedf1",
  "border": "#c0c6cf",
  "divider": "#dfe2e7",
  "row_alt": "#eceff3",
  "hover_surface": "#e6ecf5",
  "selection": "#d0dff2",
  "scroll_handle": "#bcc2cb",
  "button": "#dce0e6",
  "button_hover": "#cfd4db",
  "button_pressed": "#c0c6cf",
  "button_disabled": "#e7eaee",
  "on_button": "#1f2328",
  "text": "#1f2328",
  "text_strong": "#0d1117",
  "text_secondary": "#454d58",
  "text_faint": "#646b75",
  "focus": "#0a72c2",
  "link": "#0a63b8",
  "primary_top": "#1271c0",
  "primary_bottom": "#0b5ea3",
  "primary_hover": "#1679cc",
  "on_primary": "#ffffff",
  "action": "#f0b429",
  "action_hover": "#ffc53d",
  "on_action": "#1f2328",
}

# Meaning-carrying colors: per mode, never per brand.
DATA_DARK = {
  # Security prioritization sliders
  "sec_hs": "#98c379",
  "sec_ls": "#e5c07b",
  "sec_ns": "#e06c75",
  "sec_wh": "#61afef",
  # Route table system classes
  "route_hs": "#81c784",
  "route_ls": "#fff176",
  "route_ns": "#e57373",
  "route_wh": "#4fc3f7",
  "route_other": "#e0e0e0",
  # Route table selection tint per class
  "pick_hs": "#3c5a3c",
  "pick_ls": "#5a5028",
  "pick_ns": "#5a3232",
  "pick_wh": "#32465a",
  "on_pick": "#ffffff",
  # Status
  "status_ok": "#98c379",
  "status_error": "#e06c75",
  "jump_count": "#e5c07b",
}

DATA_LIGHT = {
  "sec_hs": "#276b2b",
  "sec_ls": "#845800",
  "sec_ns": "#c62828",
  "sec_wh": "#1565c0",
  "route_hs": "#276b2b",
  "route_ls": "#8a5d00",
  "route_ns": "#c62828",
  "route_wh": "#1565c0",
  "route_other": "#454d58",
  "pick_hs": "#d5ecd6",
  "pick_ls": "#f4e6c3",
  "pick_ns": "#f6d6d6",
  "pick_wh": "#d4e4f5",
  "on_pick": "#0d1117",
  "status_ok": "#276b2b",
  "status_error": "#c62828",
  "jump_count": "#845800",
}

_TOKEN = re.compile(r"@([a-z_]+)")


class Theme(QtCore.QObject):
  """The active mode and its tokens. `changed` fires when colors change."""

  changed = QtCore.Signal()

  def __init__(self):
    super().__init__()
    self._mode = "system"
    self._app = None

  # ----- mode -----

  @property
  def mode(self):
    return self._mode

  def install(self, app, mode="system"):
    """Set the Fusion style and palette on `app` and start following the
    OS color scheme (used while mode is "system")."""
    self._app = app
    app.setStyle("Fusion")
    hints = QtGui.QGuiApplication.styleHints()
    if hasattr(hints, "colorSchemeChanged"):
      hints.colorSchemeChanged.connect(self._on_os_scheme_changed)
    self._mode = mode if mode in MODES else "system"
    self._apply_palette()

  def set_mode(self, mode):
    if mode not in MODES:
      mode = "system"
    if mode == self._mode:
      return
    was_dark = self.is_dark()
    self._mode = mode
    if self.is_dark() != was_dark:
      self._apply_palette()
      self.changed.emit()

  def next_mode(self):
    return MODES[(MODES.index(self._mode) + 1) % len(MODES)]

  def is_dark(self):
    if self._mode == "dark":
      return True
    if self._mode == "light":
      return False
    hints = QtGui.QGuiApplication.styleHints()
    scheme = hints.colorScheme() if hasattr(hints, "colorScheme") else None
    # Unknown (or an old Qt) falls back to dark, the app's original look.
    return scheme != QtCore.Qt.ColorScheme.Light

  def _on_os_scheme_changed(self, _scheme):
    if self._mode == "system":
      self._apply_palette()
      self.changed.emit()

  # ----- tokens -----

  def tokens(self):
    if self.is_dark():
      return {**DARK, **DATA_DARK}
    return {**LIGHT, **DATA_LIGHT}

  def __getitem__(self, name):
    return self.tokens()[name]

  def color(self, name):
    return QtGui.QColor(self[name])

  def qss(self, template):
    """Substitute @token references in a stylesheet. An unknown token
    raises KeyError rather than silently painting nothing."""
    tokens = self.tokens()
    return _TOKEN.sub(lambda m: tokens[m.group(1)], template)

  def _apply_palette(self):
    if self._app is None:
      return
    t = self.tokens()
    C = QtGui.QColor
    R = QtGui.QPalette.ColorRole
    palette = QtGui.QPalette()
    palette.setColor(R.Window, C(t["window"]))
    palette.setColor(R.WindowText, C(t["text"]))
    palette.setColor(R.Base, C(t["field"]))
    palette.setColor(R.AlternateBase, C(t["panel"]))
    palette.setColor(R.Text, C(t["text"]))
    palette.setColor(R.Button, C(t["panel"]))
    palette.setColor(R.ButtonText, C(t["text"]))
    palette.setColor(R.ToolTipBase, C(t["panel"]))
    palette.setColor(R.ToolTipText, C(t["text"]))
    palette.setColor(R.Highlight, C(t["focus"]))
    palette.setColor(R.HighlightedText, C(t["on_primary"]))
    palette.setColor(R.Link, C(t["focus"]))
    palette.setColor(R.PlaceholderText, C(t["text_faint"]))
    for role in (R.WindowText, R.Text, R.ButtonText):
      palette.setColor(QtGui.QPalette.ColorGroup.Disabled, role, C(t["text_faint"]))
    self._app.setPalette(palette)


theme = Theme()
