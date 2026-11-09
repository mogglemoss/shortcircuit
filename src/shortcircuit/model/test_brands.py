# test_brands.py
"""Brand packs: loading Tripwire-format packs, importing, and theming."""

import os

# The suite is headless: select the Qt platform plugin before Qt is imported.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
import shutil

import pytest
from PySide6 import QtCore, QtWidgets

from shortcircuit import brands
from shortcircuit.theme import DARK, DATA_DARK, DATA_LIGHT, Theme

EXAMPLE = os.path.join(os.path.dirname(__file__), "fixtures", "brand_example")


@pytest.fixture(scope="session")
def qapp():
  app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  yield app


@pytest.fixture
def dirs(tmp_path, monkeypatch):
  bundled, user = tmp_path / "bundled", tmp_path / "user"
  bundled.mkdir()
  monkeypatch.setattr(brands, "bundled_dir", lambda: str(bundled))
  monkeypatch.setattr(brands, "user_dir", lambda: str(user))
  return bundled, user


def _write_pack(folder, data):
  os.makedirs(folder, exist_ok=True)
  with open(os.path.join(folder, "brand.json"), "w") as f:
    json.dump(data, f)
  return str(folder)


def _orange_pack(folder):
  """WiNGSPAN-like: an orange accent whose own label colors fail AA."""
  palette = json.load(open(os.path.join(EXAMPLE, "brand.json")))["palette"]
  return _write_pack(folder, {
    "corp": "Orange Corp", "short": "ORANGE",
    "accent": {"dark": "#f07c00", "on-dark": "#1b1b1b", "light": "#f07c00", "on-light": "#ffffff"},
    "palette": palette,
  })


def test_example_pack_maps_both_modes():
  pack = brands.load_pack(EXAMPLE)
  data = json.load(open(os.path.join(EXAMPLE, "brand.json")))
  assert pack["name"] == "Your Corp"
  assert pack["short"] == "YOURCORP"
  for mode in ("dark", "light"):
    ui = pack["ui"][mode]
    assert ui["window"] == data["palette"][mode]["background"]
    assert ui["panel"] == data["palette"][mode]["card"]
    assert ui["text"] == data["palette"][mode]["foreground"]
    assert ui["primary_top"] == data["accent"][mode]
    # Every mapped value is a real token name with a #rrggbb value.
    assert set(ui) <= set(DARK)
    assert all(brands.HEX_RE.match(v) for v in ui.values())


@pytest.mark.parametrize("mode", ["dark", "light"])
def test_accent_text_stays_legible(tmp_path, mode):
  pack = brands.load_pack(_orange_pack(tmp_path / "orange"))
  ui = pack["ui"][mode]
  # The button keeps the corp's orange; its label and links adapt.
  assert ui["primary_top"] == "#f07c00"
  assert brands.contrast(ui["on_primary"], ui["primary_top"]) >= 4.5
  assert brands.contrast(ui["link"], ui["panel"]) >= 4.5


def test_non_hex_colors_are_rejected(tmp_path):
  data = json.load(open(os.path.join(EXAMPLE, "brand.json")))
  data["palette"]["dark"]["border"] = "red; } QWidget { background: url(evil.png)"
  data["accent"]["dark"] = "rgb(1,2,3)"
  pack = brands.load_pack(_write_pack(tmp_path / "evil", data))
  ui = pack["ui"]["dark"]
  assert "border" not in ui
  assert "primary_top" not in ui and "link" not in ui
  assert all(brands.HEX_RE.match(v) for v in ui.values())


def test_pack_without_palette_is_unusable(tmp_path):
  assert brands.load_pack(_write_pack(tmp_path / "empty", {"corp": "Nope"})) is None


def test_brand_overrides_ui_but_never_data(qapp, tmp_path):
  pack = brands.load_pack(EXAMPLE)
  pack["ui"]["dark"]["sec_hs"] = "#000000"  # a pack must not reach data tokens
  t = Theme()
  t.set_mode("dark")
  fired = []
  t.changed.connect(lambda: fired.append(True))

  t.set_brand(pack)
  assert t["window"] == pack["ui"]["dark"]["window"]
  assert t["sec_hs"] == DATA_DARK["sec_hs"]
  t.set_mode("light")
  assert t["window"] == pack["ui"]["light"]["window"]
  assert t["sec_hs"] == DATA_LIGHT["sec_hs"]

  t.set_brand(None)
  assert t["sec_hs"] == DATA_LIGHT["sec_hs"]
  assert len(fired) == 3  # brand on, mode change, brand off


def test_import_copies_only_brand_json_and_images(dirs, tmp_path):
  _, user = dirs
  src = tmp_path / "My Corp!"
  shutil.copytree(EXAMPLE, src)
  (src / "logo.png").write_bytes(b"\x89PNG fake")
  (src / "run-me.sh").write_text("echo hi")
  (src / "nested").mkdir()
  (src / "nested" / "deep.png").write_bytes(b"x")

  slug = brands.import_pack(str(src))
  assert slug == "my-corp"
  assert sorted(os.listdir(user / slug)) == ["brand.json", "logo.png"]

  listed = brands.list_packs()
  assert [(p["slug"], p["name"], p["imported"]) for p in listed] == [("my-corp", "Your Corp", True)]

  assert brands.remove_pack(slug)
  assert brands.list_packs() == []


