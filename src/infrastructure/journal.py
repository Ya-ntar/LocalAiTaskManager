import json, datetime, os
from .config import CHANGES

def log_change(name, args, result):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M} {name} {json.dumps(args, ensure_ascii=False)} -> {result}\n"
    with open(CHANGES, "a", encoding="utf-8") as f:
        f.write(line)

def show_journal(limit=20):
    if not os.path.exists(CHANGES):
        return "Журнал пуст"
    with open(CHANGES, encoding="utf-8") as f:
        lines = f.readlines()
    return "".join(lines[-limit:]).strip() or "Журнал пуст"