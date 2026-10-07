# timetable.py
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
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from .homework_api import fetchHomeworks
from .information import InformationWindow
from .lesson import Lesson
from .holiday import Holiday
from .offline_banner import OfflineBanner
from .dialog import closeOnClickOutside
from .api import getDateTime, id as appId
import cairo
import datetime
import math
import time
import threading


class DayLayout(Gtk.Widget):
    __gtype_name__ = "DayLayout"

    # places the lessons of one day on a minute grid and puts
    # overlapping lessons next to each other, like the mobile app

    def __init__(self, start, end, **kwargs):
        super().__init__(**kwargs)
        self.set_hexpand(True)
        self.start = start
        self.end = end

    def add(self, child):
        child.set_parent(self)

    def remove(self, child):
        child.unparent()

    def do_dispose(self):
        for child in list(self):
            child.unparent()

    def do_measure(self, orientation, for_size):
        if orientation == Gtk.Orientation.VERTICAL:
            height = max(self.end - self.start, 0)
            return height, height, -1, -1
        minimum = 0
        for child in self:
            c_min, c_nat, _, _ = child.measure(orientation, -1)
            minimum = max(minimum, c_min)
        return minimum, minimum, -1, -1

    def do_size_allocate(self, width, height, baseline):
        for child in self:
            layoutStart = child.lesson.get("layoutStart") or 0
            layoutWidth = child.lesson.get("layoutWidth") or 1000
            rect = Gdk.Rectangle()
            rect.x = width * layoutStart // 1000
            rect.width = width * layoutWidth // 1000
            if layoutStart + layoutWidth < 1000:
                rect.width -= 2  # a little gap between parallel lessons
            rect.y = child.lesson["start"] - self.start
            rect.height = child.lesson["end"] - child.lesson["start"]
            child.size_allocate(rect, baseline)


