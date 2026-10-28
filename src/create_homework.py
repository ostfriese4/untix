# create_homework.py
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
from .homework_api import getNewId, setValue, getById, delete
from .dialog import closeOnClickOutside
from .shared import shared


@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/create_homework.ui")
class HomeworkEditWindow(Adw.Dialog):
    __gtype_name__ = "HomeworkEditWindow"

    completed = Gtk.Template.Child()
    date = Gtk.Template.Child()
    task = Gtk.Template.Child()
    save = Gtk.Template.Child()
    subject = Gtk.Template.Child()

    delete_button = Gtk.Template.Child()
    delete_row = Gtk.Template.Child()

    def __init__(self, window, **kwargs):
        super().__init__(**kwargs)
        self.window = window
        closeOnClickOutside(self)
        self.save.add_css_class("suggested-action")
        self.save.connect("activated", self.on_save)
        self.delete_button.add_css_class("destructive-action")
        self.delete_button.connect("activated", self.delete)

    def new_homework(self):
        self.window.main_view_stack.set_visible_child_name("homework")
        self.row = None
        self.current_id = getNewId()
        self.task.set_text("")
        self.delete_row.set_visible(False)
        self.set_title(_("Create homework"))
        self.present(self.window)

    def edit(self, id, row=None):
        self.row = row
        self.current_id = id
        item = getById(id)
        self.task.set_text(item["text"])
        self.subject.set_text(item["subject"])
        self.completed.set_active(item["completed"])
        date = item["dueDate"]
        year = int(date * 0.0001)
        month = int((date - (year * 10000)) * 0.01)
        day = date - year * 10000 - month * 100
        self.date.set_year(year)
        self.date.set_month(month - 1)
        self.date.set_day(day)
        self.delete_row.set_visible(True)
        self.set_title(_("Edit homework"))
        self.present(self.window)

    def on_save(self, data=None):
        setValue(self.current_id, "text", self.task.get_text())
        setValue(self.current_id, "subject", self.subject.get_text())
        setValue(self.current_id, "completed", self.completed.get_active())
        setValue(
            self.current_id,
            "dueDate",
            int(
                str(self.date.get_year()).zfill(4)
                + str(self.date.get_month() + 1).zfill(2)
                + str(self.date.get_day()).zfill(2)
            ),
        )
        self.close()
        if self.row is not None:
            self.row.update()
        for action in shared.homeworkUpdatedActions:
            GLib.idle_add(action)

    def delete(self, data=None):
        warning = Adw.AlertDialog()
        warning.set_body(_("Do you really want to delete this homework?"))
        warning.set_heading(_("Delete?"))
        warning.add_response("cancel", _("Cancel"))
        warning.add_response("delete", _("Delete"))
        warning.set_default_response("cancel")
        warning.set_close_response("cancel")
        warning.set_response_appearance("delete", 2)

        def on_answer(warning, answer):
            if answer == "delete":
                self.deleteData()

        warning.connect("response", on_answer)
        warning.present(self.get_ancestor(Adw.ApplicationWindow))

    def deleteData(self):
        delete(self.current_id)
        self.close()
        if self.row is not None:
            if getById(self.current_id) is None:
                self.row.delete()
            else:
                self.row.update()
        for action in shared.homeworkUpdatedActions:
            GLib.idle_add(action)

dialog = None
def getEditWindow():
    global dialog
    if dialog is None:
        window = shared.app.props.active_window
        dialog = HomeworkEditWindow(window)
    return dialog
