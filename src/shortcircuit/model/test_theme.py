# test_theme.py
"""Color tokens and light/dark mode."""

import os

# The suite is headless: select the Qt platform plugin before Qt is imported.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import re

import pytest
from PySide6 import QtWidgets

from shortcircuit.theme import DARK, DATA_DARK, DATA_LIGHT, LIGHT, MODES, Theme


@pytest.fixture(scope="session")
def qapp():
  app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  yield app


def _luminance(hex_color):
  r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
  f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contrast(a, b):
  hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
  return (hi + 0.05) / (lo + 0.05)


def test_both_modes_define_the_same_tokens():
  assert DARK.keys() == LIGHT.keys()
  assert DATA_DARK.keys() == DATA_LIGHT.keys()
  # A data token must never shadow a UI token (brand packs override UI only).
  assert not (DARK.keys() & DATA_DARK.keys())


def test_every_stylesheet_token_resolves_in_both_modes(qapp):
  from shortcircuit.app import MAIN_QSS

  used = set(re.findall(r"@([a-z_]+)", MAIN_QSS))
  assert used, "stylesheet should reference tokens"
  for ui, data in ((DARK, DATA_DARK), (LIGHT, DATA_LIGHT)):
    missing = used - set(ui) - set(data)
    assert not missing, missing


def test_qss_substitutes_and_rejects_unknown_tokens(qapp):
  t = Theme()
  t.set_mode("dark")
  assert t.qss("color: @text;") == "color: {};".format(DARK["text"])
  with pytest.raises(KeyError):
    t.qss("color: @no_such_token;")


def test_mode_cycle_and_change_signal(qapp):
  t = Theme()
  t.set_mode("dark")
  fired = []
  t.changed.connect(lambda: fired.append(t.mode))

  assert t.next_mode() == MODES[(MODES.index("dark") + 1) % len(MODES)]
  t.set_mode("light")
  assert not t.is_dark()
  assert t["text"] == LIGHT["text"]
  t.set_mode("light")  # no change, no signal
  t.set_mode("dark")
  assert t.is_dark()
  assert fired == ["light", "dark"]


def test_unknown_mode_falls_back_to_system(qapp):
  t = Theme()
  t.set_mode("dark")
  t.set_mode("sepia")
  assert t.mode == "system"


@pytest.mark.parametrize("fg,bg", [
  ("text", "panel"), ("text", "window"), ("text", "field"),
  ("text_secondary", "panel"), ("text_secondary", "window"),
  ("text_faint", "panel"), ("link", "panel"),
  ("on_button", "button"), ("on_primary", "primary_top"),
  ("on_primary", "primary_bottom"), ("on_action", "action"),
])
def test_light_mode_text_meets_wcag_aa(fg, bg):
  assert _contrast(LIGHT[fg], LIGHT[bg]) >= 4.5


@pytest.mark.parametrize("fg", [
  "sec_hs", "sec_ls", "sec_ns", "sec_wh",
  "route_hs", "route_ls", "route_ns", "route_wh", "route_other",
  "status_ok", "status_error",
])
def test_light_mode_data_colors_meet_wcag_aa(fg):
  assert _contrast(DATA_LIGHT[fg], LIGHT["panel"]) >= 4.5
  assert _contrast(DATA_LIGHT[fg], LIGHT["row_alt"]) >= 4.5
