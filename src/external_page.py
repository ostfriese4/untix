# external_page.py
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

import gi
gi.require_version('WebKit', '6.0')

from gi.repository import Gtk
from gi.repository import Adw
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import WebKit
import os

@Gtk.Template(resource_path='/page/codeberg/ostfriese4/Untis/external_page.ui')
class ExternalPage(Gtk.Box):
    __gtype_name__ = 'ExternalPage'

    open_button = Gtk.Template.Child()
    back_button = Gtk.Template.Child()
    next_button = Gtk.Template.Child()
    home_button = Gtk.Template.Child()
    view = Gtk.Template.Child()
    title = Gtk.Template.Child()
    progress = Gtk.Template.Child()

    def __init__(self, data, id, **kwargs):
        super().__init__(**kwargs)
        self.loaded = False
        self.id = id
        self.data = data

        self.open_button.connect("clicked", self.open)
        self.title.set_label(data["name"])

        def back(data):
            self.webview.go_back()
        self.back_button.connect("clicked", back)
        def next(data):
            self.webview.go_forward()
        self.next_button.connect("clicked", next)
        def home(data):
            self.webview.load_uri(self.data["redirectUrl"])
        self.home_button.connect("clicked", home)

    def refresh(self):
        self.webview.reload()

    def open(self, data):
        Gio.AppInfo.launch_default_for_uri(self.webview.get_uri(), None)

    def updateButtons(self, data=None, data2=None):
        uri = self.webview.get_uri()
        history = self.webview.get_back_forward_list()

        if uri == self.data["redirectUrl"]:
            self.home_button.set_sensitive(False)
        else:
            self.home_button.set_sensitive(True)

        if history.get_back_item() is None:
            self.back_button.set_sensitive(False)
        else:
            self.back_button.set_sensitive(True)

        if history.get_forward_item() is None:
            self.next_button.set_sensitive(False)
        else:
            self.next_button.set_sensitive(True)

    def toggleProgress(self, webview, loading):
        loading = webview.is_loading()
        self.progress.set_visible(loading)
        self.progress.set_fraction(0)
        if loading:
            GLib.idle_add(self.animateLoad)

    def animateLoad(self):
        self.progress.set_fraction(self.webview.get_estimated_load_progress())
        return self.webview.is_loading() # repeat if loading

    def load(self):
        profile = "profile-" + str(self.shared.profiles["default-profile"])
        dataPath = os.environ.get("XDG_DATA_HOME", ".untis") + "/untis/webview/" + profile
        cachePath = os.environ.get("XDG_CACHE_HOME", ".untis/cache") + "/untis/webview/" + profile
        self.browserSession = WebKit.NetworkSession(
            data_directory=dataPath,
            cache_directory=cachePath
        )

        cookies = self.browserSession.get_cookie_manager()
        cookies.set_persistent_storage(
            dataPath + "/cookies.sqlite", WebKit.CookiePersistentStorage.SQLITE
        )

        self.webview = WebKit.WebView(network_session = self.browserSession)
        self.view.append(self.webview)
        self.webview.set_hexpand(True)
        self.webview.set_vexpand(True)
        self.loaded = True

        self.webview.connect("notify::uri", self.updateButtons)
        self.webview.connect("notify::is-loading", self.toggleProgress)

        self.webview.load_uri(self.data["redirectUrl"])
        self.updateButtons()

    def enable_bindings(self, parent):
        self.shared = parent.shared
        def on_visible(page, pspec):
            if parent.main_view_stack.get_visible_child_name() == self.id:
                if not self.loaded:
                    GLib.idle_add(self.load)
        parent.main_view_stack.connect("notify::visible-child-name", on_visible)

def addExternalPages(window):
    groupName = _("External")

    needed = window.shared.session.getMenu()

    for page in window.dynamicPages:
        if page["group"] == _("External"):
            if page["data"] in needed:
                needed.remove(page["data"])
            else:
                window.dynamicPages.remove(page)

    for pageData in needed:
        id = "external" + pageData["name"] + pageData["redirectUrl"]

        content = ExternalPage(pageData, id)
        content.enable_bindings(window)

        window.dynamicPages.append({
            "group": groupName,
            "data": pageData,
            "widget": content,
            "name": id,
            "icon": "globe-alt-symbolic",
            "title": pageData["name"],
        })

moduleInfo = {
    "pageProviders": [
        {
            "name": "external-pages",
            "code": addExternalPages
        }
    ]
}
