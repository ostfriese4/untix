# custom_timetable_builder.py
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
from gi.repository import Gio
import traceback


def getTemplates(window, type="component"):
    shared = window.shared

    filters = {
        "true": {
            "description": _("Take all"),
            "template": {}
        },
        "isOneOf": {
            "description": _("Property has value"),
            "template": {
                "values": [],
                "key": ["mainStudentGroup", "name"],
            }
        },
    }

    components = {
        "fromRealTimetable": {
            "description": _("Take lessons from real timetable"),
            "template": {
                "timetable": shared.session.getOwnTimetableId(),
                "filters": [
                    {
                        "type": "true"
                    }
                ],
            }
        },
#        "regularLesson": {
#            "description": _("Regular lesson"),
#            "template": {
#
#            }
#        },
    }

    templates = {
        "component": components,
        "filter": filters,
    }
    return templates[type]

def choose(window, question, title, choices, callback):
    dialog = Adw.Dialog()
    dialog.set_title(title)
    dialog.set_content_width(450)

    content = Adw.ToolbarView()
    dialog.set_child(content)
    header = Adw.HeaderBar()
    content.add_top_bar(header)

    page = Adw.PreferencesPage()
    content.set_content(page)
    group = Adw.PreferencesGroup()
    page.add(group)

    group.set_title(question)
    for choice in choices:
        id = choice
        title = choices[id]
        row = Adw.ActionRow(title = title)
        row.set_activatable(True)
        def code(*args, type=id):
            callback(type)
        row.connect("activated", code)
        row.connect("activated", lambda *args: dialog.close())
        group.add(row)

    dialog.present(window)

def confirm(window, question, yes, no, callback):
    dialog = Adw.AlertDialog()
    dialog.set_heading(question)
    dialog.add_response("no", no)
    dialog.add_response("yes", yes)
    dialog.set_close_response("no")
    dialog.set_default_response("no")
    dialog.set_response_appearance("yes", Adw.ResponseAppearance.DESTRUCTIVE)

    def code(dialog, response):
        if response == "yes":
            callback()

    dialog.connect("response", code)
    dialog.choose(window)

class CustomTimetableFilter(Adw.ActionRow):
    def __init__(self, filter, step):
        super().__init__()

        self.step = step
        self.data = filter

        filters = getTemplates(self.step.parent.parent, "filter")
        self.set_title(filters[self.data["type"]]["description"])

        match self.data["type"]:
            case "isOneOf":
                self.addEditButton()

        self.delete_button = Gtk.Button()
        self.delete_button.set_icon_name("user-trash-symbolic")
        self.delete_button.set_tooltip_text(_("Delete component"))
        self.delete_button.add_css_class("destructive-action")
        self.delete_button.connect("clicked", self.delete)
        self.add_suffix(self.delete_button)

    def delete(self, *args):
        def delete():
            self.step.filters.remove(self)
            self.step.filter_row.remove(self)
        confirm(
            self.step.parent.parent.edit_timetable_dialog,
            _("Do you want to delete this fiter?"),
            _("Delete"),
            _("Cancel"),
            delete,
        )

    def addEditButton(self):
        self.edit_button = Gtk.Button()
        self.edit_button.set_icon_name("document-edit-symbolic")
        self.edit_button.set_tooltip_text(_("Edit filter"))
        self.add_suffix(self.edit_button)
        self.edit_button.connect("clicked", self.edit)
        self.prepareEdit()

    def edit(self, *args):
        self.edit_window.present(self.get_ancestor(Adw.Dialog))

    def prepareEdit(self):
        self.edit_window = Adw.Dialog()

        self.edit_window.set_title(_("Edit filter"))
        self.edit_window.set_content_width(450)
        self.edit_window.set_content_height(550)

        self.edit_window_content = Adw.ToolbarView()
        self.edit_window.set_child(self.edit_window_content)
        self.edit_window_header = Adw.HeaderBar()
        self.edit_window_content.add_top_bar(self.edit_window_header)

        match self.data["type"]:
            case "isOneOf":
                self.availableKeys = {
                    _("Class/Course"): ["mainStudentGroup", "name"],
                    _("Room"): ["room"],
                    _("Subject (short)"): ["subject", "shortName"],
                    _("Subject (long)"): ["subject", "longName"],
                    _("Teachers (short)"): ["teachers-short"],
                    _("Teachers (long)"): ["teachers-long"],
                }

                page = Adw.PreferencesPage()
                self.edit_window_content.set_content(page)

                upperGroup = Adw.PreferencesGroup()
                page.add(upperGroup)
                self.key = Adw.ComboRow()
                self.key.set_title(_("Key"))
                self.key.set_enable_search(True)
                self.key.set_search_match_mode(Gtk.StringFilterMatchMode.SUBSTRING)
                model = Gtk.StringList()
                i = 0
                position = 0
                for key in self.availableKeys:
                    model.append(key)
                    if self.availableKeys[key] == self.data["key"]:
                        position = i
                    i+=1
                self.key.set_model(model)
                self.key.set_selected(position)
                upperGroup.add(self.key)

                self.items_group = Adw.PreferencesGroup(title = _("Values"))
                self.values = []
                page.add(self.items_group)

                def add(*args):
                    self.addIsOneOfRow("")

                self.add_button = Gtk.Button()
                self.add_button.set_icon_name("list-add-symbolic")
                self.add_button.set_tooltip_text(_("Add value"))
                self.add_button.connect("clicked", add)
                self.items_group.set_header_suffix(self.add_button)

                for value in self.data["values"]:
                    self.addIsOneOfRow(value)

    def addIsOneOfRow(self, value):
        row = Adw.EntryRow()
        row.set_title(_("Value"))
        row.set_text(str(value))

        delete_button = Gtk.Button()
        delete_button.set_icon_name("user-trash-symbolic")
        delete_button.set_tooltip_text(_("Delete value"))
        delete_button.add_css_class("destructive-action")
        row.add_suffix(delete_button)

        def onDelete(*args):
            def code():
                self.values.remove(row)
                self.items_group.remove(row)
            confirm(
                self.get_ancestor(Adw.Dialog),
                _("Do you really want to delete this value?"),
                _("Yes"),
                _("No"),
                code,
            )
        delete_button.connect("clicked", onDelete)

        self.items_group.add(row)
        self.values.append(row)

    def save(self):
        data = self.data.copy()

        match data["type"]:
            case "isOneOf":
                data["key"] = self.availableKeys[self.key.get_selected_item().get_string()]
                values = []
                for value in self.values:
                    values.append(value.get_text())
                data["values"] = values

        return data


