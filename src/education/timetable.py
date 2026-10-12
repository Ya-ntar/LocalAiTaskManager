import os, json, datetime
from ..infrastructure import store

PATH = os.path.join(store.USER_DATA_DIR, "timetable.json")
SOURCES = ("есть", "хочу")
KINDS = ("обязательное", "дополнительное")
MODES = ("присутствие", "подключиться", "работа")
PLACES = ("офлайн", "онлайн")
DAY_NAMES = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
SHORT_DAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
DEFAULT_DURATION = 90
DEFAULT_COMMUTE = 60
DAY_WINDOW = ("08:00", "23:00")

def _load():
    return store.read_json(PATH, [])

def _save(items):
    store.write_json(PATH, items)

def _next_id(items):
    ids = [i.get("id") for i in items
           if isinstance(i, dict) and isinstance(i.get("id"), int)
           and not isinstance(i.get("id"), bool)]
    return max(ids + [0]) + 1

def _mins(hhmm):
    if not isinstance(hhmm, str) or len(hhmm) != 5 or hhmm[2] != ":":
        raise ValueError("время в формате HH:MM")
    t = datetime.time.fromisoformat(hhmm)
    return t.hour * 60 + t.minute

def _fmt(minutes):
    minutes = max(0, min(minutes, 23 * 60 + 59))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

def _span(item):
    start = _mins(item["start"])
    end = _mins(item["end"]) if item.get("end") else start + DEFAULT_DURATION
    return start, end

def _bool(value, default=True):
    if value is None or value == "":
        return default
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "нет", "0", "no")
    return bool(value)

def parse_weekdays(text):
    if not text:
        return []
    parts = str(text).replace(",", " ").replace(";", " ").split()
    result = []
    for p in parts:
        n = p.strip().lower()
        if n in SHORT_DAYS:
            result.append(SHORT_DAYS.index(n))
        elif n in DAY_NAMES:
            result.append(DAY_NAMES.index(n))
        else:
            raise ValueError(f"непонятный день недели: {p}")
    return sorted(set(result))

def occurs_on(item, day):
    if not isinstance(day, datetime.date):
        raise TypeError("day должен быть датой")
    if day.isoformat() in item.get("skip_dates", []):
        return False
    if item.get("date"):
        return item["date"] == day.isoformat()
    anchor = datetime.date.fromisoformat(item["anchor"])
    if day < anchor:
        return False
    if item.get("until") and day > datetime.date.fromisoformat(item["until"]):
        return False
    every = max(1, int(item.get("every_days", 7)))
    if (day - anchor).days % every != 0:
        return False
    days = item.get("weekdays") or []
    if days and day.weekday() not in days:
        return False
    return True

def items_on(day):
    items = [i for i in _load() if occurs_on(i, day)]
    return sorted(items, key=lambda i: _mins(i["start"]))

def commute(items):
    off = [i for i in items
           if i.get("place", "офлайн") == "офлайн"
           and i.get("source", "есть") == "есть"
           and i.get("commute", True)]
    if not off:
        return []
    first = min(_span(i)[0] for i in off)
    last = max(_span(i)[1] for i in off)
    return [(first - DEFAULT_COMMUTE, first, "дорога туда"),
            (last, last + DEFAULT_COMMUTE, "дорога обратно")]

def busy_intervals(day):
    items = items_on(day)
    busy = [(*_span(i), i["title"]) for i in items if i.get("source", "есть") == "есть"]
    busy += commute(items)
    return sorted(busy)

def free_slots(day, min_minutes=45):
    if min_minutes < 0:
        raise ValueError("min_minutes не может быть отрицательным")
    cursor, end_of_day = _mins(DAY_WINDOW[0]), _mins(DAY_WINDOW[1])
    free = []
    for start, end, _ in busy_intervals(day):
        if end <= cursor:
            continue
        if start >= end_of_day:
            break
        start = max(start, cursor)
        end = min(end, end_of_day)
        if start - cursor >= min_minutes:
            free.append((cursor, start))
        cursor = max(cursor, end)
    if end_of_day - cursor >= min_minutes:
        free.append((cursor, end_of_day))
    return [(_fmt(a), _fmt(b)) for a, b in free]

def conflicts(day):
    busy = busy_intervals(day)
    out = []
    for n, a in enumerate(busy):
        for b in busy[n + 1:]:
            if a[0] < b[1] and b[0] < a[1]:
                out.append(f"«{a[2]}» пересекается с «{b[2]}»")
    return out

def day_view(day):
    items = items_on(day)
    head = f"{day:%d.%m} ({DAY_NAMES[day.weekday()]})"
    if not items:
        return f"{head}: занятий нет, окно {DAY_WINDOW[0]}-{DAY_WINDOW[1]}"
    lines = [head + ":"]
    for i in items:
        start, end = _span(i)
        lines.append(f"  #{i.get('id', '-')} {_fmt(start)}-{_fmt(end)} {i['title']} "
                     f"[{i.get('source', 'есть')}; {i.get('kind', 'обязательное')}; "
                     f"{i.get('mode', 'присутствие')}; {i.get('place', 'офлайн')}]")
    for a, b, label in commute(items):
        lines.append(f"  {label}: {_fmt(a)}-{_fmt(b)}")
    free = free_slots(day)
    lines.append("  свободно: " + (", ".join(f"{a}-{b}" for a, b in free) or "нет окон"))
    lines += [f"  ! {c}" for c in conflicts(day)]
    return "\n".join(lines)