@Gtk.Template(resource_path="/page/codeberg/ostfriese4/Untis/timetable.ui")
class Timetable(Gtk.Box):
    __gtype_name__ = "Timetable"

    overlay = Gtk.Template.Child()
    offline = Gtk.Template.Child()
    timetable = Gtk.Template.Child()
    next_button = Gtk.Template.Child()
    previous_button = Gtk.Template.Child()

    progress = Gtk.Template.Child()

    header_button = Gtk.Template.Child()
    date_chooser = Gtk.Template.Child()
    date_chooser_dialog = Gtk.Template.Child()

    def __init__(self, resourceType = None, resourceId = None, id = "timetable", **kwargs):
        super().__init__(**kwargs)

        self.id = id

        self.columns = []
        self.lessons = []
        self.overlays = []
        self.prefetching = []

        self.resourceType = resourceType
        self.resourceId = resourceId

        self.information_window = InformationWindow(self)

        self.next_button.connect("clicked", self.next)
        self.previous_button.connect("clicked", self.previous)
        self.header_button.connect("clicked", self.on_header_button)
        self.date_chooser.connect("day-selected", self.on_day_selected)
        closeOnClickOutside(self.date_chooser_dialog)

        self.loading = False

        self.info_rows = []

        def onSwipe(gesture, x, y):
            if abs(y) < abs(x) * 0.5:
                if x > 100:
                    self.previous()
                elif x < 100:
                    self.next()

        swipe = Gtk.GestureSwipe()
        swipe.connect("swipe", onSwipe)
        self.timetable.add_controller(swipe)

        self.settings = Gio.Settings(schema_id=appId)
        self.settings.connect(
            "changed::show-cancelled-lessons", lambda *args: self.loadData()
        )
        self.settings.connect(
            "changed::show-time-axis", lambda *args: self.loadData()
        )
        self.settings.connect(
            "changed::ignore-exam-breaks", lambda *args: self.loadData()
        )

        GLib.timeout_add(1000 * 60, self.update_marker)  # update time-marker
        GLib.timeout_add(
            1000 * 60 * 10, self.loadData
        )  # Update every ten minutes (will result in every hour because of caching)

    def on_header_button(self, data=None):
        self.date_chooser.set_year(self.startdate.year)
        self.date_chooser.set_month(self.startdate.month - 1)
        self.date_chooser.set_day(self.startdate.day)
        self.date_chooser_dialog.present(self.get_ancestor(Adw.ApplicationWindow))

    def on_day_selected(self, date):
        date = datetime.datetime.strptime(
            self.date_chooser.get_date().format("%d-%m-%Y"), "%d-%m-%Y"
        )
        self.date_chooser_dialog.close()
        self.jump_to(date)

    def jump_to(self, date):
        self.startdate = date - datetime.timedelta(days=date.weekday())
        self.enddate = self.startdate + datetime.timedelta(days=4)
        while self.enddate < date:
            self.next()
        self.loadData()

    def update_marker(self):
        for overlay in self.overlays:
            overlay[1].queue_draw()
        return True

    def enable_bindings(self, parent):
        self.shared = parent.shared

        self.window = parent
        try:
            self.jump_to(getDateTime())
        except:
            pass

    def next(self, data=None):
        self.startdate += datetime.timedelta(days=7)
        self.enddate += datetime.timedelta(days=7)
        self.loadData()

    def previous(self, data=None):
        self.startdate -= datetime.timedelta(days=7)
        self.enddate -= datetime.timedelta(days=7)
        self.loadData()

    def refresh(self):
        self.loadData()

    def refreshHomeworks(self):
        for lesson in self.lessons:
            lesson[1].clearHomeworks()
        homeworks = fetchHomeworks(self.startdate, self.enddate)
        self.displayHomeworks(homeworks)

    def getTimetable(self, start, end, mode="normal"):
        if self.resourceType:
            return self.shared.session.getTimetable(self.resourceType, self.resourceId, start, end, mode=mode)
        else:
            return self.shared.session.getOwnTimetable(start, end, mode=mode)

    def prefetch(self):
        def code():
            while self.prefetching != []:
                day = self.prefetching[0]
                data = self.getTimetable(day, day)
                self.prefetching.remove(day)
            return False

        ok = self.prefetching == []

        start = self.startdate + datetime.timedelta(days=7)
        for date in (start + datetime.timedelta(n) for n in range(5)):
            self.prefetching.append(date)
        start = self.startdate - datetime.timedelta(days=7)
        for date in (start + datetime.timedelta(n) for n in range(5)):
            self.prefetching.append(date)

        if ok:
            thread = threading.Thread(target=code, daemon=True)
            thread.start()

    def loadingAnimation(self):
        if not self.loading:
            self.loading = True
            self.progress.set_visible(True)

            def code():
                while self.loading:
                    self.progress.pulse()
                    time.sleep(0.2)
                self.progress.set_visible(False)

            thread = threading.Thread(target=code, daemon=True)
            thread.start()

    def loadData(self, data = None, data2 = None):
        self.loadingAnimation()
        s = self.startdate

        if not self.shared.checked:
            self.window.checkCredentials()

        def load():
            try:
                data = self.getTimetable(
                    self.startdate, self.enddate, mode="cache"
                )
                table, grid = data
                grid = self.shared.session.getTimeGrid(grid)
                table = (table, grid)
            except:
                table = None
            try:
                if s == self.startdate:
                    GLib.idle_add(self.displayData, table)
                    data = self.getTimetable(
                        self.startdate, self.enddate, mode="normal"
                    )
                    table, grid = data
                    grid = self.shared.session.getTimeGrid(grid)
                    if s == self.startdate:
                        GLib.idle_add(self.displayData, (table, grid))
                        homeworks = fetchHomeworks(self.startdate, self.enddate)
                        if s == self.startdate:
                            GLib.idle_add(self.displayHomeworks, homeworks)
                            self.loading = False
                            self.prefetch()
            except:
                self.loading = False
                raise
            return False

        thread = threading.Thread(target=load, daemon=True)
        thread.start()
        return True  # To repeat

    def displayHomeworks(self, data):
        for homework in data:
            lessons = []
            for lesson in self.lessons:
                ld = lesson[2]
                dueDate = datetime.datetime.strptime(ld["startDateTime"], "%Y-%m-%dT%H:%M:%S").strftime("%Y%m%d")
                if ld["subject"]["shortName"] == homework["subject"]:
                    if str(homework["dueDate"]) == dueDate:
                        lesson[1].addHomework(homework)
                        break
                if "original" in ld:
                    if "subject" in ld["original"]:
                        if (
                            ld["original"]["subject"]["shortName"]
                            == homework["subject"]
                        ):
                            if str(homework["dueDate"]) == dueDate:
                                lessons.append(lesson[1])
            for lesson in lessons:
                lesson.addHomework(homework)

    def drawTimeMarker(self, area, context, width, height, dateLabel, week):
        now = getDateTime()
        y = now.hour * 60 + now.minute - self.start + dateLabel.get_allocated_height()

        context.set_source_rgb(1, 0, 0)
        if week:
            context.set_line_width(1)
        else:
            context.set_line_width(4)
        context.move_to(0, y)
        context.line_to(width, y)
        context.stroke()

        if week and self.showAxis:  # show the current time on the marker, on top of the time axis
            text = now.strftime("%H:%M")
            context.select_font_face(
                "sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD
            )
            context.set_font_size(11)
            extents = context.text_extents(text)
            chipWidth = extents.width + 12
            radius = (extents.height + 8) / 2
            context.new_sub_path()
            context.arc(2 + radius, y, radius, 0.5 * math.pi, 1.5 * math.pi)
            context.arc(2 + chipWidth - radius, y, radius, 1.5 * math.pi, 0.5 * math.pi)
            context.close_path()
            context.fill()
            context.set_source_rgb(1, 1, 1)
            context.move_to(2 + 6, y + extents.height / 2)
            context.show_text(text)

    def timeToMinutes(self, time):
        dt = datetime.datetime.strptime(time, "%H:%M")
        return self.dateTimeToMinutes(dt)

    def dateTimeToMinutes(self, dt):
        return dt.minute + dt.hour * 60

    def drawTimeAxis(self, area, context, width, height):
        color = area.get_color()
        context.select_font_face(
            "sans", cairo.FontSlant.NORMAL, cairo.FontWeight.NORMAL
        )
        context.set_font_size(11)

        def drawLabel(minutes):
            y = minutes - self.start
            text = "%02d:%02d" % (minutes // 60, minutes % 60)
            extents = context.text_extents(text)
            context.set_source_rgba(color.red, color.green, color.blue, 0.6)
            textY = max(y, extents.height / 2 + 1)  # keep the first label visible
            context.move_to(width - 10 - extents.width, textY + extents.height / 2)
            context.show_text(text)
            context.set_source_rgba(color.red, color.green, color.blue, 0.3)
            context.rectangle(width - 7, y - 0.5, 7, 1)
            context.fill()

        slots = self.gridFormat["timeGridSlots"]
        i=0
        for slot in slots:
            start = self.timeToMinutes(slot["duration"]["start"])
            end = self.timeToMinutes(slot["duration"]["end"])
            drawLabel(start)
            i+=1
            drawEnd = i==len(slots)
            if not drawEnd:
                nextStart = self.timeToMinutes(slots[i]["duration"]["start"])
                drawEnd = nextStart != end
            if drawEnd:
                drawLabel(end)

    def displayData(self, data):
        dontClose = False
        if data is None:
            return
        table, self.gridFormat = data

        showCancelled = self.settings.get_boolean("show-cancelled-lessons")
        for i, day in enumerate(table):
            if not showCancelled:
                # hide cancelled lessons that would sit next to a lesson
                # taking place instead, their info stays in the popup
                day = [
                    lesson
                    for lesson in day
                    if lesson["status"] != "CANCELLED"
                    or not any(
                        other["status"] != "CANCELLED"
                        and other["start"] < lesson["end"]
                        and lesson["start"] < other["end"]
                        for other in day
                    )
                ]
                table[i] = day
            self.shared.session.layoutDay(day, ignore_exam_breaks = self.settings.get_boolean("ignore-exam-breaks"))

        atLeastOneLesson = False

        self.header_button.set_label(self.startdate.strftime(_("Week %W")))
        self.window.updateOfflineBanners()

        self.start = self.timeToMinutes(self.gridFormat["duration"]["start"])
        self.end = self.timeToMinutes(self.gridFormat["duration"]["end"])

        for day in table:
            for lesson in day:
                atLeastOneLesson = True

        self.showAxis = self.settings.get_boolean("show-time-axis")
        if not atLeastOneLesson:
            self.start = 0
            self.showAxis = False

        for lesson in self.lessons:
            lesson[0].remove(lesson[1])
            lesson[1].markAsHidden()
        self.lessons.clear()

        for column in self.columns:
            self.timetable.remove(column)
        self.columns.clear()

        for overlay in self.overlays:
            overlay[0].remove_overlay(overlay[1])
        self.overlays.clear()

        if self.showAxis:
            axisColumn = Gtk.Box()
            axisColumn.set_orientation(Gtk.Orientation.VERTICAL)
            axisHeader = Gtk.Label(label=" ")
            axisHeader.add_css_class("day")
            axisColumn.append(axisHeader)
            axis = Gtk.DrawingArea()
            axis.set_content_width(44)
            axis.set_content_height(self.end - self.start)
            axis.set_draw_func(self.drawTimeAxis)
            axisColumn.append(axis)
            self.timetable.append(axisColumn)
            self.columns.append(axisColumn)

        date = self.startdate
        past = True
        now = getDateTime()
        for day in table:
            column = Gtk.Overlay()
            self.timetable.append(column)
            self.columns.append(column)

            dayBox = Gtk.Box()
            dayBox.set_orientation(Gtk.Orientation.VERTICAL)
            dayBox.set_hexpand(True)
            dayBox.set_halign(Gtk.Align.FILL)
            dayBox.set_spacing(0)
            column.set_child(dayBox)

            dateLabel = Gtk.Label()
            # Translators: date format in the timetable
            dateLabel.set_label(date.strftime(_("%m/%d/%y")))
            dayBox.append(dateLabel)
            dateLabel.add_css_class("day")
            if date.date() == now.date():
                dateLabel.add_css_class("today")
                if atLeastOneLesson or self.showAxis:
                    timeMarker = Gtk.DrawingArea()
                    timeMarker.set_hexpand(True)
                    timeMarker.set_vexpand(True)
                    timeMarker.set_draw_func(self.drawTimeMarker, dateLabel, False)
                    timeMarker.set_can_target(False)
                    column.add_overlay(timeMarker)
                    self.overlays.append((column, timeMarker))

                    timeMarkerWeek = Gtk.DrawingArea()
                    timeMarkerWeek.set_hexpand(True)
                    timeMarkerWeek.set_vexpand(True)
                    timeMarkerWeek.set_draw_func(self.drawTimeMarker, dateLabel, True)
                    timeMarkerWeek.set_can_target(False)
                    self.overlays.append((self.overlay, timeMarkerWeek))
                    self.overlay.add_overlay(timeMarkerWeek)

            if day == []:
                holiday = self.shared.session.getHoliday(date)
                obj = Holiday(holiday["name"])
                dayBox.append(obj)
            else:
                layout = DayLayout(self.start, self.end)
                dayBox.append(layout)
                for lesson in day:
                    block = Lesson(lesson, self, now)
                    layout.add(block)
                    self.lessons.append((layout, block, lesson))
                    if lesson == self.information_window.lesson:
                        dontClose = True

            date += datetime.timedelta(days=1)

        if not dontClose and self.information_window.lesson is not None:
            self.information_window.close()

moduleInfo = {
    "staticPages": [
        {
            "group": _("Timetables"),
            "widget": Timetable(),
            "name": "timetable",
            "title": _("My timetable"),
            "icon": "month-symbolic",
        }
    ]
}
