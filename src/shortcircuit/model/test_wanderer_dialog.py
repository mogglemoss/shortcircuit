# test_wanderer_dialog.py
"""The Wanderer dialog catches a token that isn't a Wanderer map key.

The token field is masked, so a wrong paste (the instance URL, or a key
from elsewhere in Wanderer) is invisible and only shows up later as a 401
"invalid token for map". Wanderer map keys are UUIDs.
"""

import os

# The suite is headless: select the Qt platform plugin before Qt is imported.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest import mock

import pytest
from PySide6 import QtWidgets

from shortcircuit.mapper_dialogs import WandererDialog

KEY = "1b4e28ba-2fa1-11d2-883f-0016d3cca427"
SAVE = QtWidgets.QMessageBox.StandardButton.Save
CANCEL = QtWidgets.QMessageBox.StandardButton.Cancel


@pytest.fixture(scope="session")
def qapp():
  return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _ok(token, answer=CANCEL):
  dlg = WandererDialog("W", "http://wanderer:8000", "my-map", token)
  with mock.patch.object(QtWidgets.QMessageBox, "warning", return_value=answer) as warn:
    dlg.accept()
  return dlg.result(), warn


def test_a_map_key_is_accepted_without_warning(qapp):
  result, warn = _ok(KEY)
  assert result == QtWidgets.QDialog.DialogCode.Accepted
  warn.assert_not_called()


def test_a_pasted_url_is_caught(qapp):
  result, warn = _ok("http://mollusk.magpie-cherimoya.ts.net:8000/")
  assert result == QtWidgets.QDialog.DialogCode.Rejected
  assert "a web address" in warn.call_args.args[2]


def test_a_key_from_elsewhere_is_caught(qapp):
  result, warn = _ok("x" * 44)
  assert result == QtWidgets.QDialog.DialogCode.Rejected
  assert "44 characters" in warn.call_args.args[2]


def test_save_anyway_still_saves(qapp):
  result, _ = _ok("not-a-uuid", answer=SAVE)
  assert result == QtWidgets.QDialog.DialogCode.Accepted
