# absences.py
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

import datetime


class Absence(Adw.ExpanderRow):
    __gtype_name__ = "Absence"

    def __init__(self, absence, **kwargs):
        super().__init__(**kwargs)

        self.set_title(absence["reason"])
        self.set_subtitle(absence["text"])
        self.set_subtitle_lines(1)

        start = datetime.datetime.strptime(
            str(absence["startDate"]) + str(absence["startTime"]), "%Y%m%d%H%M"
        )
        end = datetime.datetime.strptime(
            str(absence["endDate"]) + str(absence["endTime"]), "%Y%m%d%H%M"
        )

        if absence["text"] != "":
            text = Adw.ActionRow(title=_("Text"), subtitle=absence["text"])
            self.add_row(text)

        if absence["isExcused"]:
            excusedRow = Adw.ActionRow(title=_("Excused"))
        else:
            excusedRow = Adw.ActionRow(title=_("Unexcused"))
            self.add_css_class("unexcused")
        self.add_row(excusedRow)

        startRow = Adw.ActionRow(title=_("Start"), subtitle=start.strftime("%c"))
        self.add_row(startRow)
        startRow.add_css_class("property")

        endRow = Adw.ActionRow(title=_("End"), subtitle=end.strftime("%c"))
        self.add_row(endRow)
        endRow.add_css_class("property")


@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/absences.ui")
class AbsencesPage(Gtk.Box):
    __gtype_name__ = "AbsencesPage"

    offline = Gtk.Template.Child()
    container = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.displayed = []

    def enable_bindings(self, parent):
        def on_visible(page, pspec):
            if parent.main_view_stack.get_visible_child_name() == "absences":
                self.display()

        parent.main_view_stack.connect("notify::visible-child-name", on_visible)
        self.shared = parent.shared
        self.parent = parent

    def onAdded(self):
        absences = self.shared.session.getAbsences()
        self.count(absences)

    def count(self, absences):
        count = 0
        for absence in absences:
            if not absence["isExcused"]:
                count += 1
        page = self.parent.main_view_stack.get_page(self)
        page.set_badge_number(count)
        print(count, "absences")

    def shouldHide(self):
        absences = self.shared.session.getAbsences()
        return absences is None or absences == []

    def display(self):
        absences = self.shared.session.getAbsences()
        self.count(absences)

        while self.displayed != []:
            row = self.displayed.pop()
            self.container.remove(row)

        for absence in absences:
            row = Absence(absence)
            self.container.add(row)
            self.displayed.append(row)

moduleInfo = {
    "staticPages": [
        {
            "group": _("Modules"),
            "widget": AbsencesPage(),
            "name": "absences",
            "title": _("Absences"),
            "icon": "appointment-soon-symbolic",
        }
    ]
}
