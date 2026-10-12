import datetime
from ..infrastructure import store
from ..infrastructure.config import SCHEDULE

def load_schedule():
    data = store.read_json(SCHEDULE, {})
    sleep = data.get("sleep", {})
    return {"sleep": {"from": sleep.get("from", ""), "to": sleep.get("to", "")},
            "routine": data.get("routine", "")}

def parse_time(value):
    return datetime.time.fromisoformat(value)

def sleep_state(now=None):
    s = load_schedule()["sleep"]
    if not s["from"] or not s["to"]:
        return "сон не задан"
    try:
        start, end = parse_time(s["from"]), parse_time(s["to"])
    except ValueError:
        return "сон задан неверно"
    t = (now or datetime.datetime.now()).time()
    if start <= end:
        asleep = start <= t < end
    else:
        asleep = t >= start or t < end
    return "сейчас время сна" if asleep else "сейчас время бодрствования"

def schedule_text():
    s = load_schedule()
    sleep = (f"сон с {s['sleep']['from']} до {s['sleep']['to']}"
             if s["sleep"]["from"] and s["sleep"]["to"] else "сон не задан")
    routine = s["routine"] or "рутина не задана"
    return f"{sleep} ({sleep_state()}). Рутина: {routine}"

def set_schedule(sleep_from="", sleep_to="", routine=""):
    data = load_schedule()
    try:
        if sleep_from:
            parse_time(sleep_from)
            data["sleep"]["from"] = sleep_from
        if sleep_to:
            parse_time(sleep_to)
            data["sleep"]["to"] = sleep_to
    except ValueError:
        return "Время должно быть в формате ЧЧ:ММ, например 23:30"
    if routine:
        data["routine"] = routine
    store.write_json(SCHEDULE, data)
    return f"Расписание сохранено: {schedule_text()}"