def view(date_text="", days=1):
    try:
        start = datetime.date.fromisoformat(date_text) if date_text else datetime.date.today()
    except (TypeError, ValueError):
        return "Дата в формате YYYY-MM-DD"
    try:
        days = int(days or 1)
    except (TypeError, ValueError):
        return "Количество дней должно быть числом от 1 до 7"
    days = max(1, min(days, 7))
    return "\n\n".join(day_view(start + datetime.timedelta(n)) for n in range(days))

def _build(d):
    if not isinstance(d, dict):
        raise ValueError("занятие должно быть объектом")
    title = str(d.get("title", "")).strip()
    if not title:
        raise ValueError("нет названия")
    start = d.get("start", "")
    _mins(start)
    end = d.get("end") or ""
    if end:
        _mins(end)
        if _mins(end) <= _mins(start):
            raise ValueError("окончание должно быть позже начала")
    source = d.get("source") or "есть"
    kind = d.get("kind") or "обязательное"
    mode = d.get("mode") or "присутствие"
    place = d.get("place") or "офлайн"
    if source not in SOURCES or kind not in KINDS or mode not in MODES or place not in PLACES:
        raise ValueError("проверьте source, kind, mode, place")
    item = {"title": title, "start": start, "end": end, "source": source, "kind": kind,
            "mode": mode, "place": place, "commute": _bool(d.get("commute")), "skip_dates": []}
    if d.get("date") and d.get("anchor"):
        raise ValueError("укажите date или anchor, но не оба")
    if d.get("date"):
        item["date"] = datetime.date.fromisoformat(d["date"]).isoformat()
    else:
        if not d.get("anchor"):
            raise ValueError("для повтора нужна первая дата anchor")
        item["anchor"] = datetime.date.fromisoformat(d["anchor"]).isoformat()
        try:
            every_days = int(d.get("every_days") or 7)
        except (TypeError, ValueError):
            raise ValueError("every_days должен быть целым числом") from None
        if every_days < 1:
            raise ValueError("every_days должен быть положительным")
        item["every_days"] = every_days
        item["weekdays"] = parse_weekdays(d.get("weekdays"))
        if d.get("until"):
            item["until"] = datetime.date.fromisoformat(d["until"]).isoformat()
            if item["until"] < item["anchor"]:
                raise ValueError("until не может быть раньше anchor")
    return item

def add_items(items):
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except json.JSONDecodeError:
            return "items должен быть списком объектов"
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list) or not items:
        return "Пустой список занятий"
    stored = _load()
    next_id = _next_id(stored)
    added, errors = [], []
    for d in items:
        label = d.get("title", "?") if isinstance(d, dict) else str(d)
        try:
            item = _build(d)
            item["id"] = next_id
            next_id += 1
            stored.append(item)
            added.append(f"#{item['id']} {item['title']}")
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            errors.append(f"{label}: {e}")
    if added:
        _save(stored)
    msg = ("Добавлено " + str(len(added)) + ": " + "; ".join(added)) if added else "Ничего не добавлено"
    if errors:
        msg += " | Ошибки: " + "; ".join(errors)
    return msg

def _find(items, key):
    key = str(key).strip()
    if not key:
        return []
    by_id = [i for i in items if str(i.get("id")) == key.lstrip("#")]
    if by_id:
        return by_id
    needle = key.lower()
    return [i for i in items if needle in str(i.get("title", "")).lower()]

def skip_occurrence(key, date):
    items = _load()
    matches = _find(items, key)
    if not matches:
        return f"«{key}» не найдено"
    if len(matches) > 1:
        return "Подходит несколько, укажите id: " + "; ".join(f"#{i['id']} {i['title']}" for i in matches)
    try:
        day = datetime.date.fromisoformat(date)
    except (TypeError, ValueError):
        return "Дата в формате YYYY-MM-DD"
    item = matches[0]
    if not occurs_on(item, day):
        return f"«{item.get('title', '?')}» не идёт {date}"
    if item.get("date"):
        items.remove(item)
    else:
        skipped = item.setdefault("skip_dates", [])
        if date not in skipped:
            skipped.append(date)
    _save(items)
    return f"Пропуск записан: «{item.get('title', '?')}» на {date}"

def move_occurrence(key, from_date, to_date):
    items = _load()
    matches = _find(items, key)
    if len(matches) != 1:
        return "Нужно однозначное название или id"
    src = dict(matches[0])
    try:
        day_from = datetime.date.fromisoformat(from_date)
        day_to = datetime.date.fromisoformat(to_date)
    except (TypeError, ValueError):
        return "Даты в формате YYYY-MM-DD"
    if day_from == day_to:
        return "Новая дата должна отличаться от исходной"
    if not occurs_on(src, day_from):
        return f"«{src.get('title', '?')}» не идёт {from_date}"
    if occurs_on(src, day_to):
        return f"«{src.get('title', '?')}» уже идёт {to_date}"
    result = skip_occurrence(str(src["id"]), from_date)
    if not result.startswith("Пропуск записан:"):
        return result
    items = _load()
    next_id = _next_id(items)
    new = {k: v for k, v in src.items()
           if k not in ("id", "anchor", "every_days", "weekdays", "until", "skip_dates", "date")}
    new.update({"id": next_id, "date": to_date, "skip_dates": []})
    items.append(new)
    _save(items)
    return f"Перенесено: «{src.get('title', '?')}» с {from_date} на {to_date}"

def remove_item(key):
    items = _load()
    matches = _find(items, key)
    if not matches:
        return f"«{key}» не найдено"
    if len(matches) > 1:
        return "Подходит несколько, укажите id: " + "; ".join(f"#{i['id']} {i['title']}" for i in matches)
    items.remove(matches[0])
    _save(items)
    return f"Удалено из расписания: «{matches[0]['title']}»"