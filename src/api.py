import requests
import os
import json
import time
import datetime
import copy
import pyotp
import binascii
from pathlib import Path
from hashlib import md5

version = "5.0.0"
releaseNotes = '	<p>This release renames the app to Untix and adds support for loging in using a QR-Code</p>\n	<p>More changes include</p>\n        <ul>\n          <li>added a setting to merge long exams despite of breaks</li>\n          <li>added support for attachments in messages</li>\n          <li>added buttons to view news of older days</li>\n          <li>fixed own homeworks not showing up in timetable</li>\n          <li>make links in messages clickable</li>\n          <li>show the subject display name like the mobile app</li>\n          <li>renamed from "Timetable" to "Untix"</li>\n	  <li>updated to GNOME 51</li>\n        </ul>\n'
id = "page.codeberg.ostfriese4.Untis"
useragent = id + " " + version

headers = {"User-Agent": useragent, "Accept": "application/json"}

offline = False
lastOnline = None

fakeTime = datetime.datetime.strptime("26.09.01 10:31:03", "%y.%m.%d %H:%M:%S")

def getDateTime():
    #return fakeTime
    return datetime.datetime.now()
def getDate():
    return getDateTime().date()


def _login(credentials):
    global offline, lastOnline
    s = requests.Session()
    s.headers.update(headers)
    s.headers.update({"Referer": credentials["server"] + "/"})

    try:
        match credentials["type"]:
            case "password":
                form_data = {
                    "school": credentials["school"],
                    "j_username": credentials["user"],
                    "j_password": credentials["password"],
                }

                url = credentials["server"] + "/WebUntis/j_spring_security_check"
                response = s.post(url, data=form_data)
                json = response.json()

                ok = json["state"] == "SUCCESS"

            case "token":
                totp = pyotp.TOTP(credentials["password"], interval=30)
                token = totp.now()
                currentTime = int(datetime.datetime.now().timestamp() * 1000)

                url = credentials["server"] + "/WebUntis/jsonrpc_intern.do"
                data = {
                    "id":     "login" + credentials["profile"],
                    "method": "getUserData2017",
                    "jsonrpc": "2.0",
                    "params": [{
                                "auth": {
                                        "clientTime": currentTime,
                                        "user":       credentials["user"],
                                        "otp":        token
                                }
                    }]
                }

                params = {
                    "m":      "getUserData2017",
                    "school": credentials["school"],
                    "v":      "i2.2"
                }

                response = s.post(url, json=data)
                json = response.json()

                ok = not "error" in json

            case "no":
                return s


        offline = False
        lastOnline = getDateTime()
        if response.status_code == 200 and ok:
            token = s.get(credentials["server"] + "/WebUntis/api/token/new").text
            s.headers.update({"Authorization": "Bearer " + token})
            print("logged in successfully")
            return s
        else:
            print(response)
    except requests.exceptions.ConnectionError:
        offline = True
        print("offline, could not log in")
    except requests.exceptions.JSONDecodeError:
        offline = True
        print("invalid answer, could not log in")
    except requests.exceptions.InvalidURL:
        print("invalid url, could not log in")
    except binascii.Error:
        print("invalid token, could not log in")
    except Exception:
        print("could not log in because of an unknown error")


# from https://github.com/l-koehler/untis-py (api.py)
def searchSchool(query):
    # return: [display name, server URL]

    if query == "":
        return ["too many results"]

    baseurl = "https://schoolsearch.webuntis.com/schoolquery2"
    json = {
        "id": useragent,
        "jsonrpc": "2.0",
        "method": "searchSchool",
        "params": [{"search": f"{query}"}],
    }
    try:
        data = requests.post(url=baseurl, json=json).json()
        if "error" in data:
            return [data["error"]["message"]]
        return data["result"]["schools"]
    except requests.exceptions.ConnectionError:
        return ["offline"]

def parseLandingPage(server, path = "/WebUntis", key = "config: ", session = requests):
    landingPage = session.get(server + path).text
    pos = landingPage.find(key) + len(key)
    end = pos
    score = 0
    while score != 0 or end == pos:
        i = landingPage[end]
        if i == "{":
            score += 1
        elif i == "}":
            score -= 1
        end += 1
    code = landingPage[pos:end]
    return json.loads(code)


