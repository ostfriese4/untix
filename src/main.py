# main.py
#
# Copyright 2026 Jonas
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from .api import session, version, id, testCredentials, releaseNotes
from .homework_api import setShared
from gi.repository import Gtk, Gio, Adw
from .window import UntisWindow
from .preferences import PreferencesDialog
from .credentials import getCredentials, getProfiles
import datetime
import os

paths = [
    os.environ.get("XDG_CACHE_HOME", ".untis/cache") + "/untis/",
    os.environ.get("XDG_DATA_HOME", ".untis/data")
]

for path in paths:
    if not os.path.exists(path):
        os.makedirs(path)


developers = ["Ostfriese4", "Felitendo"]


class shared:
    pass


class UntisApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="page.codeberg.ostfriese4.Untis",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            resource_base_path="/page/codeberg/ostfriese4/Untis",
        )
        self.create_action("quit", lambda *_: self.quit(), ["<control>q"])
        self.create_action("about", self.on_about_action)
        self.create_action("preferences", self.on_preferences_action, ["<control>comma"])
        self.create_action("login", self.on_login_action, ["<control>l"])
        self.create_action("profiles", self.on_profiles_action, ["<control>p"])
        self.create_action("refresh", self.on_refresh_action, ["<control>r"])
        self.create_action(
            "create_homework", self.on_create_homework_action, ["<control>n"]
        )

        self.shared = shared()
        self.shared.shared = shared
        self.shared.profiles = getProfiles()
        self.shared.checked = False
        self.loginIfPossible = False

        profile = self.shared.profiles["default-profile"]
        credentials = getCredentials(profile)
        self.shared.session = session(credentials)
        if not testCredentials(credentials):
            self.loginIfPossible = True

        setShared(self.shared)

        self.set_flags(Gio.ApplicationFlags.HANDLES_OPEN)

    def do_open(self, files, n_files, hint):
        self.do_activate(check = False)
        for file in files:
            url = file.get_uri()
            self.props.active_window.profiles_window.createProfileFromUri(url)

    def do_activate(self, check = True):
        win = self.props.active_window
        if not win:
            win = UntisWindow(self.shared, application=self)
        win.present()

        if check:
            win.checkCredentials()

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(
            application_name=_("Untix"),
            application_icon=id,
            developer_name=developers[0],
            version=version,
            developers=developers,
            copyright="© 2026 " + developers[0],
        )
        # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
        about.set_translator_credits(_("translator-credits"))
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_issue_url("https://codeberg.org/ostfriese4/untix/issues")
        about.set_release_notes(releaseNotes)
        about.present(self.props.active_window)

    def on_preferences_action(self, *args):
        PreferencesDialog().present(self.props.active_window)

    def on_login_action(self, widget, _):
        self.props.active_window.login_window.requestLogin(
            self.shared.profiles["default-profile"]
        )

    def on_profiles_action(self, widget, _):
        self.props.active_window.profiles_window.manage()

    def on_refresh_action(self, widget, _):
        self.props.active_window.refresh()

    def on_create_homework_action(self, widget, _):
        self.props.active_window.homeworkEditWindow.new_homework()

    def create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    """The application's entry point."""
    app = UntisApplication()

    return app.run(sys.argv)
