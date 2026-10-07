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

    main_view_stack = Gtk.Template.Child()
    sidebar_breakpoint = Gtk.Template.Child()
    split_view = Gtk.Template.Child()
    sidebar = Gtk.Template.Child()

    def __init__(self, shared, **kwargs):
        super().__init__(**kwargs)

        self.absences = AbsencesPage()
        self.additional_timetables = AdditionalTimetablesPage()
        self.homework = HomeworkList()
        self.messages = MessagesPage()
        self.teachers = TeacherPage()
        self.timetable = Timetable()

        self.pages = [
            {
                "group": _("Timetables"),
                "widget": self.timetable,
                "name": "timetable",
                "title": _("My timetable"),
                "icon": "month-symbolic",
            },
            {
                "group": _("Timetables"),
                "widget": self.additional_timetables,
                "name": "additional_timetables",
                "title": _("All timetables"),
                "icon": "month-symbolic",
            },
            {
                "group": _("Modules"),
                "widget": self.homework,
                "name": "homework",
                "title": _("Homework"),
                "icon": "agenda-symbolic",
            },
            {
                "group": _("Modules"),
                "widget": self.absences,
                "name": "absences",
                "title": _("Absences"),
                "icon": "appointment-soon-symbolic",
            },
            {
                "group": _("Modules"),
                "widget": self.messages,
                "name": "messages",
                "title": _("Messages"),
                "icon": "mail-unread-symbolic",
            },
            {
                "group": _("Modules"),
                "widget": self.teachers,
                "name": "teachers",
                "title": _("Teachers"),
                "icon": "system-users-symbolic",
            },
        ]
        self.dynamicPages = []
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
            "changed::hide-unsupported-features", lambda *args: self.rebuildSidebar()
        )

        self.sidebar.connect("activated", lambda *args: self.split_view.set_show_content(True))

        def renameWindow(*args):
            child = self.main_view_stack.get_visible_child()
            if child is not None:
                page = self.main_view_stack.get_page(child)
                title = page.get_title()
                self.set_title(title)
            else:
                self.set_title(_("Untix"))
        renameWindow()
        self.main_view_stack.connect("notify::visible-child-name", renameWindow)

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

    def rebuildSidebar(self):
        model = self.main_view_stack.get_pages()
        visiblePage = self.main_view_stack.get_visible_child()
        visiblePages = []
        for i in range(model.get_n_items()):
            page = model.get_object(i)
            visiblePages.append(page.get_child())
        for page in visiblePages:
            self.main_view_stack.remove(page)

        allPages = self.pages + self.dynamicPages
        for page in allPages.copy():
            if page["widget"] in self.hiddenPages:
                allPages.remove(page)

        groups = {}
        for page in allPages:
            group = page["group"]
            if group not in groups:
                groups[group] = []
            groups[group].append(page)

        for group in groups:
            first = True
            for p in groups[group]:
                page = self.main_view_stack.add(p["widget"])
                page.set_title(p["title"])
                page.set_name(p["name"])
                page.set_icon_name(p["icon"])
                if first:
                    first = False
                    page.set_starts_section(True)
                    page.set_section_title(group)
                if p["widget"] not in visiblePages:
                    try:
                        GLib.idle_add(p["widget"].onAdded)
                    except Exception:
                        print(f"page {p["name"]} does not support onAdded")

        if visiblePage in allPages:
            self.main_view_stack.set_visible_child(visiblePage)

    def hidePage(self, page):
        if not page in self.hiddenPages:
            self.hiddenPages.append(page)

    def shouldViewHide(self, name):
        show = name in self.shared.session.getPermissions()["views"]
        return not show

    def showPage(self, page):
        if page in self.hiddenPages:
            self.hiddenPages.remove(page)

    def showHideViews(self):
        if self.messages.shouldHide():
            self.hidePage(self.messages)
        else:
            self.showPage(self.messages)

        if self.absences.shouldHide():
            self.hidePage(self.absences)
        else:
            self.showPage(self.absences)

        if self.teachers.shouldHide():
            self.hidePage(self.teachers)
        else:
            self.showPage(self.teachers)

        if self.additional_timetables.shouldHide():
            self.hidePage(self.additional_timetables)
        else:
            self.showPage(self.additional_timetables)

        self.addExternalPages()
        self.rebuildSidebar()

    def addExternalPages(self):
        groupName = _("External")

        needed = self.shared.session.getMenu()

        for page in self.dynamicPages:
            if page["group"] == _("External"):
                if page["data"] in needed:
                    needed.remove(page["data"])
                else:
                    self.dynamicPages.remove(page)

        for pageData in needed:
            id = "external" + pageData["name"] + pageData["redirectUrl"]

            content = ExternalPage(pageData, id)
            content.enable_bindings(self)

            self.dynamicPages.append({
                "group": groupName,
                "data": pageData,
                "widget": content,
                "name": id,
                "icon": "globe-alt-symbolic",
                "title": pageData["name"],
            })

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
        self.showHideViews()

    def checkCredentials(self):
        print("check credentials")

        login = not testCredentials(getCredentials(self.shared.profiles["default-profile"]))

        if login:
            self.login_window.requestLogin(self.shared.profiles["default-profile"])

        if not self.shared.session.getOffline():
            self.shared.checked = True
