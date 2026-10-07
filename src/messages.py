# messages.py
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
from gi.repository import GObject
from gi.repository import GLib
from .offline_banner import OfflineBanner
from .attachment import Attachment
from .api import getDate

import datetime
import re
from html.parser import HTMLParser

URL_PATTERN = re.compile(r"(?:https?://|www\.)[^\s<>\"]*[^\s<>\".,;:!?)]")

# HTML tags that have an equivalent in Pango markup
FORMAT_TAGS = {
    "b": "b",
    "strong": "b",
    "i": "i",
    "em": "i",
    "u": "u",
    "s": "s",
    "strike": "s",
    "del": "s",
}


def linkify(text):
    """Escapes text for Pango markup and turns URLs into clickable links"""
    markup = ""
    end = 0
    for match in URL_PATTERN.finditer(text):
        url = match.group()
        href = url if "://" in url else "https://" + url
        markup += GLib.markup_escape_text(text[end : match.start()])
        markup += '<a href="{}">{}</a>'.format(
            GLib.markup_escape_text(href), GLib.markup_escape_text(url)
        )
        end = match.end()
    return markup + GLib.markup_escape_text(text[end:])


class MarkupParser(HTMLParser):
    """Converts message HTML to Pango markup, keeping links and basic formatting"""

    def __init__(self):
        super().__init__()
        self.markup = ""
        self.open = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.markup += "\n"
        elif tag == "li":
            self.markup += "\n• "
        elif tag == "a":
            href = dict(attrs).get("href")
            if href and "a" not in self.open:
                self.markup += '<a href="{}">'.format(GLib.markup_escape_text(href))
                self.open.append("a")
        elif tag in FORMAT_TAGS:
            self.markup += "<{}>".format(FORMAT_TAGS[tag])
            self.open.append(FORMAT_TAGS[tag])

    def handle_endtag(self, tag):
        if tag in ("p", "div", "ul", "ol"):
            self.markup += "\n"
        tag = FORMAT_TAGS.get(tag, tag)
        if tag in self.open:
            # also close tags that were not closed properly inside of it
            while self.open:
                closed = self.open.pop()
                self.markup += "</{}>".format(closed)
                if closed == tag:
                    break

    def handle_data(self, data):
        if "a" in self.open:
            self.markup += GLib.markup_escape_text(data)
        else:
            self.markup += linkify(data)

    def close(self):
        super().close()
        while self.open:
            self.markup += "</{}>".format(self.open.pop())


def toMarkup(text):
    """Converts message HTML to Pango markup with clickable links"""
    parser = MarkupParser()
    parser.feed(text)
    parser.close()
    return parser.markup.strip()


class Message(Adw.ExpanderRow):
    __gtype_name__ = "Message"

    def __init__(self, message, session, **kwargs):
        super().__init__(**kwargs)

        self.set_title(message["subject"])
        self.set_subtitle(message["contentPreview"])
        self.set_subtitle_lines(1)

        self.message = message
        self.loaded = False
        self.session = session

        if message["hasAttachments"]:
            attachmentIcon = Gtk.Image(icon_name="xsi-mail-attachment-symbolic")
            self.add_suffix(attachmentIcon)

        self.connect("notify::expanded", self.load)

    def load(self, a, b):
        if not self.loaded:
            self.loaded = True
            message = self.session.getMessageById(self.message["id"])

            content = Adw.ActionRow(title=toMarkup(message["content"]))
            self.add_row(content)
            content.add_css_class("property")

            attachments = self.session.getAttachments(message)
            for attachment in attachments:
                attachment_row = Attachment(attachment, self.session)
                self.add_row(attachment_row)

            date = Adw.ActionRow(
                title=_("Date"),
                subtitle=datetime.datetime.strptime(
                    self.message["sentDateTime"], "%Y-%m-%dT%H:%M:%S"
                ).strftime("%c"),
            )
            self.add_row(date)
            date.add_css_class("property")

            sender = Adw.ActionRow(
                title=_("Sender"), subtitle=message["sender"]["displayName"]
            )
            self.add_row(sender)
            sender.add_css_class("property")


@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/messages.ui")
class MessagesPage(Gtk.Box):
    __gtype_name__ = "MessagesPage"

    offline = Gtk.Template.Child()
    container = Gtk.Template.Child()
    news_of_day = Gtk.Template.Child()
    prev_day = Gtk.Template.Child()
    next_day = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.displayed = []
        self.displayedNews = []
        self.date = getDate()
        self.prev_day.connect("clicked", self.prev)
        self.next_day.connect("clicked", self.next)

    def enable_bindings(self, parent):
        def on_visible(page, pspec):
            if parent.main_view_stack.get_visible_child_name() == "messages":
                self.display()

        parent.main_view_stack.connect("notify::visible-child-name", on_visible)
        self.shared = parent.shared
        self.parent = parent

    def onAdded(self):
        self.countUnread()

    def shouldHide(self):
        messages = self.shared.session.getMessages()
        if messages is not None and messages != []:
            return False

        news = self.shared.session.getNewsOfDay()
        if news is not None and news != []:
            return False

        return True

    def refresh(self):
        self.display()

    def countUnread(self):
        try:
            count = self.shared.session.getUnreadMessagesCount()
            print(count, "unread messages")
        except:
            count = 0
            print("could not count unread messages")
        page = self.parent.main_view_stack.get_page(self)
        page.set_badge_number(count)

    def next(self, *args):
        self.date += datetime.timedelta(days=1)
        self.display()

    def prev(self, *args):
        self.date -= datetime.timedelta(days=1)
        self.display()

    def display(self):
        self.news_of_day.set_title(self.date.strftime(_("News of %m/%d/%Y")))

        messages = self.shared.session.getMessages()

        while self.displayed != []:
            row = self.displayed.pop()
            self.container.remove(row)
        while self.displayedNews != []:
            row = self.displayedNews.pop()
            self.news_of_day.remove(row)

        self.container.set_visible(True)
        for message in messages:
            row = Message(message, self.shared.session)
            self.container.add(row)
            self.displayed.append(row)
        if messages == []:
            self.container.set_visible(False)

        news = self.shared.session.getNewsOfDay(self.date)
        self.news_of_day.set_visible(True)
        if news == []:
            news = [
                {
                    "text": "",
                    "subject": _("No News for this day"),
                }
            ]
        for item in news:
            row = Adw.ActionRow(title=item["subject"], subtitle=toMarkup(item["text"]))
            self.news_of_day.add(row)
            self.displayedNews.append(row)

        self.countUnread()

moduleInfo = {
    "staticPages": [
        {
            "group": _("Modules"),
            "widget": MessagesPage(),
            "name": "messages",
            "title": _("Messages"),
            "icon": "mail-unread-symbolic",
        }
    ]
}
