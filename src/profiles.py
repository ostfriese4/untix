# profiles.py
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
from .credentials import getProfiles, setProfiles, getCredentials
from .api import session
from .dialog import closeOnClickOutside
import traceback


class ProfileRow(Adw.ActionRow):
    __gttype_name__ = "ProfileRow"

    def __init__(self, id, data, window):
        super().__init__()

        self.set_activatable(True)

        try:
            name = data["name"]
        except:
            name = _("Unnamed")
            data["name"] = name

        self.set_title(name)

        edit = Gtk.Button()
        edit.set_icon_name("document-edit-symbolic")
        edit.set_tooltip_text(_("Edit profile %s").replace("%s", name))
        self.add_suffix(edit)

        delete = Gtk.Button()
        delete.set_icon_name("user-trash-symbolic")
        delete.add_css_class("destructive-action")
        delete.set_tooltip_text(_("Delete profile %s").replace("%s", name))
        self.add_suffix(delete)

        def on_delete(a):
            print("delete profile", id)
            window.deleteProfile(id)

        delete.connect("clicked", on_delete)

        def on_edit(a):
            print("edit profile", id)
            window.editProfile(id)

        edit.connect("clicked", on_edit)

        def on_enable(a):
            print("enable profile", id)
            window.switchProfile(id)

        self.connect("activated", on_enable)


@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/profiles.ui")
class ProfilesWindow(Adw.Dialog):
    __gtype_name__ = "ProfilesWindow"

    container = Gtk.Template.Child()
    add_button = Gtk.Template.Child()

    def __init__(self, window, **kwargs):
        super().__init__(**kwargs)

        closeOnClickOutside(self)

        self.add_button.connect("clicked", self.createProfile)

        self.window = window
        self.displayed = []

    def updateList(self):
        while self.displayed != []:
            item = self.displayed.pop()
            self.container.remove(item)
        profiles = self.window.shared.profiles["profiles"]
        for profile in profiles:
            row = ProfileRow(profile, profiles[profile], self)
            self.displayed.append(row)
            self.container.add(row)

    def manage(self):
        self.updateList()
        self.present(self.window)

    def createProfile(self, a=None):
        data = self.window.shared.profiles
        id = len(data["profiles"]) + 1
        while str(id) in data["profiles"]:
            id+=1
        id = str(id)

        data["profiles"][id] = {}
        self.editProfile(id)

    def createProfileFromUri(self, uri):
        self.createProfile()
        self.window.login_window.fillDataFromUri(uri)

    def switchProfile(self, id):
        data = self.window.shared.profiles
        data["default-profile"] = id
        setProfiles(data)
        self.close()
        try:
            self.window.shared.session = session(getCredentials(id))
            self.window.reload()
        except:
            traceback.print_exc()

    def editProfile(self, id):
        self.switchProfile(id)
        self.window.login_window.requestLogin(id)

    def deleteProfile(self, id):
        data = self.window.shared.profiles
        if len(data["profiles"]) == 1:
            error = Adw.AlertDialog()
            error.set_body(_("Can not delete only profile"))
            error.set_heading(_("Error"))
            error.add_response("cancel", _("Cancel"))
            error.present(self.get_ancestor(Adw.ApplicationWindow))
        else:

            def confirm(warning, answer):
                if answer == "delete":
                    del data["profiles"][id]
                    setProfiles(data)
                    if id == data["default-profile"]:
                        self.switchProfile(list(data["profiles"].keys())[0])
                    self.manage()

            warning = Adw.AlertDialog()
            warning.set_body(_("Do you really want to delete this profile?"))
            warning.set_heading(_("Delete?"))
            warning.add_response("cancel", _("Cancel"))
            warning.add_response("delete", _("Delete"))
            warning.set_default_response("cancel")
            warning.set_close_response("cancel")
            warning.set_response_appearance("delete", 2)
            warning.connect("response", confirm)
            warning.present(self.get_ancestor(Adw.ApplicationWindow))
