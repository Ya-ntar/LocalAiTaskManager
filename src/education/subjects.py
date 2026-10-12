import os, datetime
from ..infrastructure import store
from . import timetable
from ..planner import tasks

PATH = os.path.join(store.USER_DATA_DIR, "subjects.json")

def _today():
    return datetime.date.today()

def _key(name):
    return " ".join(str(name).lower().split())

def _data():
    return store.read_json(PATH, {})

def _save(data):
    store.write_json(PATH, data)

def _names():
    """Предметы из расписания (факты) плюс те, по которым уже есть данные."""
    names = {}
    for item in store.read_json(timetable.PATH, []):
        if item.get("source", "есть") == "есть":
            names.setdefault(_key(item["title"]), item["title"])
    for k, v in _data().items():
        names.setdefault(k, v.get("name", k))
    return names

def _alias_matches(needle, names):
    aliases = {
        "английский": ("english", "англий"),
        "английский язык": ("english", "англий"),
        "го": ("го",),
    }
    return [name for name in names.values()
            if any(alias in _key(name) for alias in aliases.get(needle, ()))]

def _task_subject(task, names):
    subject = _key(task.get("subject", ""))
    if not subject:
        return None
    if subject in names:
        return names[subject]
    matches = [k for k in names if subject in k or k in subject]
    if len(matches) == 1:
        return names[matches[0]]
    alias_matches = _alias_matches(subject, names)
    return alias_matches[0] if len(alias_matches) == 1 else None

def _open_task_homework(name, names):
    target = _key(name)
    result = []
    for task in tasks.load_tasks():
        if task.get("column") == "Готово":
            continue
        task_subject = _task_subject(task, names)
        if task_subject and _key(task_subject) == target:
            result.append(task)
    return result

def _resolve(text):
    names = _names()
    needle = _key(text)
    if not needle:
        return None, "Укажите предмет"
    if needle in names:
        return names[needle], None
    found = [k for k in names if needle in k]
    found_names = _alias_matches(needle, names)
    if len(found_names) == 1:
        return found_names[0], None
    if len(found) == 1:
        return names[found[0]], None
    if not found:
        return None, "Предмет не найден. Есть: " + ", ".join(sorted(names.values()))
    return None, "Подходит несколько предметов: " + ", ".join(names[k] for k in found)

def _entry(data, name):
    return data.setdefault(_key(name), {"name": name, "homework": [], "notes": [], "touched": ""})

def _open_hw(entry):
    return [h for h in entry.get("homework", []) if not h.get("done")]

def show_subjects():
    names = _names()
    if not names:
        return "Предметов пока нет. Они появятся из расписания."
    data = _data()
    rows = []
    for k, name in names.items():
        e = data.get(k, {"homework": []})
        open_hw = _open_hw(e)
        open_tasks = _open_task_homework(name, names)
        dues = sorted(h["due"] for h in open_hw if h.get("due"))
        task_dues = sorted(t["due"] for t in open_tasks if t.get("due"))
        all_dues = sorted(dues + task_dues)
        total = len(open_hw) + len(open_tasks)
        label = "открытых домашних заданий" if not open_tasks else "открытых домашних заданий и задач"
        line = f"- {name}: {label} {total}"
        if all_dues:
            line += f", ближайший срок {all_dues[0]}"
        rows.append((all_dues[0] if all_dues else "9999", line))
    return "\n".join(line for _, line in sorted(rows))

def subject_detail(subject):
    name, err = _resolve(subject)
    if err:
        return err
    e = _data().get(_key(name), {"homework": [], "notes": []})
    lines = [f"[{name}]"]
    open_hw = _open_hw(e)
    if not open_hw:
        lines.append("Открытой домашки нет.")
    for h in open_hw:
        lines.append(f"  домашка: {h['title']}" + (f" до {h['due']}" if h.get("due") else ""))
    for task in _open_task_homework(name, _names()):
        lines.append(f"  задача: {task['title']}" + (f" до {task['due']}" if task.get("due") else ""))
    for n in e.get("notes", [])[-5:]:
        lines.append(f"  заметка {n['date']}: {n['text']}")
    return "\n".join(lines)

def add_homework(subject, title, due=""):
    name, err = _resolve(subject)
    if err:
        return err
    if due:
        try:
            datetime.date.fromisoformat(due)
        except ValueError:
            return "Срок нужен в формате YYYY-MM-DD"
    data = _data()
    e = _entry(data, name)
    next_id = max([h.get("id", 0) for h in e["homework"]] + [0]) + 1
    e["homework"].append({"id": next_id, "title": title, "due": due or "", "done": False})
    e["touched"] = _today().isoformat()
    _save(data)
    return f"Записано по «{name}»: {title}" + (f", срок {due}" if due else "")

def done_homework(subject, title):
    name, err = _resolve(subject)
    if err:
        return err
    data = _data()
    e = _entry(data, name)
    matches = [h for h in _open_hw(e) if title.lower() in h["title"].lower()]
    if not matches:
        return f"Открытой домашки «{title}» по «{name}» нет"
    if len(matches) > 1:
        return "Подходит несколько, уточните: " + "; ".join(h["title"] for h in matches)
    matches[0]["done"] = True
    e["touched"] = _today().isoformat()
    _save(data)
    return f"Отмечено выполненным: {matches[0]['title']}"

def add_subject_note(subject, text):
    name, err = _resolve(subject)
    if err:
        return err
    data = _data()
    e = _entry(data, name)
    e["notes"].append({"date": _today().isoformat(), "text": text})
    e["notes"] = e["notes"][-100:]
    e["touched"] = _today().isoformat()
    _save(data)
    return f"Заметка по «{name}» записана"

def subject_to_ask():
    """Выбирает предмет для вопроса: сначала срочная домашка, потом давно не обсуждавшийся."""
    names = _names()
    data = _data()
    today = _today()
    best = None
    for k, name in names.items():
        for h in _open_hw(data.get(k, {"homework": []})):
            if not h.get("due"):
                continue
            days = (datetime.date.fromisoformat(h["due"]) - today).days
            if days <= 7 and (best is None or days < best[0]):
                best = (days, name, f"домашка «{h['title']}», срок через {days} дн. (отрицательное число значит просрочка)")
    if best:
        return f"{best[1]}: {best[2]}"
    if not names:
        return ""
    stale = min(names.items(), key=lambda kv: data.get(kv[0], {}).get("touched", ""))
    return f"{stale[1]} (давно не обсуждали)"