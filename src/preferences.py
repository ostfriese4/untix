# preferences.py
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
from gi.repository import Gio
from .api import id
from .dialog import closeOnClickOutside


@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/preferences.ui")
class PreferencesDialog(Adw.PreferencesDialog):
    __gtype_name__ = "PreferencesDialog"

    show_cancelled = Gtk.Template.Child()
    show_time_axis = Gtk.Template.Child()
    ignore_exam_breaks = Gtk.Template.Child()
    hide_unsupported_features = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        closeOnClickOutside(self)

        self.settings = Gio.Settings(schema_id=id)
        self.settings.bind(
            "show-cancelled-lessons",
            self.show_cancelled,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        self.settings.bind(
            "show-time-axis",
            self.show_time_axis,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        self.settings.bind(
            "ignore-exam-breaks",
            self.ignore_exam_breaks,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        self.settings.bind(
            "hide-unsupported-features",
            self.hide_unsupported_features,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
