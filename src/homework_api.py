import json
import datetime
import os
from .shared import shared

DATAPATH = os.environ.get("XDG_DATA_HOME", ".untis")

profile = None
shared.homeworkUpdatedActions = []


def loadOwnData(profile):
    path = DATAPATH + profile + ".json"
    if os.path.exists(path):
        with open(path) as file:
            return json.load(file)
    else:
        return {}

ownData = {}
def getOwnData():
    global ownData
    global profile
    if profile != shared.profiles["default-profile"]:
        profile = shared.profiles["default-profile"]
        ownData = loadOwnData(profile)
    return ownData

def writeOwnData(data):
    with open(DATAPATH + profile + ".json", "w") as file:
        json.dump(data, file, indent=4)

def getLocalHomeworks(start=None, end=None):
    if start is not None:
        start = int(start.strftime("%Y%m%d"))
    if end is not None:
        end = int(end.strftime("%Y%m%d"))

    result = []
    for id in (ownData := getOwnData()):
        if id.startswith("own"):
            item = ownData[id]

            if start is not None and item["dueDate"] <= start:
                continue
            if end is not None and item["dueDate"] >= end:
                continue

            result.append(item)

    return result

def getRemoteHomeworks(start=None, end=None, mode="normal", orig=False):
    result = []
    for homework in shared.session.getOwnHomeworks(start, end, mode = mode):
        if orig:
            result.append(homework)
        else:
            result.append(applyChanges(homework))
    return result

def mergeHomeworks(lists):
    def key(item):
        return item["dueDate"]
    result = []
    for homeworks in lists:
        result += homeworks
    result.sort(key = key)
    return result

def getAllHomeworks(start = None, end = None, mode = "normal", orig = False):
    return mergeHomeworks([
        getLocalHomeworks(start, end),
        getRemoteHomeworks(start, end, mode, orig),
    ])

def applyChanges(item):
    ownData = getOwnData()

    if (id := str(item["id"])) in ownData:
        item["oldKeys"] = {}
        for key in (changes := ownData[id]):
            item["oldKeys"][key] = item[key]
            item[key] = changes[key]
    return item

def setValue(id, key, value):
    ownData = getOwnData()

    id = str(id)
    if not id in ownData:
        ownData[id] = {"id": id}
    ownData[id][key] = value
    writeOwnData(ownData)


def getById(id, orig=False):
    id = str(id)
    for item in getAllHomeworks(orig = orig):
        if str(item["id"]) == id:
            return item


def delete(id):
    ownData = getOwnData()

    id = str(id)
    if id in ownData:
        del ownData[id]
        writeOwnData(ownData)


def getNewId():
    ownData = getOwnData()

    i = 0
    while "own" + str(i) in ownData:
        i += 1
    return "own" + str(i)


def getChanges(id):
    ownData = getOwnData()

    id = str(id)
    if id.startswith("own"):
        return {}
    elif id in ownData:
        orig = getById(id, True)
        out = {}
        for key in ownData[id]:
            if key != "id":
                old = orig[key]
                new = ownData[id][key]
                if old != new:
                    out[key] = (old, new)
        return out
    return {}
