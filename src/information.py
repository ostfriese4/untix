# information.py
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
from .homework_row import HomeworkRow
from .dialog import closeOnClickOutside


@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/information.ui")
class InformationWindow(Adw.Dialog):
    __gtype_name__ = "InformationWindow"

    info_table = Gtk.Template.Child()

    def __init__(self, window, **kwargs):
        super().__init__(**kwargs)
        self.window = window
        self.info_rows = []
        self.lesson = None
        closeOnClickOutside(self)
        self.connect("closed", self.onClose)

    def onClose(self, *args):
        self.lesson = None

    def setLesson(self, lesson):
        self.lesson = lesson
        while self.info_rows != []:
            self.info_table.remove(self.info_rows.pop())

        rows = []
        data = {}
        rows.append(("", data))

        data[_("Subject")] = lesson["subject"]["longName"]
        data[_("Room")] = lesson["room"]
        data[_("Room description")] = lesson["room-info"]
        data[_("Teacher")] = lesson["teachers-long"]
        if lesson.get("mainStudentGroup"):
            data[_("Class")] = lesson["mainStudentGroup"]["name"]
        if lesson.get("substText"):
            data[_("Substitution")] = lesson["substText"]
        if lesson["lessonInfo"] is not None:
            data[_("Information about this lesson")] = lesson["lessonInfo"]
        if lesson["teachingContent"] is not None:
            data[_("Teaching content")] = lesson["teachingContent"]
        if lesson["status"] == "CANCELLED":
            data[_("Cancelled")] = ""

        minutes_start = str(lesson["start"] % 60).zfill(2)
        hours_start = str(int(lesson["start"] / 60)).zfill(2)

        minutes_end = str(lesson["end"] % 60).zfill(2)
        hours_end = str(int(lesson["end"] / 60)).zfill(2)

        data[_("Duration")] = (
            str(lesson["duration"])
            + " "
            + _("Minutes")
            + " ("
            + hours_start
            + ":"
            + minutes_start
            + " - "
            + hours_end
            + ":"
            + minutes_end
            + ")"
        )

        if lesson["homeworks"] != []:
            homeworks = lesson["homeworks"]
            data = {}
            i = 0
            for homework in homeworks:
                data[i] = homework
                i += 1
            rows.append((_("Homework"), data))

        if "original" in lesson:
            data = {}
            rows.append((_("Original lesson"), data))
            original = lesson["original"]
            data[_("Subject")] = original["subject"]["longName"]
            data[_("Room")] = original["room"]
            data[_("Room description")] = original["room-info"]
            data[_("Teacher")] = original["teachers-long"]

        for r in rows:
            data = r[1]
            table = Adw.PreferencesGroup(title=r[0])
            self.info_table.add(table)
            for key, value in data.items():
                if r[0] == _("Homework"):
                    row = HomeworkRow(value)
                else:
                    row = Adw.ActionRow(title=key)
                    row.set_subtitle(value)
                    if value != "":
                        row.add_css_class("property")
                table.add(row)
            self.info_rows.append(table)

        self.present(self.window)
