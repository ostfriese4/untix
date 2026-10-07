# homework.py
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
from gi.repository import GLib
from gi.repository import GObject
from .homework_api import getAll
from .offline_banner import OfflineBanner
from .homework_row import HomeworkRow
import datetime


@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/homework.ui")
class HomeworkList(Gtk.Box):
    __gtype_name__ = "HomeworkList"

    offline = Gtk.Template.Child()
    container_done = Gtk.Template.Child()
    container_undone = Gtk.Template.Child()
    undone_page = Gtk.Template.Child()
    empty_undone = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.days = {}
        self.scrollTo = None

    def enable_bindings(self, parent):
        self.shared = parent.shared
        self.parent = parent

    def refresh(self, reason):
        self.displayAll()

    def onAdded(self):
        self.displayAll()

    def set_number(self, unfinished):
        page = self.parent.main_view_stack.get_page(self)
        page.set_badge_number(unfinished)
        self.undone_page.set_badge_number(unfinished)
        if unfinished == 0:
            self.empty_undone.set_visible(True)
        else:
            self.empty_undone.set_visible(False)

    def get_number(self):
        return self.page.get_badge_number()

    def displayAll(self):
        unfinished = 0
        self.scrollTo = None
        data = getAll()
        for item in data:
            if item["completed"] == False:
                unfinished += 1
        self.display(data)
        self.set_number(unfinished)

    def sortData(self, data):
        new = []
        if not len(data) == 0:
            new.append(data.pop())
            for homework in data:
                i = 0
                date = datetime.datetime.strptime(str(homework["dueDate"]), "%Y%m%d")
                for item in new:
                    itemDate = datetime.datetime.strptime(
                        str(item["dueDate"]), "%Y%m%d"
                    )
                    if date.year < itemDate.year:
                        break
                    elif date.year == itemDate.year:
                        if date.month < itemDate.month:
                            break
                        elif date.month == itemDate.month:
                            if date.day <= itemDate.day:
                                break
                    i += 1
                new.insert(i, homework)
        return new

    def display(self, data):
        data = self.sortData(data)
        for day in self.days:
            self.days[day][0].remove(self.days[day][1])
        self.days = {}
        for homework in data:
            dateName = str(homework["dueDate"])
            date = datetime.datetime.strptime(dateName, "%Y%m%d")
            completed = homework["completed"]
            dayName = dateName + str(completed)

            if dayName in self.days:
                day = self.days[dayName][1]
            else:
                if completed:
                    container = self.container_done
                else:
                    container = self.container_undone
                day = Adw.PreferencesGroup(title=date.strftime("%x"))
                container.add(day)
                self.days[dayName] = (container, day)
            row = HomeworkRow(homework)
            day.add(row)

moduleInfo = {
    "staticPages": [
        {
            "group": _("Modules"),
            "widget": HomeworkList(),
            "name": "homework",
            "title": _("Homework"),
            "icon": "agenda-symbolic",
        }
    ]
}
