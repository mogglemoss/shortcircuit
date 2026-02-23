# versioncheck.py
import asyncio
import json
import os
from datetime import datetime, timedelta

import semver
from PySide6 import QtCore
from dateutil import parser
from dateutil.tz import tzutc

from shortcircuit import __version__ as app_version
from .logger import Logger


class VersionCheck(QtCore.QObject):
  """
  Version Check on Github releases
  """

  finished = QtCore.Signal(str)

  def process(self):
    """
    Emits latest version string
    """
    if 'DEBUG' in os.environ:
      import debugpy
      debugpy.debug_this_thread()

    try:
      asyncio.run(self._process_async())
    except BaseException as e:
      Logger.error(f"VersionCheck exception: {e}", exc_info=True)
      self.finished.emit(None)

  async def _process_async(self):
    import httpx

    try:
      async with httpx.AsyncClient() as client:
        response = await client.get(
          url='https://api.github.com/repos/secondfry/shortcircuit/releases/latest',
          timeout=3.1,
          follow_redirects=True,
        )
    except httpx.RequestError as e:
      Logger.error('Exception raised while trying to get latest version info')
      Logger.error(e)
      self.finished.emit(None)
      return

    if not VersionCheck.should_emit_response(response):
      self.finished.emit(None)
      return

    self.finished.emit(response.text)

  @staticmethod
  def should_emit_response(response):
    from .utility.configuration import Configuration

    if response.status_code != 200:
      Logger.error('Response code is not 200')
      Logger.error(response)
      return False

    try:
      github_data = json.loads(response.text)
    except:
      Logger.error('Response was not json')
      Logger.error(response)
      return False

    if 'tag_name' not in github_data:
      Logger.error('tag_name is missing from response')
      Logger.error(response)
      return False

    github_version = github_data['tag_name'].split('v')[-1]
    try:
      if semver.Version.parse(github_version) <= semver.Version.parse(app_version):
        Logger.debug('GitHub version is not newer')
        return False
    except ValueError:
      Logger.error(
        'semver.compare(\'{}\', \'{}\')'.format(github_version, app_version)
      )
      return False
    except Exception as e:
      Logger.error('Something is really wrong', exc_info=e)
      return False

    datetime_now = datetime.now(tzutc())
    datetime_now_string = datetime_now.strftime('%Y-%m-%dT%H:%M:%SZ')

    saved_version = Configuration.settings.value('updates/version')
    Logger.debug('Latest remote version saved is – v{}'.format(saved_version))
    if not saved_version or semver.Version.parse(github_version) != semver.Version.parse(saved_version):
      Configuration.settings.setValue('updates/version', github_version)
      Configuration.settings.setValue(
        'updates/ping_timestamp', datetime_now_string
      )
      return True

    saved_version_timestamp = Configuration.settings.value(
      'updates/ping_timestamp'
    )
    Logger.debug(
      'Last time user was notified about update was – {}'.
      format(saved_version_timestamp)
    )
    if not saved_version_timestamp:
      Configuration.settings.setValue(
        'updates/ping_timestamp', datetime_now_string
      )
      return True

    version_timestamp = parser.parse(timestr=saved_version_timestamp)
    if datetime_now - version_timestamp > timedelta(days=7):
      Configuration.settings.setValue(
        'updates/ping_timestamp', datetime_now_string
      )
      return True

    return False


def main():
  version_check = VersionCheck()
  version_check.process()


if __name__ == "__main__":
  main()
