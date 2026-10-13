import os

from ..infrastructure import store
from . import task_repository

PATH = os.path.join(store.USER_DATA_DIR, "themes.json")
DEFAULT_THEME = "Без темы"


def _key(name):
    return " ".join(str(name).strip().split()).casefold()


def _normalize(name):
    return " ".join(str(name).strip().split())


def load(task_list=None):
    saved = store.read_json(PATH, [])
    names = [DEFAULT_THEME]
    keys = {_key(DEFAULT_THEME)}
    for name in saved if isinstance(saved, list) else []:
        normalized = _normalize(name)
        if normalized and _key(normalized) not in keys:
            names.append(normalized)
            keys.add(_key(normalized))
    for task in task_list or task_repository.load_tasks():
        for name in task.get("tags", []):
            normalized = _normalize(name)
            if normalized and _key(normalized) not in keys:
                names.append(normalized)
                keys.add(_key(normalized))
    names = [DEFAULT_THEME] + sorted(
        (name for name in names if _key(name) != _key(DEFAULT_THEME)),
        key=str.casefold,
    )
    if names != saved:
        store.write_json(PATH, names)
    return names


def add(name):
    normalized = _normalize(name)
    if not normalized:
        return "Название темы не может быть пустым"
    names = load()
    if any(_key(item) == _key(normalized) for item in names):
        return f"Тема «{normalized}» уже существует"
    names.append(normalized)
    names.sort(key=str.casefold)
    store.write_json(PATH, names)
    return f"Тема добавлена: «{normalized}»"


def rename(old_name, new_name):
    old = _normalize(old_name)
    new = _normalize(new_name)
    if not old or not new:
        return "Название темы не может быть пустым"
    if _key(old) == _key(DEFAULT_THEME):
        return f"Тему «{DEFAULT_THEME}» нельзя переименовать"
    names = load()
    if not any(_key(item) == _key(old) for item in names):
        return f"Тема «{old}» не найдена"
    if _key(old) != _key(new) and any(_key(item) == _key(new) for item in names):
        return f"Тема «{new}» уже существует"

    tasks = task_repository.load_tasks()
    changed = False
    for task in tasks:
        updated = [new if _key(tag) == _key(old) else tag for tag in task.get("tags", [])]
        if updated != task.get("tags", []):
            task["tags"] = list(dict.fromkeys(updated))
            changed = True
    if changed:
        task_repository.save_tasks(tasks)

    names = [new if _key(item) == _key(old) else item for item in names]
    names = sorted(dict.fromkeys(names), key=str.casefold)
    store.write_json(PATH, names)
    return f"Тема переименована: «{old}» → «{new}»"


def remove(name):
    target = _normalize(name)
    if not target:
        return "Название темы не может быть пустым"
    if _key(target) == _key(DEFAULT_THEME):
        return f"Тему «{DEFAULT_THEME}» нельзя удалить"
    names = load()
    if not any(_key(item) == _key(target) for item in names):
        return f"Тема «{target}» не найдена"

    task_list = task_repository.load_tasks()
    changed = False
    for task in task_list:
        updated = [tag for tag in task.get("tags", [])
                   if _key(tag) != _key(target)]
        if updated != task.get("tags", []):
            task["tags"] = updated
            changed = True
    if changed:
        task_repository.save_tasks(task_list)

    names = [item for item in names if _key(item) != _key(target)]
    store.write_json(PATH, names)
    return f"Тема удалена: «{target}»"
