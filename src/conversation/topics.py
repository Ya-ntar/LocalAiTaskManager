import os, datetime
from ..infrastructure import store

TOPICS_DIR = os.path.join(store.USER_DATA_DIR, "topics")
INDEX = os.path.join(TOPICS_DIR, "index.json")

def _today():
    return datetime.date.today().isoformat()

def _load_index():
    return store.read_json(INDEX, [])

def _save_index(items):
    os.makedirs(TOPICS_DIR, exist_ok=True)
    store.write_json(INDEX, items)

def _path(topic_id):
    return os.path.join(TOPICS_DIR, topic_id + ".md")

def _append(topic_id, text):
    os.makedirs(TOPICS_DIR, exist_ok=True)
    with open(_path(topic_id), "a", encoding="utf-8") as f:
        f.write(text + "\n")

def _resolve(items, title, status=None):
    """Ищет тему по названию. status=None — среди всех тем."""
    pool = [i for i in items if status is None or i["status"] == status]
    needle = title.lower().strip()
    exact = [i for i in pool if i["title"].lower() == needle]
    if len(exact) == 1:
        return exact[0], None
    found = [i for i in pool if needle in i["title"].lower()]
    if len(found) == 1:
        return found[0], None
    if not found:
        return None, f"Тема «{title}» не найдена"
    return None, "Подходит несколько тем, уточните: " + "; ".join(i["title"] for i in found)

def list_topics(include_closed=False):
    items = _load_index()
    lines = []
    for i in items:
        if i["status"] == "открыта" or include_closed:
            lines.append(f"- {i['title']} ({i['status']}, с {i['opened']})")
    return "\n".join(lines) if lines else "Открытых тем нет"

def open_topic(title, first_note=""):
    items = _load_index()
    existing, _ = _resolve(items, title, "открыта")
    if existing:
        return f"Такая тема уже открыта: «{existing['title']}». Пишите в неё через add_note."
    today = _today()
    topic_id = f"{today.replace('-', '')}-{len(items) + 1:03d}"
    os.makedirs(TOPICS_DIR, exist_ok=True)
    with open(_path(topic_id), "w", encoding="utf-8") as f:
        f.write(f"# {title}\nОткрыта: {today}\n\n")
    items.append({"id": topic_id, "title": title, "status": "открыта", "opened": today, "closed": ""})
    _save_index(items)
    if first_note:
        _append(topic_id, f"- {today}: {first_note}")
    return f"Открыта новая тема: «{title}» (файл topics/{topic_id}.md)"

def add_note(topic, text):
    items = _load_index()
    t, err = _resolve(items, topic, "открыта")
    if err:
        return err
    _append(t["id"], f"- {_today()}: {text}")
    return f"Записано в «{t['title']}»"

def read_topic(topic):
    items = _load_index()
    t, err = _resolve(items, topic)
    if err:
        return err
    if not os.path.exists(_path(t["id"])):
        return "Файл темы пуст или отсутствует"
    with open(_path(t["id"]), encoding="utf-8") as f:
        text = f.read()
    return text[-3000:]

def close_topic(topic, summary=""):
    items = _load_index()
    t, err = _resolve(items, topic, "открыта")
    if err:
        return err
    today = _today()
    t["status"] = "закрыта"
    t["closed"] = today
    _save_index(items)
    _append(t["id"], f"\n## Закрыто {today}\n{summary}" if summary else f"\n## Закрыто {today}")
    return f"Тема закрыта: «{t['title']}»"

def reopen_topic(topic):
    items = _load_index()
    t, err = _resolve(items, topic, "закрыта")
    if err:
        return err
    t["status"] = "открыта"
    t["closed"] = ""
    _save_index(items)
    _append(t["id"], f"- переоткрыта {_today()}")
    return f"Тема снова открыта: «{t['title']}»"