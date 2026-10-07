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
from .create_homework import HomeworkEditWindow
from .credentials import getCredentials
from .api import testCredentials, id as appId
from .profiles import ProfilesWindow
from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Gio
import  traceback


@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/window.ui")
class UntisWindow(Adw.ApplicationWindow):
    __gtype_name__ = "UntisWindow"

    main_view_stack = Gtk.Template.Child()
    sidebar_breakpoint = Gtk.Template.Child()
    split_view = Gtk.Template.Child()
    sidebar = Gtk.Template.Child()

    def __init__(self, shared, **kwargs):
        super().__init__(**kwargs)

        self.pages = []
        self.dynamicPages = []
        self.hiddenPages = []
        self.pageProviders = []

        self.shared = shared
        self.shared.window = self
        self.login_window = LoginWindow(self)
        self.homeworkEditWindow = HomeworkEditWindow(self)
        self.profiles_window = ProfilesWindow(self)

        # runs after the handlers of the pages, so their data is loaded
        self.main_view_stack.connect(
            "notify::visible-child-name", lambda *args: self.updateOfflineBanners()
        )
        self.main_view_stack.connect("notify::visible-child-name", self.refreshPage)

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

        GLib.idle_add(self.loadModules)

    def loadModule(self, name):
        print("loading module", name)
        try:
            module = __import__("untix." + name, fromlist=["*"])
            info = module.moduleInfo
            if "staticPages" in info:
                pages = info["staticPages"]
                for page in pages:
                    self.pages.append(page)
                    page["widget"].enable_bindings(self)
            if "pageProviders" in info:
                providers = info["pageProviders"]
                self.pageProviders += providers
        except Exception:
            traceback.print_exc()

    def loadModules(self):
        for name in [
            "additional_timetables",
            "messages",
            "absences",
            "teachers",
            "homework",
            "external_page",
        ]:
            self.loadModule(name)
        self.showHideViews()

    def updateOfflineBanners(self):
        model = self.main_view_stack.get_pages()
        try:
            offline = self.shared.session.getOffline()
            last = self.shared.session.getLastOnline()
        except AttributeError:
            print("could not get last online information")
            return

        offline_banners = []
        for i in range(model.get_n_items()):
            page = model.get_item(i)
            try:
                offline_banners.append(page.get_child().offline)
            except Exception:
                print(f"page {page.get_name()} does not have an offline-banner")

        for banner in offline_banners:
            banner.update(offline, last)

    def rebuildSidebar(self):
        model = self.main_view_stack.get_pages()
        visiblePage = self.main_view_stack.get_visible_child()
        visiblePages = []
        for i in range(model.get_n_items()):
            page = model.get_item(i)
            visiblePages.append(page.get_child())
        for page in visiblePages:
            self.main_view_stack.remove(page)

        allPages = self.pages + self.dynamicPages
        if self.settings.get_boolean("hide-unsupported-features"):
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
            for page in groups[group].copy():
                if not "prioritize" in page or ("prioritize" in page and not page["prioritize"]):
                    groups[group].remove(page)
                    groups[group].append(page)
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

        for page in allPages:
            if page["widget"] == visiblePage:
                self.main_view_stack.set_visible_child(visiblePage)
        if visiblePage != self.main_view_stack.get_visible_child():
            self.refreshPage()
        self.updateOfflineBanners()

    def hidePage(self, page):
        if not page in self.hiddenPages:
            self.hiddenPages.append(page)

    def showPage(self, page):
        if page in self.hiddenPages:
            self.hiddenPages.remove(page)

    def showHideViews(self):
        for page in self.pages:
            try:
                hide = page["widget"].shouldHide()
            except Exception:
                hide = False
                traceback.print_exc()
            if hide:
                self.hidePage(page)
            else:
                self.showPage(page)

        for provider in self.pageProviders:
            code = provider["code"]
            try:
                code(self)
            except Exception:
                traceback.print_exc()

        self.rebuildSidebar()

    def homeworksChanged(self):
        # keep the homework page and the indicators in the timetable in
        # sync when a homework is created, edited, checked off or deleted
        homework = self.main_view_stack.get_child_by_name("homework")
        if homework is not None:
            homework.displayAll()
        timetable = self.main_view_stack.get_child_by_name("timetable")
        if timetable is not None:
            timetable.refreshHomeworks()
        additional = self.main_view_stack.get_child_by_name("additional_timetables")
        if additional is not None:
            if additional.currentTimetable is not None:
                additional.currentTimetable.refreshHomeworks()

    def refreshPage(self, *args, reason = "open"):
        try:
            page = self.main_view_stack.get_visible_child()
            page.refresh(reason)
        except Exception:
            print("refresh not implemented by page", self.main_view_stack.get_visible_child_name())
            self.shared.session.getOwnId() # request to update online status

    def refresh(self):
        self.shared.session.refresh()
        self.refreshPage(reason = "refresh")
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
