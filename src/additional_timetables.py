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

@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/additional_timetables.ui")
class AdditionalTimetablesPage(Gtk.Box):
    __gtype_name__ = "AdditionalTimetablesPage"

    show_sidebar_button = Gtk.Template.Child()
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
        parent.split_view.bind_property(
            "show-sidebar",
            self.show_sidebar_button,
            "active",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
        )
        parent.sidebar_breakpoint.add_setter(self.show_sidebar_button, "visible", True)

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
        widget.initTimetable(self.parent)
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

    def display(self):
        self.isDisplayed = True
        timetables = self.shared.session.getAvailableTimetables()

        for section in self.displayed:
            section = self.displayed[section]
            self.container.remove(section)
        self.displayed.clear()

        for timetable in timetables:
            print(timetable)
            row = Adw.ActionRow(title = timetable["name"])
            row.set_activatable(True)
            row.connect("activated", self.openTimetable, timetable)

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
