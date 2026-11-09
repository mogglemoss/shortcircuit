# test_name_label.py
"""Wrapping and eliding of the character name beside the portrait.

Widths are derived from the label's own font metrics, so the assertions
hold whatever font the test machine renders with.
"""

import os

# The suite is headless: select the Qt platform plugin before Qt is imported.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtGui, QtWidgets


@pytest.fixture(scope="session")
def qapp():
  app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  yield app


@pytest.fixture
def make_label(qapp):
  from shortcircuit.app import NameLabel

  def _make(text):
    label = NameLabel(text)
    label.setStyleSheet("font-size: 14px; font-weight: bold;")
    label.ensurePolished()
    return label

  return _make


def _width(label, text):
  return QtGui.QFontMetrics(label.font()).horizontalAdvance(text)


def test_short_name_stays_on_one_line(make_label):
  label = make_label("CORMORANT FELL")
  lines, cut = label.fitted_lines(_width(label, "CORMORANT FELL") + 20)
  assert lines == ["CORMORANT FELL"]
  assert not cut


def test_long_first_and_last_name_wrap_onto_two_lines(make_label):
  name = "BARTHOLOMEW RAVENSCROFT-WINTERBOURNE"
  label = make_label(name)
  # Room for the longer of the two words, but not for both on one line.
  width = _width(label, "RAVENSCROFT-WINTERBOURNE") + 4
  lines, cut = label.fitted_lines(width)
  assert lines == ["BARTHOLOMEW", "RAVENSCROFT-WINTERBOURNE"]
  assert not cut


def test_single_word_too_long_for_the_line_is_elided(make_label):
  word = "RAVENSCROFTWINTERBOURNE"
  label = make_label(word)
  lines, cut = label.fitted_lines(_width(label, word) // 2)
  assert len(lines) == 1
  assert lines[0].endswith("…")
  assert cut


def test_more_words_than_lines_elides_the_last_line(make_label):
  label = make_label("ALPHA BRAVO CHARLIE")
  # Each word fits on a line, but three words need three lines.
  width = _width(label, "CHARLIE") + 4
  lines, cut = label.fitted_lines(width)
  assert len(lines) == 2
  assert lines[0] == "ALPHA"
  assert lines[1].endswith("…")
  assert cut


def test_full_name_goes_to_tooltip_only_when_cut(qapp, make_label):
  name = "BARTHOLOMEW RAVENSCROFT-WINTERBOURNE"
  label = make_label(name)
  # Shown like in the app: Qt defers resize events for hidden widgets.
  label.show()

  label.resize(_width(label, "BARTHOLOMEW") // 2, 60)
  qapp.processEvents()
  assert label.toolTip() == name
  assert label.full_text() == name

  label.resize(_width(label, name) + 40, 60)
  qapp.processEvents()
  assert label.toolTip() == ""
  assert label.text() == name
  label.close()
