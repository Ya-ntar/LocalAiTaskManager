import json, os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
USER_DATA_DIR = os.path.join(BASE, "user_data")
PROJECTS_DIR = os.path.join(USER_DATA_DIR, "projects")

FILES = {
    "tasks": os.path.join(USER_DATA_DIR, "tasks.json"),
    "goals": os.path.join(USER_DATA_DIR, "goals.json"),
    "recurring": os.path.join(USER_DATA_DIR, "recurring.json"),
    "hobbies": os.path.join(USER_DATA_DIR, "hobbies.json"),
    "chat_log": os.path.join(USER_DATA_DIR, "chat_log.json"),
    "reports": os.path.join(USER_DATA_DIR, "reports.jsonl"),
}

LEGACY_FILES = {
    "tasks": os.path.join(BASE, "tasks.json"),
    "goals": os.path.join(BASE, "goals.json"),
    "recurring": os.path.join(BASE, "recurring.json"),
    "hobbies": os.path.join(BASE, "hobbies.json"),
    "chat_log": os.path.join(BASE, "chat_log.json"),
    "reports": os.path.join(BASE, "reports.jsonl"),
}

LEGACY_USER_FILES = {
    "timetable.json", "subjects.json", "schedule.json", "changes.log",
    "board.html",
}
LEGACY_USER_DIRS = {"chats", "topics", "projects"}

def read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    return json.loads(text) if text else default

def write_json(path, data):
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def load(name, default=None):
    _migrate_file(name)
    return read_json(FILES[name], [] if default is None else default)

def save(name, data):
    write_json(FILES[name], data)

def _migrate_file(name):
    source = LEGACY_FILES.get(name)
    target = FILES.get(name)
    if source and target and os.path.exists(source) and not os.path.exists(target):
        os.makedirs(os.path.dirname(target), exist_ok=True)
        os.replace(source, target)

def migrate_user_data():
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    for name, source in LEGACY_FILES.items():
        target = FILES[name]
        if os.path.exists(source) and not os.path.exists(target):
            os.replace(source, target)
    for name in LEGACY_USER_FILES:
        source = os.path.join(BASE, name)
        target = os.path.join(USER_DATA_DIR, name)
        if os.path.exists(source) and not os.path.exists(target):
            os.replace(source, target)
    for name in LEGACY_USER_DIRS:
        source = os.path.join(BASE, name)
        target = os.path.join(USER_DATA_DIR, name)
        if os.path.isdir(source) and not os.path.exists(target):
            os.replace(source, target)

def append_report(entry):
    with open(FILES["reports"], "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def read_reports():
    if not os.path.exists(FILES["reports"]):
        return []
    with open(FILES["reports"], encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def project_path(name):
    safe = "".join(c for c in name if c.isalnum() or c in "-_") or "project"
    return os.path.join(PROJECTS_DIR, safe + ".json")

def load_project(name):
    empty = {"name": name, "status": "зелёный", "deadlines": [], "people": [], "notes": []}
    return read_json(project_path(name), empty)

def save_project(name, data):
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    write_json(project_path(name), data)

def list_projects():
    if not os.path.isdir(PROJECTS_DIR):
        return []
    return [f[:-5] for f in os.listdir(PROJECTS_DIR) if f.endswith(".json")]