# test_versioncheck.py
"""The update prompt asks this fork's releases and its Download button works.

3.0.0 shipped asking upstream's repo (whose versions are v1.x, so no fork
release would ever be announced), and with a Download button that did
nothing: exec() returns an opaque id for custom buttons, which never equals
AcceptRole, so every click read as "Remind me later".
"""

import json
import os

# The suite is headless: select the Qt platform plugin before Qt is imported.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest import mock

import pytest
from PySide6 import QtCore, QtWidgets

from shortcircuit.model import versioncheck

RELEASE = {
  "tag_name": "v9.9.9",
  "published_at": "2026-11-09T00:00:00Z",
  "body": "Notes.",
  "html_url": "https://github.com/mogglemoss/shortcircuit/releases/tag/v9.9.9",
}


@pytest.fixture(scope="session")
def qapp():
  app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  yield app


def test_asks_this_forks_releases():
  check = versioncheck.VersionCheck()
  with mock.patch.object(versioncheck.requests, "get", side_effect=versioncheck.requests.exceptions.ConnectionError) as get:
    check.process()
  assert get.call_args.kwargs["url"] == (
    "https://api.github.com/repos/mogglemoss/shortcircuit/releases/latest"
  )


def _answer_prompt(button_text):
  """Show the real prompt and click the named button; return the URL opened."""
  from shortcircuit import app as app_module

  parent = QtWidgets.QWidget()

  def click_when_shown():
    box = next(w for w in QtWidgets.QApplication.topLevelWidgets()
               if isinstance(w, QtWidgets.QMessageBox) and w.isVisible())
    next(b for b in box.buttons() if b.text() == button_text).click()

  QtCore.QTimer.singleShot(50, click_when_shown)
  with mock.patch.object(app_module.sys, "platform", "darwin"), \
       mock.patch.object(app_module.QtGui.QDesktopServices, "openUrl") as open_url:
    app_module.MainWindow.version_check_done(parent, json.dumps(RELEASE))
  return [c.args[0].toString() for c in open_url.call_args_list]


def test_download_now_opens_the_release_page(qapp):
  assert _answer_prompt("Download now") == [RELEASE["html_url"]]


def test_remind_me_later_opens_nothing(qapp):
  assert _answer_prompt("Remind me later") == []