def test_import_rejects_folder_without_brand_json(dirs, tmp_path):
  (tmp_path / "notapack").mkdir()
  with pytest.raises(ValueError):
    brands.import_pack(str(tmp_path / "notapack"))


def test_bundled_packs_listed_and_not_removable(dirs):
  bundled, _ = dirs
  shutil.copytree(EXAMPLE, bundled / "corp-a")
  assert [p["slug"] for p in brands.list_packs()] == ["corp-a"]
  assert brands.list_packs()[0]["imported"] is False
  assert not brands.remove_pack("corp-a")
  assert (bundled / "corp-a" / "brand.json").exists()


def test_remove_refuses_path_tricks(dirs):
  assert not brands.remove_pack("../etc")
  assert not brands.remove_pack("")


def test_name_label_shows_markup_as_text(qapp):
  from shortcircuit.app import NameLabel

  label = NameLabel('<img src="x">Corp')
  assert label.textFormat() == QtCore.Qt.TextFormat.PlainText


def _png(path, color="#ff8800", size=(40, 20)):
  from PySide6 import QtGui
  img = QtGui.QImage(size[0], size[1], QtGui.QImage.Format.Format_ARGB32)
  img.fill(QtGui.QColor(color))
  assert img.save(str(path))


def _pack_with_mark(folder, mark, extra=None):
  data = json.load(open(os.path.join(EXAMPLE, "brand.json")))
  data["mark"] = mark
  data.pop("landing_mark", None)
  data.update(extra or {})
  return _write_pack(folder, data)


def test_mark_resolves_inside_the_pack(qapp, tmp_path):
  folder = tmp_path / "corp"
  _pack_with_mark(folder, "wing.png")
  _png(folder / "wing.png")
  pack = brands.load_pack(str(folder))
  assert pack["mark"] == os.path.abspath(folder / "wing.png")


@pytest.mark.parametrize("name", [
  "../outside.png", "sub/inside.png", ".hidden.png", "run.sh", "missing.png", "", None, 42,
])
def test_mark_rejects_anything_but_a_plain_image_in_the_pack(qapp, tmp_path, name):
  folder = tmp_path / "corp"
  _pack_with_mark(folder, name)
  _png(tmp_path / "outside.png")
  os.makedirs(folder / "sub", exist_ok=True)
  _png(folder / "sub" / "inside.png")
  _png(folder / ".hidden.png")
  (folder / "run.sh").write_text("echo")
  assert brands.load_pack(str(folder))["mark"] is None


def test_mark_rejects_symlinks(qapp, tmp_path):
  folder = tmp_path / "corp"
  _pack_with_mark(folder, "link.png")
  _png(tmp_path / "outside.png")
  os.symlink(tmp_path / "outside.png", folder / "link.png")
  assert brands.load_pack(str(folder))["mark"] is None


def test_letterhead_prefers_lockup_main_over_short(tmp_path):
  lockup = {"logo": {"lockup": {"above": "Ministry of", "main": "Pantoscopic Observance"}}}
  with_lockup = brands.load_pack(_pack_with_mark(tmp_path / "a", None, lockup))
  without = brands.load_pack(_pack_with_mark(tmp_path / "b", None))
  assert with_lockup["letterhead"] == "Pantoscopic Observance"
  assert without["letterhead"] == "YOURCORP"


class _FakeWindow:
  """Just what MainWindow._render_portrait_slot reads."""

  def __init__(self, label):
    from shortcircuit.app import MainWindow
    self.lbl_portrait = label
    self.state_eve_connection = {"connected": False, "char_id": 0}
    self._mark_pixmap = lambda path: MainWindow._mark_pixmap(self, path)
    self.render = lambda: MainWindow._render_portrait_slot(self)


def test_portrait_slot_shows_the_right_image(qapp, tmp_path):
  from PySide6 import QtGui
  from shortcircuit.theme import theme

  folder = tmp_path / "corp"
  _pack_with_mark(folder, "wing.png")
  _png(folder / "wing.png")
  silhouette = QtGui.QPixmap(10, 10)
  silhouette.fill(QtGui.QColor("#000000"))
  me = QtGui.QPixmap(11, 11)
  me.fill(QtGui.QColor("#00ff00"))

  w = _FakeWindow(QtWidgets.QLabel())
  w._silhouette_pixmap = silhouette
  try:
    # Logged out, default look: EVE's silhouette.
    theme.set_brand(None)
    w.render()
    assert w.lbl_portrait.pixmap().cacheKey() == silhouette.cacheKey()

    # Logged out with a branded pack: the corp's mark, square canvas.
    theme.set_brand(brands.load_pack(str(folder)))
    w.render()
    shown = w.lbl_portrait.pixmap()
    assert shown.width() == shown.height() == 144

    # Logged in: your portrait, never the mark.
    w.state_eve_connection = {"connected": True, "char_id": 93594488}
    w._character_pixmap = (93594488, me)
    w.render()
    assert w.lbl_portrait.pixmap().cacheKey() == me.cacheKey()

    # A late reply for a different character is never shown.
    w._character_pixmap = (12345, me)
    w.render()
    assert w.lbl_portrait.pixmap().cacheKey() == silhouette.cacheKey()
  finally:
    theme.set_brand(None)