def testCredentials(credentials):
    return _login(credentials) is not None or offline


class session:
    def __init__(self, credentials):
        self.session = _login(credentials)
        self.credentials = credentials
        self.server = credentials["server"]

        self.name = credentials["school"] + credentials["user"] + credentials["server"] + credentials["profile"]
        self.name = md5(self.name.encode()).hexdigest()
        self.CACHEDIR = (
            os.environ.get("XDG_CACHE_HOME", ".untis/cache") + "/untis/" + self.name + "/"
        )
        self.cache = {}

        self._readCacheIndex()

        try:
            with open(
                os.environ.get("XDG_CACHE_HOME", ".untis/cache") + "/untis-colors.json"
            ) as file:
                self.colors = json.load(file)
        except:
            self.colors = {}

    def ensureLogin(self):
        if self.session is None:
            print("not logged in yet")
            self.session = _login(self.credentials)

    def getOffline(self):
        return offline

    def getLastOnline(self):
        global lastOnline
        if lastOnline is None:
            last = None
            for item in self.cacheIndex:
                if "request" in item:
                    if last is None:
                        last = self.cacheIndex[item]
                    elif self.cacheIndex[item] > last:
                        last = self.cacheIndex[item]
            if last is not None:
                lastOnline = datetime.datetime.fromtimestamp(last)
        return lastOnline

    def scanFiles(self, root, rootName):
        out = []
        for name in os.listdir(root):
            path = root + name
            if os.path.isfile(path):
                out.append(rootName + "/" + name)
            else:
                out += self.scanFiles(path + "/", rootName + "/" + name)
        return out

    def repairCacheIndex(self):
        print("repairing cache index...")
        self.cacheIndex = {"last-refresh": time.time()}
        for file in self.scanFiles(self.CACHEDIR, ""):
            self.cacheIndex[file] = time.time() - 3600
            print("found", file)
        self._saveCacheIndex()

    def _readCacheIndex(self):
        path = self.CACHEDIR + "index.json"
        if os.path.exists(path):
            try:
                with open(path) as file:
                    self.cacheIndex = json.load(file)
            except json.decoder.JSONDecodeError:
                self.repairCacheIndex()
        else:
            self.cacheIndex = {"last-refresh": time.time()}

    def _saveCacheIndex(self):
        path = self.CACHEDIR + "index.json"
        with open(path, "w") as file:
            json.dump(self.cacheIndex, file)

    def refresh(self):
        self.cacheIndex["last-refresh"] = time.time()
        self._saveCacheIndex()

    def _writeToRamCache(self, object, content):
        if object in self.cache:
            return
        self.cache[object] = content
        if len(self.cache) > 50:
            oldest = list(self.cache.keys())[0]
            del self.cache[oldest]

    def _readFromCache(self, object):
        if object in self.cache:
            item = self.cache.pop(object)
            self.cache[object] = copy.deepcopy(item)
            return item
        try:
            with open(self.CACHEDIR + object) as file:
                data = json.load(file)
                self._writeToRamCache(object, copy.deepcopy(data))
                return data
        except FileNotFoundError:
            return

    def _writeToCache(self, object, content):
        content = copy.deepcopy(content)
        path = self.CACHEDIR + object
        Path(path).parent.mkdir(exist_ok=True, parents=True)
        with open(path, "w") as file:
            json.dump(content, file)
            self.cacheIndex[object] = time.time()
            self._saveCacheIndex()
        self._writeToRamCache(object, content)

    def _useCache(self, object, maxage=3600):
        if object in self.cacheIndex:
            if self.cacheIndex[object] < self.cacheIndex["last-refresh"]:
                return False
            else:
                return self.cacheIndex[object] + maxage >= time.time()
        return False

    def _RPCRequest(self, method, params, mode="normal", maxage=3600):
        global offline, lastOnline
        orig = mode

        hashed = method + str(params)
        hashed = "rpc-requests/" + md5(hashed.encode()).hexdigest()

        payload = {
            "id": hashed,
            "method": method,
            "params": params,
            "jsonrpc": "2.0"
        }

        if self.session is None:
            self.ensureLogin()
            if self.session is None:
                mode = "cache"
        if mode == "normal":
            if self._useCache(hashed, maxage=maxage):
                mode = "cache"
            else:
                mode = "online"

        if mode == "online":
            try:
                response = self.session.post(self.server + "/WebUntis/jsonrpc.do", json = payload)
                data = response.json()
                offline = False
                lastOnline = getDateTime()
                if not "result" in data:  # e.g. "no right for getTeachers()"
                    print("ERROR: RPC:", method, params, data.get("error"))
                    mode = "cache"
                elif "errorCode" in data["result"]:
                    print("ERROR: RPC:", method, params)
                    mode = "cache"
                else:
                    data = data["result"]
                    self._writeToCache(hashed, data)
                    return data
            except requests.exceptions.ConnectionError:
                mode = "cache"
                offline = True
            except requests.exceptions.InvalidURL:
                mode = "cache"
            except Exception:
                raise
                mode = "cache"

        if mode == "cache":
            try:
                return self._readFromCache(hashed)
            except json.decoder.JSONDecodeError:
                if orig != "online":
                    print("repairing cache", path)
                    return self._getRequest(path, "online")

    def getAllTeachers(self, mode = "normal", maxage = 86400):
        name = "data/allTeachers"
        match mode:
            case "cache":
                cache = True
            case "normal":
                cache = self._useCache(name, maxage)
            case "online":
                cache = False
        if not cache:
            data = self._RPCRequest(method = "getTeachers", params = {}, mode = mode, maxage = maxage)
            if data is not None:
                out = {}
                for teacher in data:
                    out[teacher["name"]] = teacher
                self._writeToCache(name, out)
                return out
        return self._readFromCache(name) or {}  # no teacher data available

    def getTeacherById(self, id, mode = "normal"):
        for teacher in self.getAllTeachers(mode = mode):
            if teacher["id"] == id:
                return teacher

    def _getRequest(self, path, mode="normal", maxage=3600, referer = None):
        global offline, lastOnline
        orig = mode
        hashed = "requests/" + md5(path.encode()).hexdigest()
        if self.session is None:
            self.ensureLogin()
            if self.session is None:
                mode = "cache"
        if mode == "normal":
            if self._useCache(hashed, maxage=maxage):
                mode = "cache"
            else:
                mode = "online"

        if mode == "online":
            try:
                response = self.session.get(self.server + path)
                data = response.json()
                offline = False
                lastOnline = getDateTime()
                if "errorCode" in data or "errorMessage" in data:
                    print("ERROR: PATH:", self.server + path, data)
                    if "errorMessage" in data:
                        if data["errorMessage"] == "Unauthorized":
                            print("relogin")
                            self.session = _login(self.credentials)
                    mode = "cache"
                else:
                    self._writeToCache(hashed, data)
                    return data
            except requests.exceptions.ConnectionError:
                mode = "cache"
                offline = True
            except requests.exceptions.InvalidURL:
                mode = "cache"
            except Exception:
                raise
                mode = "cache"

        if mode == "cache":
            try:
                return self._readFromCache(hashed)
            except json.decoder.JSONDecodeError:
                if orig != "online":
                    print("repairing cache", path)
                    return self._getRequest(path, "online")

    def getNewsOfDay(self, day=None):
        if day is None:
            day = getDate()
        path = "/WebUntis/api/public/news/newsWidgetData?date=" + day.strftime("%Y%m%d")
        data = self._getRequest(path)
        try:
            data = data["data"]["messagesOfDay"]
        except TypeError:
            data = []
        return data

    def getTimetable(self, resourceType, resourceId, start = None, end = None, mode = "normal"):
        year = self.getCurrentSchoolYear()
        gridFormat = None

        s_start = datetime.datetime.strptime(year["dateRange"]["start"], "%Y-%m-%d")
        s_end = datetime.datetime.strptime(year["dateRange"]["end"], "%Y-%m-%d")
        if start is None:
            start = s_start
        if end is None:
            end = s_end

        data = []
        start = start.date()
        end = end.date()
        day = start
        while day <= end:
            name = "days-" + resourceType + str(resourceId) + "/" + day.strftime("%Y-%m-%d")
            cache = mode == "cache"
            if mode == "normal":
                cache = self._useCache(name)

            dayData = []
            if cache:
                try:
                    dayData = self._readFromCache(name)
                    if dayData is None:
                        dayData = []
                except:
                    pass
            if not cache:
                path = (
                    "/WebUntis/api/rest/view/v1/timetable/entries?start="
                    + day.strftime("%Y-%m-%d")
                    + "&end="
                    + day.strftime("%Y-%m-%d")
                    + "&format=2&resourceType="
                    + resourceType
                    + "&resources="
                    + str(resourceId)
                    + "&periodTypes=&timetableType=MY_TIMETABLE&layout=START_TIME"
                )
                fetched = self._getRequest(path, mode)
                gridFormat = fetched["format"]
                dayData = self.analyzeTimetable(fetched["days"], resourceType, resourceId, mode)[0]
                self._writeToCache(name, dayData)
            data.append(dayData)
            day += datetime.timedelta(days=1)

        return data, gridFormat

    def getOwnTimetableId(self):
        for timetable in self.getAvailableTimetables():
            if self.isOwnTimetable(timetable):
                return timetable
        print("could not get own timetable")

    def isOwnTimetable(self, timetable):
        roles = self.getOwnRoles()
        id = self.getOwnId()
        return timetable["id"] == id and timetable["type"] in roles

    def getAvailableTimetables(self):
        if not self._useCache("availableTimetables"):
            result = []

            students = self.getAvailableTiemtablesOfType("STUDENT")
            if students:
                for student in students["students"]:
                    result.append({
                        "id": student["student"]["id"],
                        "type": "STUDENT",
                        "name": student["student"]["displayName"]
                    })

            teachers = self.getAvailableTiemtablesOfType("TEACHER")
            if teachers:
                for teacher in teachers["teachers"]:
                    result.append({
                        "id": teacher["teacher"]["id"],
                        "type": "TEACHER",
                        "name": teacher["teacher"]["displayName"]
                    })

            rooms = self.getAvailableTiemtablesOfType("ROOM")
            if rooms:
                for room in rooms["rooms"]:
                    result.append({
                        "id": room["room"]["id"],
                        "type": "ROOM",
                        "name": room["room"]["displayName"]
                    })

            classes = self.getAvailableTiemtablesOfType("CLASS")
            if classes:
                for cls in classes["classes"]:
                    name = cls["class"]["displayName"]
                    if cls["classTeacher1"]:
                        name += " (" + cls["classTeacher1"]["displayName"] + ")"

                    result.append({
                        "id": cls["class"]["id"],
                        "type": "CLASS",
                        "name": name
                    })

            for timetable in result:
                if self.isOwnTimetable(timetable):
                    timetable["name"] = _("My timetable")

            self._writeToCache("availableTimetables", result)
            return result
        return self._readFromCache("availableTimetables")

    def getAvailableTiemtablesOfType(self, t):
        year = self.getCurrentSchoolYear()
        start = year["dateRange"]["start"]
        end = year["dateRange"]["end"]

        path = (
            "/WebUntis/api/rest/view/v1/timetable/filter?resourceType="
            + t
            + "&timetableType=STANDARD&start="
            + start
            + "&end="
            + end
        )

        data = self._getRequest(path)

        return data

    def createList(self, data, key, long, integrate=None):
        text = ""
        i = 0
        for item in data:
            text += item[key]
            if integrate is not None:
                text += " (" + item[integrate] + ")"
            if i == len(data) - 1:
                return text
            elif long and i == len(data) - 2:
                text += " " + _("and") + " "
            else:
                text += ", "
            i += 1
        if long:
            return _("Unknown")
        else:
            return "???"

    def getColor(self, subject):
        if subject in self.colors:
            return self.colors[subject]
        colors = [
            "green",
            "red",
            "blue",
            "orange",
            "purple",
            "teal",
            "yellow",
            "slate",
            "pink",
        ]
        color = colors[0]
        count = 0
        for key in self.colors:
            if self.colors[key] == color:
                count += 1
        for c in colors:
            n = 0
            for key in self.colors:
                if self.colors[key] == c:
                    n += 1
            if n < count:
                count = n
                color = c
        self.colors[subject] = color

        with open(
            os.environ.get("XDG_CACHE_HOME", ".untis") + "/untis-colors.json", "w"
        ) as file:
            json.dump(self.colors, file)

        return color

    def getDisplayNames(self, gridEntries):
        # the grid entries carry the subject names configured in WebUntis (e.g.
        # an alternate name), search all positions as their layout can change
        names = {}
        for entry in gridEntries:
            for key, labels in entry.items():
                if not key.startswith("position") or not labels:
                    continue
                for label in labels:
                    for state in (label.get("current"), label.get("removed")):
                        if state and state.get("type") == "SUBJECT":
                            names[state.get("shortName")] = state.get("displayName")
        return names

    def analyzeLesson(self, lesson, displayNames=None):
        rooms = lesson["rooms"]
        old = rooms.copy()
        change = False
        for room in rooms.copy():
            if room["status"] == "REMOVED":
                change = True
                rooms.remove(room)
                room["status"] = "LATER_REMOVED"
            else:
                old.remove(room)
        if change and not "original" in lesson:
            lesson["original"] = lesson.copy()
            lesson["original"]["rooms"] = old

        start = datetime.datetime.strptime(lesson["startDateTime"], "%Y-%m-%dT%H:%M:%S")
        end = datetime.datetime.strptime(lesson["endDateTime"], "%Y-%m-%dT%H:%M:%S")
        lesson["start"] = start.hour * 60 + start.minute
        lesson["end"] = end.hour * 60 + end.minute
        lesson["duration"] = lesson["end"] - lesson["start"]
        lesson["gridStatus"] = lesson.get("status")
        lesson["gridType"] = lesson.get("type")

        for teacher in lesson["teachers"]:
            short = teacher["shortName"]
            long = self.getFullTeacherNameByShortName(short)
            if short != long:
                teacher["longName"] = long

        if lesson["subject"] == None:
            if lesson.get("gridType") == "EVENT" or lesson.get("type") == "EVENT":
                name = lesson.get("lessonInfo") or _("Event")
                if "lessonInfo" in lesson:
                    lesson["lessonInfo"] = None
                lesson["subject"] = {"shortName": _("Event"), "longName": name}
            else:
                lesson["subject"] = {"shortName": "???", "longName": _("Unknown")}

        # shown on the lesson block like the mobile app does, the short name
        # stays untouched as homeworks are matched by it
        subject = lesson["subject"]
        subject["displayName"] = (displayNames or {}).get(subject["shortName"]) or subject["shortName"]

        lesson["teachers-short"] = self.createList(
            lesson["teachers"], "shortName", False
        )
        lesson["room"] = self.createList(rooms, "shortName", False)

        lesson["teachers-long"] = self.createList(
            lesson["teachers"], "longName", True, integrate="shortName"
        )
        lesson["room-info"] = self.createList(rooms, "longName", True)

        if lesson.get("color"):
            lesson["color"] = "#" + lesson["color"].lstrip("#")
        else:
            lesson["color"] = self.getColor(lesson["subject"]["shortName"])

        if "original" in lesson:
            lesson["original"] = self.analyzeLesson(lesson["original"], displayNames)

        return lesson

    def analyzeTimetable(self, data, resourceType, resourceId, mode="normal"):
        timetable = []
        for day in data:
            date = day["date"]
            lessons = []
            timetable.append(lessons)
            start = date + "T00:00"
            end = date + "T23:59"

            details = self.getLessonDetails(
                start,
                end,
                resourceType,
                resourceId,
                mode,
            )

            if details is None:
                print("empty lesson")
                continue

            displayNames = self.getDisplayNames(day["gridEntries"])
            for lesson in details:
                lessons.append(self.analyzeLesson(lesson, displayNames))
        return timetable

    def lessonsAreEqual(self, l1, l2):
        keys = [
            "room",
            "room-info",
            "status",
            "subject",
            "teachers-long",
            "teachers-short",
        ]
        for key in keys:
            if l1[key] != l2[key]:
                return False
        return True

    def mergeDay(self, lessons, ignore_exam_breaks = False):
        # combine consecutive parts of the same lesson into one block, other
        # (e.g. cancelled) lessons can sit between their grid entries

        old = lessons.copy()
        for lesson in old:
            previous = None
            i = lessons.index(lesson)

            while i>=0:
                item = lessons[i]
                ok = item["end"] == lesson["start"]
                if ignore_exam_breaks:
                    if item["gridType"] == "EXAM" and lesson["gridType"] == "EXAM":
                        ok = item["end"] <= lesson["start"]
                if ok:
                    ok = self.lessonsAreEqual(lesson, item)
                if ok:
                    item["end"] = lesson["end"]
                    item["duration"] = item["end"] - item["start"]
                    lessons.remove(lesson)
                    break
                i -= 1

    def layoutDay(self, lessons, ignore_exam_breaks = False):
        # place overlapping lessons in columns next to each other, computed
        # from the merged lessons so that double periods stay combined
        cluster = []  # (lesson, column) of the current overlap group
        ends = []  # end of the last lesson per column

        lessons.sort(key=lambda l: (l["start"], l["end"]))
        self.mergeDay(lessons, ignore_exam_breaks = ignore_exam_breaks)

        def apply():
            width = 1000 // max(len(ends), 1)
            for lesson, column in cluster:
                lesson["layoutStart"] = column * width
                lesson["layoutWidth"] = width

        for lesson in lessons:
            if ends and all(end <= lesson["start"] for end in ends):
                apply()
                cluster = []
                ends = []
            for column, end in enumerate(ends):
                if end <= lesson["start"]:
                    ends[column] = lesson["end"]
                    break
            else:
                column = len(ends)
                ends.append(lesson["end"])
            cluster.append((lesson, column))
        apply()

    def getOwnId(self):
        return self.getGeneralData()["user"]["person"]["id"]

    def getMyData(self):
        path = "/WebUntis/api/rest/view/v1/timetable/filter?resourceType=STUDENT"
        data = self._getRequest(path)
        print(data)

    def getSchoolYears(self):
        path = "/WebUntis/api/rest/view/v1/schoolyears"
        data = self._getRequest(path)
        return data

    def getGeneralData(self):
        path = "/WebUntis/api/rest/view/v1/app/data"
        data = self._getRequest(path)
        return data

    def getHolidays(self):
        return self.getGeneralData()["holidays"]

    def getHoliday(self, day):
        for holiday in self.getHolidays():
            start = datetime.datetime.strptime(holiday["start"], "%Y-%m-%dT%H:%M:%S")
            end = datetime.datetime.strptime(holiday["end"], "%Y-%m-%dT%H:%M:%S")
            if start <= day <= end:
                holiday["start"] = start
                holiday["end"] = end
                return holiday
        return {"start": day, "end": day, "name": _("No data")}

    def getCurrentSchoolYear(self):
        now = getDateTime()
        years = self.getSchoolYears()
        for year in years:
            start = datetime.datetime.strptime(year["dateRange"]["start"], "%Y-%m-%d")
            end = datetime.datetime.strptime(year["dateRange"]["end"], "%Y-%m-%d")
            if start < now < end:
                return year
        return years[-1]

    def getAbsences(self, start=None, end=None):
        year = self.getCurrentSchoolYear()
        if start is None:
            start = datetime.datetime.strptime(year["dateRange"]["start"], "%Y-%m-%d")
        if end is None:
            end = datetime.datetime.strptime(year["dateRange"]["end"], "%Y-%m-%d")

        path = (
            "/WebUntis/api/classreg/absences/students?startDate="
            + start.strftime("%Y%m%d")
            + "&endDate="
            + end.strftime("%Y%m%d")
            + "&studentId="
            + str(self.getOwnId())
            + "&excuseStatusId=-1"
        )
        data = self._getRequest(path)
        return data["data"]["absences"]

    def getMessages(self):
        path = "/WebUntis/api/rest/view/v1/messages"
        data = self._getRequest(path)
        return data["incomingMessages"]

    def getMessageById(self, id):
        path = "/WebUntis/api/rest/view/v1/messages/" + str(id)
        data = self._getRequest(path)

        if data is None:
            all = self.getMessages()
            for message in all:
                if message["id"] == id:
                    message["content"] = message["contentPreview"]
                    return message
        else:
            data["sender"]["displayName"] = self.getFullTeacherNameByShortName(data["sender"]["displayName"])
            return data

    def getFullTeacherNameByShortName(self, short):
        teachers = self.getAllTeachers()
        if short in teachers:
            teacher = teachers[short]
            return teacher["foreName"] + " " +  teacher["longName"]
        return short

    def getLessonDetails(self, start, end, resourceType, resourceId, mode="normal"):
        resourceTypes = ["CLASS", "TEACHER", "SUBJECT", "ROOM", "STUDENT"]
        resourceType = str(resourceTypes.index(resourceType) + 1)
        path = (
            "/WebUntis/api/rest/view/v2/calendar-entry/detail?elementId="
            + str(resourceId)
            + "&elementType="
            + resourceType
            + "&endDateTime="
            + end
            + "&homeworkOption=DUE&startDateTime="
            + start
        )

        data = self._getRequest(path, mode)
        data = data["calendarEntries"]

        if data == []:
            return

        takingPlace = []
        cancelled = []
        for lesson in data:
            if lesson["status"] == "CANCELLED":
                cancelled.append(lesson)
            else:
                takingPlace.append(lesson)

        if len(takingPlace) == 1 and len(cancelled) == 1:
            lesson = takingPlace[0]
            lesson["original"] = cancelled[0]

        return takingPlace + cancelled

    def getTenant(self):
        return self.getGeneralData()["tenant"]

    def getAttachmentStorageUrl(self, id):
        path = (
            "/WebUntis/api/rest/view/v1/messages/"
            + id
            + "/attachmentstorageurl"
        )
        return self._getRequest(path, maxage = 5)

    def getAllRooms(self):
        year = self.getCurrentSchoolYear()
        start = datetime.datetime.strptime(year["dateRange"]["start"], "%Y-%m-%d")
        end = datetime.datetime.strptime(year["dateRange"]["end"], "%Y-%m-%d")
        path = (
            "/WebUntis/api/rest/view/v1/calendar-entry/rooms/form?endDateTime="
            + end.strftime("%Y-%m-%dT%H:%M:%S")
            + "&startDateTime="
            + start.strftime("%Y-%m-%dT%H:%M:%S")
        )
        data = self._getRequest(path)
        return data

    def getMenu(self):
        path = "/WebUntis/api/rest/view/v1/app/platform-application/menus"
        data = self._getRequest(path)
        return data or []

    def getOwnUser(self):
        return self.getGeneralData()["user"]

    def getOwnRoles(self):
        return self.getOwnUser()["roles"]

    def getPermissions(self):
        views = self.getGeneralData()["user"]["permissions"]["views"]
        general = self.getGeneralData()["permissions"]
        return {
            "views": views,
            "general": general,
        }

    def getUnreadMessagesCount(self):
        path = "/WebUntis/api/rest/view/v1/messages/status"
        return self._getRequest(path)["unreadMessagesCount"]

    def getAttachments(self, item):
        out = []
        for attachment in item["storageAttachments"]:
            out.append({
                "name": attachment["name"],
                "id": attachment["id"],
                "type": "storageAttachment"
            })
        return out

    def getHomeworks(self, start=None, end=None):
        year = self.getCurrentSchoolYear()
        if start is None:
            start = datetime.datetime.strptime(year["dateRange"]["start"], "%Y-%m-%d")
        if end is None:
            end = datetime.datetime.strptime(year["dateRange"]["end"], "%Y-%m-%d")

        path = (
            "/WebUntis/api/homeworks/lessons?startDate="
            + start.strftime("%Y%m%d")
            + "&endDate="
            + end.strftime("%Y%m%d")
        )
        data = self._getRequest(path)
        if data is None or not "data" in data:  # e.g. no right for homeworks
            print("ERROR: homeworks:", data)
            return {"lessons": [], "homeworks": []}
        return data["data"]

    def getTimeGrid(self, id=None, mode = "normal"):
        path = "/WebUntis/api/rest/view/v1/timetable/grid?timetableType=MY_TIMETABLE"
        data = self._getRequest(path, mode=mode)

        if id is None:
            return data["formatDefinitions"][0]
        else:
            for grid in data["formatDefinitions"]:
                if grid["id"] == id:
                    return grid
