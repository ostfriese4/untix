# window.py
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

from .login import LoginWindow
from .timetable import Timetable
from .additional_timetables import AdditionalTimetablesPage
from .homework import HomeworkList
from .teachers import TeacherPage
from .messages import MessagesPage
from .absences import AbsencesPage
from .create_homework import HomeworkEditWindow
from .credentials import getCredentials
from .api import testCredentials, id as appId
from .profiles import ProfilesWindow
from .external_page import ExternalPage
from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Gio


@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/window.ui")
class UntisWindow(Adw.ApplicationWindow):
    __gtype_name__ = "UntisWindow"

    timetable = Gtk.Template.Child()
    absences = Gtk.Template.Child()
    absences_page = Gtk.Template.Child()
    additional_timetables = Gtk.Template.Child()
    homework = Gtk.Template.Child()
    homework_page = Gtk.Template.Child()
    main_view_stack = Gtk.Template.Child()
    sidebar_breakpoint = Gtk.Template.Child()
    split_view = Gtk.Template.Child()
    sidebar = Gtk.Template.Child()
    teachers = Gtk.Template.Child()
    messages = Gtk.Template.Child()
    messages_page = Gtk.Template.Child()

    def __init__(self, shared, **kwargs):
        super().__init__(**kwargs)

        self.pages = []
        self.hiddenPages = []

        self.shared = shared
        self.login_window = LoginWindow(self)
        self.homeworkEditWindow = HomeworkEditWindow(self)
        self.profiles_window = ProfilesWindow(self)

        self.timetable.enable_bindings(self)
        self.homework.enable_bindings(self)
        self.teachers.enable_bindings(self)
        self.messages.enable_bindings(self)
        self.absences.enable_bindings(self)
        self.additional_timetables.enable_bindings(self)

        # runs after the handlers of the pages, so their data is loaded
        self.main_view_stack.connect(
            "notify::visible-child-name", lambda *args: self.updateOfflineBanners()
        )

        self.settings = Gio.Settings(schema_id=appId)
        self.settings.connect(
            "changed::hide-unsupported-features", lambda *args: self.showHideViews()
        )

        self.sidebar.connect("activated", lambda *args: self.split_view.set_show_content(True))

        def renameWindow(*args):
            child = self.main_view_stack.get_visible_child()
            page = self.main_view_stack.get_page(child)
            title = page.get_title()
            self.set_title(title)
        renameWindow()
        self.main_view_stack.connect("notify::visible-child-name", renameWindow)

        GLib.idle_add(self.addExternalPages)
        GLib.idle_add(self.showHideViews)
        GLib.idle_add(self.updateOfflineBanners)

    def updateOfflineBanners(self):
        try:
            offline = self.shared.session.getOffline()
            last = self.shared.session.getLastOnline()
        except AttributeError:
            print("could not get last online information")
            return

        offline_banners = [
            self.timetable.offline,
            self.homework.offline,
            self.teachers.offline,
            self.messages.offline,
            self.absences.offline,
            self.additional_timetables.offline,
            self.additional_timetables.nested_offline,
        ]

        for banner in offline_banners:
            banner.update(offline, last)

    def hidePage(self, name):
        if not self.settings.get_boolean("hide-unsupported-features"):
            return self.showPage(name)
        if not name in self.hiddenPages:
            page = self.main_view_stack.get_child_by_name(name)
            self.main_view_stack.remove(page)
            self.hiddenPages.append(name)
            print("hide page",name)

    def shouldViewHide(self, name):
        show = name in self.shared.session.getPermissions()["views"]
        return not show

    def showPage(self, name):
        if name in self.hiddenPages:
            page = self.main_view_stack.get_child_by_name(name)
            self.main_view_stack.append(page)
            self.hiddenPages.remove(name)
            print("show page",name)

    def showHideViews(self):
        if self.messages.shouldHide():
            self.hidePage("messages")
        else:
            self.showPage("messages")

        if self.absences.shouldHide():
            self.hidePage("absences")
        else:
            self.showPage("absences")

        if self.teachers.shouldHide():
            self.hidePage("teachers")
        else:
            self.showPage("teachers")

        if self.additional_timetables.shouldHide():
            self.hidePage("additional_timetables")
        else:
            self.showPage("additional_timetables")

    def addExternalPages(self):
        for page in self.pages:
            self.main_view_stack.remove(page)
        self.pages.clear()

        first = True
        for pageData in self.shared.session.getMenu():
            id = "external" + str(len(self.pages))
            content = ExternalPage(pageData, id)

            page = self.main_view_stack.add(content)
            page.set_title(pageData["name"])
            page.set_name(id)
            page.set_icon_name("globe-alt-symbolic")

            if first:
                first = False
                page.set_starts_section(True)
                #page.set_section_title(_("External services"))

            content.enable_bindings(self)

            self.pages.append(content)

    def homeworksChanged(self):
        # keep the homework page and the indicators in the timetable in
        # sync when a homework is created, edited, checked off or deleted
        self.homework.displayAll()
        self.timetable.refreshHomeworks()

    def refresh(self):
        self.shared.session.refresh()
        try:
            page = self.main_view_stack.get_visible_child()
            page.refresh()
        except Exception:
            print("refresh not implemented by page", self.main_view_stack.get_visible_child_name())
            self.shared.session.getOwnId() # request to update online status
        self.updateOfflineBanners()

    def reload(self):
        self.checkCredentials()
        self.main_view_stack.set_visible_child_name("timetable")
        self.timetable.loadData()
        try:
            self.shared.session.getHomeworks()
        except:
            pass
        self.homework.displayAll()
        self.addExternalPages()
        self.showHideViews()

    def checkCredentials(self):
        print("check credentials")

        login = not testCredentials(getCredentials(self.shared.profiles["default-profile"]))

        if login:
            self.login_window.requestLogin(self.shared.profiles["default-profile"])

        if not self.shared.session.getOffline():
            self.shared.checked = True
