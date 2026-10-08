# lesson.py
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
from gi.repository import Gdk
from gi.repository import Adw
from gi.repository import Pango
from .colors import serverColorClass
import datetime


def strikeOut(label):
    # pango's strikethrough is hair-thin, draw a thick line instead
    overlay = Gtk.Overlay()
    overlay.set_child(label)
    line = Gtk.Box()
    line.add_css_class("strike")
    line.set_valign(Gtk.Align.CENTER)
    line.set_can_target(False)
    overlay.add_overlay(line)
    return overlay


class ConstrainedScrolledWindow(Gtk.ScrolledWindow):
    __gtype_name__ = "ConstrainedScrolledWindow"

    def __init__(self, start, duration, labels, **kwargs):
        super().__init__(**kwargs)
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
        self.start = start
        self.duration = duration
        self.box = Gtk.Box(orientation="vertical")
        self.box.set_hexpand(True)
        for label in labels:
            label.set_halign(Gtk.Align.START)
            label.set_margin_start(8)
            self.box.append(label)
        self.set_child(self.box)


class LessonContent(Gtk.Widget):
    __gtype_name__ = "LessonContent"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_hexpand(True)

    def add_label(self, lesson):
        lesson.set_parent(self)

    def do_dispose(self):
        for child in list(self):
            child.unparent()

    def do_measure(self, orientation, for_size):
        w_min, w_nat, b_min, b_nat = 1, 1, -1, -1
        for child in self:
            c_min, c_nat, _, _ = child.measure(orientation, -1)
            if orientation == Gtk.Orientation.VERTICAL:
                w_min = max(w_min, c_min)
            else:
                w_min = max(w_min, c_min)
                w_nat = max(w_nat, c_nat)
        w_nat = max(w_min, w_nat)
        return w_min, w_nat, b_min, b_nat

    def do_size_allocate(self, width, height, baseline):
        rect = Gdk.Rectangle()
        rect.x, rect.width = 0, width
        for child in self:
            rect.y = child.start * height
            rect.height = child.duration - 6
            child.size_allocate(rect, baseline)


@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/lesson.ui")
class Lesson(Gtk.Overlay):
    __gtype_name__ = "Lesson"

    homework_indicator = Gtk.Template.Child()
    info_indicator = Gtk.Template.Child()
    content_box = Gtk.Template.Child()

    def __init__(self, lesson, window, now, **kwargs):
        super().__init__(**kwargs)

        click = Gtk.GestureClick.new()
        click.connect("released", self.on_click)
        self.add_controller(click)

        self.lesson = lesson
        self.window = window

        subject = self.lesson["subject"]
        self.subject_label = Gtk.Label(label=subject.get("displayName") or subject["shortName"])
        self.subject_label.add_css_class("subject")
        self.teacher_label = Gtk.Label(label=self.lesson["teachers-short"])
        self.room_label = Gtk.Label(label=self.lesson["room"])
        for label in (self.subject_label, self.teacher_label, self.room_label):
            # don't force a minimum width, parallel lessons can be narrow
            label.set_ellipsize(Pango.EllipsizeMode.END)

        stripe = Gtk.Box()
        stripe.add_css_class("colorstripe")
        stripe.set_size_request(10, -1)
        if self.lesson["color"].startswith("#"):  # color from WebUntis
            stripe.add_css_class(serverColorClass(self.lesson["color"]))
        else:
            stripe.add_css_class(self.lesson["color"])
        self.content_box.append(stripe)

        labels = [self.subject_label, self.teacher_label, self.room_label]
        if self.lesson["status"] == "CANCELLED":
            labels = [strikeOut(label) for label in labels]

        self.content = LessonContent()
        self.content.add_label(
            ConstrainedScrolledWindow(
                0,
                self.lesson["duration"],
                labels,
            )
        )
        self.content_box.append(self.content)

        self.set_size_request(-1, self.lesson["duration"])
        self.set_size_request(-1, self.lesson["duration"])
        if self.lesson["status"] == "CANCELLED":
            self.add_css_class("cancelled")
        elif self.lesson["gridType"] == "EXAM":
            self.add_css_class("exam")
        elif (
            "original" in self.lesson
            or self.lesson.get("gridStatus") == "CHANGED"
            or self.lesson.get("gridType") == "EVENT"
        ):
            self.add_css_class("changed")
        if self.lesson.get("lessonInfo") or self.lesson.get("teachingContent"):
            self.info_indicator.set_visible(True)
        if datetime.datetime.strptime(self.lesson["endDateTime"], "%Y-%m-%dT%H:%M:%S") < now:
            self.add_css_class("past")
        if "original" in self.lesson:
            self.add_css_class("changed")
            if (
                self.lesson["original"]["teachers-short"]
                != self.lesson["teachers-short"]
            ):
                self.teacher_label.add_css_class("label")
                self.teacher_label.add_css_class("changed")
            if (
                self.lesson["original"]["subject"]["shortName"]
                != self.lesson["subject"]["shortName"]
            ):
                self.subject_label.add_css_class("label")
                self.subject_label.add_css_class("changed")
            if self.lesson["original"]["room"] != self.lesson["room"]:
                self.room_label.add_css_class("label")
                self.room_label.add_css_class("changed")

        self.markedAsHidden = False
        self.lesson["homeworks"] = []

    def markAsHidden(self):
        self.markedAsHidden = True

    def on_click(self, gesture, data, x, y):
        if not self.markedAsHidden:
            self.window.information_window.setLesson(self.lesson)
        else:
            print("don't open", self.lesson)

    def clearHomeworks(self):
        self.lesson["homeworks"] = []
        self.homework_indicator.set_visible(False)

    def addHomework(self, homework):
        if "homeworks" in self.lesson:
            homeworks = self.lesson["homeworks"]
        else:
            homeworks = []
            self.lesson["homeworks"] = homeworks
        homeworks.append(homework)
        self.homework_indicator.set_visible(True)
