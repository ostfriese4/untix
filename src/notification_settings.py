# account_settings.py
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

from gi.repository import Gtk
from gi.repository import Adw
from .shared import shared


@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/notification_settings.ui")
class NotificationSettingsPage(Adw.PreferencesPage):
    __gtype_name__ = "NotificationSettingsPage"

    email = Gtk.Template.Child()
    mail_message = Gtk.Template.Child()
    mail_notification = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.editable = False

        self.email.connect("apply", lambda data:self.apply("email"))
        self.mail_message.connect("notify::active", lambda x,y:self.apply("forwardMessageToEmail"))
        self.mail_notification.connect("notify::active", lambda x,y:self.apply("systemMailForwarding"))

    def apply(self, key):
        if self.editable:
            match key:
                case "email":
                    value = self.email.get_text()
                case "forwardMessageToEmail":
                    value = self.mail_message.get_active()
                case "systemMailForwarding":
                    value = self.mail_notification.get_active()
            print(shared.session.setProfileKey(key, value))
            print("apply",key,value)

    def load(self):
        self.editable = False
        data = shared.session.getProfile()
        if "email" in data:
            self.email.set_text(data["email"])
        if "forwardMessageToEmail" in data:
            self.mail_message.set_active(data["forwardMessageToEmail"])
        if "systemMailForwarding" in data:
            self.mail_notification.set_active(data["systemMailForwarding"])
        self.editable = True

