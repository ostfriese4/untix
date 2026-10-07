# additional_timetables.py
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
from gi.repository import GObject
from .offline_banner import OfflineBanner
from .timetable import Timetable
import os
import json

@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/additional_timetables.ui")
class AdditionalTimetablesPage(Gtk.Box):
    __gtype_name__ = "AdditionalTimetablesPage"

    offline = Gtk.Template.Child()
    container = Gtk.Template.Child()
    timetable_page = Gtk.Template.Child()
    view = Gtk.Template.Child()
    main_page = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.displayed = {}
        self.currentTimetable = None
        self.nested_offline = self.offline
        self.isDisplayed = False

    def enable_bindings(self, parent):
        def on_visible(*args):
            if parent.main_view_stack.get_visible_child_name() == "additional_timetables":
                if self.isDisplayed:
                    if self.currentTimetable is not None:
                        self.view.pop_to_page(self.main_page)
                        self.currentTimetable = None
                self.display()
            else:
                self.isDisplayed = False

        parent.sidebar.connect("activated", on_visible)
        self.shared = parent.shared
        self.parent = parent

    def openTimetable(self, row, timetable):
        widget = Timetable(timetable["type"], timetable["id"])
        widget.enable_bindings(self.parent)
        self.timetable_page.set_child(widget)
        self.currentTimetable = widget
        widget.offline.update(self.nested_offline.offline, self.nested_offline.last)
        self.nested_offline = widget.offline
        self.view.push(self.timetable_page)

    def shouldHide(self):
        return len(self.shared.session.getAvailableTimetables()) <= 1 # hide if no or only one (probably the one of the user) timetable exists

    def refresh(self):
        if self.currentTimetable is not None:
            self.currentTimetable.refresh()
        self.display()

    def isStarred(self, timetable):
        all = getStarredTimetables(self.shared)
        for i in all:
            if i["id"] == timetable["id"] and i["type"] == timetable["type"]:
                return True, i
        return False, None

    def updateStarButton(self, button, timetable):
        starred, t = self.isStarred(timetable)
        if starred:
            button.set_icon_name("starred-symbolic")
            button.set_tooltip_text(_("Remove timetable from favorites"))
        else:
            button.set_icon_name("non-starred-symbolic")
            button.set_tooltip_text(_("Add timetable to favorites"))

    def toggleStarred(self, button, timetable):
        all = getStarredTimetables(self.shared)
        starred, t = self.isStarred(timetable)
        if starred:
            all.remove(t)
        else:
            all.append(timetable)

        setStarredTimetables(all, self.shared)
        self.updateStarButton(button, timetable)

    def display(self):
        self.isDisplayed = True
        timetables = self.shared.session.getAvailableTimetables()

        for section in self.displayed:
            section = self.displayed[section]
            self.container.remove(section)
        self.displayed.clear()

        for timetable in timetables:
            row = Adw.ActionRow(title = timetable["name"])
            row.set_activatable(True)
            row.connect("activated", self.openTimetable, timetable)

            star_button = Gtk.Button()
            star_button.connect("clicked", self.toggleStarred, timetable)
            row.add_suffix(star_button)
            self.updateStarButton(star_button, timetable)

            if not timetable["name"] in self.displayed:
                title = ""
                match timetable["type"]:
                    case "STUDENT":
                        title = _("Students")
                    case "TEACHER":
                        title = _("Teachers")
                    case "CLASS":
                        title = _("Classes")
                    case "ROOM":
                        title = _("Rooms")

                section = Adw.PreferencesGroup(title = title)
                self.container.add(section)
                self.displayed[timetable["name"]] = section
            else:
                section = self.displayed[timetable["name"]]

            section.add(row)

def getStarredTimetablesPath(shared):
    profile = shared.profiles["default-profile"]
    return os.environ.get("XDG_DATA_HOME", ".untix") + f"/untix-starred-timetables-{profile}.json"

def getStarredTimetables(shared):
    path = getStarredTimetablesPath(shared)
    try:
        with open(path) as file:
            return json.load(file)
    except Exception:
        timetables = []
        own = shared.session.getOwnTimetableId()
        if own is not None:
            timetables.append(own)
        return timetables

def setStarredTimetables(data, shared):
    path = getStarredTimetablesPath(shared)
    with open(path, "w") as file:
        json.dump(data, file, indent = 4)
    addStarredTimetables(shared.window)
    shared.window.rebuildSidebar()

def addStarredTimetables(window):
    groupName = _("Timetables")

    needed = getStarredTimetables(window.shared)

    for page in window.dynamicPages.copy():
        if page["group"] == groupName:
            if "data" in page:
                if page["data"] in needed:
                    needed.remove(page["data"])
                else:
                    window.dynamicPages.remove(page)

    for pageData in needed:
        id = "starred-timetable" + pageData["name"] + pageData["type"] + str(pageData["id"])

        widget = Timetable(
            resourceType = pageData["type"],
            resourceId = pageData["id"],
            id = id,
        )
        widget.enable_bindings(window)

        window.dynamicPages.append({
            "group": groupName,
            "data": pageData,
            "widget": widget,
            "name": id,
            "icon": "starred-symbolic",
            "title": pageData["name"],
        })

moduleInfo = {
    "staticPages": [
        {
            "group": _("Timetables"),
            "widget": AdditionalTimetablesPage(),
            "name": "additional_timetables",
            "title": _("All timetables"),
            "icon": "month-symbolic",
        }
    ],
    "pageProviders": [
        {
            "name": "starred-timetables",
            "code": addStarredTimetables
        }
    ]
}