class CustomTimetableStep(Adw.ExpanderRow):
    def __init__(self, step, parent):
        super().__init__()
        self.data = step
        self.parent = parent

        self.delete_button = Gtk.Button()
        self.delete_button.set_icon_name("user-trash-symbolic")
        self.delete_button.set_tooltip_text(_("Delete component"))
        self.delete_button.add_css_class("destructive-action")
        self.add_suffix(self.delete_button)

        def onDelete(*args):
            def code():
                self.parent.removeStep(self)
            confirm(
                self.get_ancestor(Adw.Dialog),
                _("Do you really want to delete this step?"),
                _("Yes"),
                _("No"),
                code,
            )
        self.delete_button.connect("clicked", onDelete)

        templates = getTemplates(self.parent.parent)
        self.set_title(templates[step["type"]]["description"])

        match step["type"]:
            case "fromRealTimetable":
                self.src_row = Adw.ComboRow()
                self.src_row.set_title(_("Timetable"))
                self.src_row.set_enable_search(True)
                self.src_row.set_search_match_mode(Gtk.StringFilterMatchMode.SUBSTRING)
                model = Gtk.StringList()
                i = 0
                position = 0
                for timetable in self.parent.parent.shared.session.getAvailableTimetables():
                    model.append(timetable["name"])
                    if timetable["id"] == self.data["timetable"]["id"] and timetable["type"] == self.data["timetable"]["type"]:
                        position = i
                    i += 1
                self.src_row.set_model(model)
                self.src_row.set_selected(position)
                self.add_row(self.src_row)

                self.filter_row = Adw.ExpanderRow()
                self.filter_row.set_title(_("Filters"))
                self.filter_row.set_expanded(True)
                self.add_row(self.filter_row)

                def addFilterOfType(type):
                    filters = getTemplates(self.parent.parent, "filter")
                    filter=filters[type]["template"]
                    filter["type"]=type
                    filterWidget = CustomTimetableFilter(filter, self)
                    self.filters.append(filterWidget)
                    self.filter_row.add_row(filterWidget)

                def addFilter(*args):
                    templates = getTemplates(self.parent.parent, "filter")
                    choices = {}
                    for template in templates:
                        choices[template] = templates[template]["description"]
                    choose(
                        self.parent.parent.edit_timetable_dialog,
                        _("Choose filter"),
                        _("Choose filter"),
                        choices,
                        addFilterOfType
                    )
                self.add_filter_button = Gtk.Button()
                self.add_filter_button.set_icon_name("list-add-symbolic")
                self.add_filter_button.set_tooltip_text(_("Add filter"))
                self.add_filter_button.connect("clicked", addFilter)
                self.filter_row.add_suffix(self.add_filter_button)

                self.filters = []
                for filter in self.data["filters"]:
                    filterWidget = CustomTimetableFilter(filter, self)
                    self.filters.append(filterWidget)
                    self.filter_row.add_row(filterWidget)

    def save(self):
        data = self.data.copy()

        match data["type"]:
            case "fromRealTimetable":
                timetableName = self.src_row.get_selected_item().get_string()
                for timetable in self.parent.parent.shared.session.getAvailableTimetables():
                    if timetable["name"] == timetableName:
                        data["timetable"] = {
                            "id": timetable["id"],
                            "type": timetable["type"],
                        }
                        break
                filters = []
                data["filters"] = filters
                for filter in self.filters:
                    filters.append(filter.save())

        return data

class CustomTimetableBuilder:
    def __init__(self, widget, parent):
        self.widget = widget
        self.parent = parent
        self.steps = []
        self.parent.add_component.connect("clicked", self.createStep)

    def addStepOfType(self, type):
        templates = getTemplates(self.parent)
        template = templates[type]["template"]
        template["type"] = type
        self.addStep(template)

    def createStep(self, *args):
        templates = getTemplates(self.parent)
        choices = {}
        for template in templates:
            choices[template] = templates[template]["description"]
        choose(
            self.parent.edit_timetable_dialog,
            _("Choose component"),
            _("Choose component"),
            choices,
            self.addStepOfType
        )

    def clear(self):
        for step in self.steps.copy():
            self.removeStep(step)

    def removeStep(self, step):
        self.widget.remove(step)
        self.steps.remove(step)

    def addStep(self, step):
        try:
            stepWidget = CustomTimetableStep(step, self)
            self.steps.append(stepWidget)
            self.widget.add(stepWidget)
        except Exception:
            traceback.print_exc()

    def loadRecipe(self, recipe):
        self.clear()
        for step in recipe:
            self.addStep(step)

    def save(self):
        out = []
        for step in self.steps:
            out.append(step.save())
        return out
