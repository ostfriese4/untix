# attachment.py
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

import os
import requests
import subprocess
from hashlib import md5
from pathlib import Path
from gi.repository import Gtk
from gi.repository import Adw
from gi.repository import Gio


@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/attachment.ui")
class Attachment(Adw.ActionRow):
    __gtype_name__ = "Attachment"

    open_button = Gtk.Template.Child()
    save_button = Gtk.Template.Child()


    def __init__(self, attachment, session,  **kwargs):
        super().__init__(**kwargs)
        self.data = attachment
        self.session = session

        self.set_title(attachment["name"])

        self.open_button.connect("clicked", self.open)
        self.save_button.connect("clicked", self.save)

    def open(self, *args):
        path = self.download()
        Gio.AppInfo.launch_default_for_uri("file://" + path)

    def save(self, *args):
        path = self.getDownloadPath()
        dialog = Gtk.FileDialog()
        dialog.set_initial_name(os.path.basename(path))
        dialog.save(
            self.get_ancestor(Adw.ApplicationWindow),
            None,
            self.finishSave,
            dialog
        )
        self.download()

    def finishSave(self, source, result, dialog):
        origPath = self.download()
        file = dialog.save_finish(result)
        newPath = file.get_path()
        subprocess.run([
            "cp",
            "-f",
            origPath,
            newPath
        ])

    def download(self):
        path = self.getDownloadPath()
        if not self.isDownloaded():
            url = self.getDownloadUrl()
            print(url)
            headers = {}
            for header in url["additionalHeaders"]:
                headers[header["key"]] = header["value"]
            remotePath = url["downloadUrl"]
            response = requests.get(remotePath, headers = headers, stream = True)
            with open(path, "wb") as file:
                for chunk in response.iter_content():
                    file.write(chunk)
        return path

    def isDownloaded(self):
        path = self.getDownloadPath()
        return os.path.exists(path)

    def getDownloadPath(self):
        name = str(self.data)
        hashed = md5(name.encode()).hexdigest()
        basePath = os.environ.get("XDG_CACHE_HOME", ".untis/cache") + "/untis/attachments/"
        path = basePath + hashed + "/" + self.data["name"]
        Path(path).parent.mkdir(exist_ok=True, parents=True)
        return path

    def getDownloadUrl(self):
        match self.data["type"]:
            case "storageAttachment":
                return self.session.getAttachmentStorageUrl(self.data["id"])
