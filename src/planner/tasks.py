import datetime
import json
import re
import uuid
from . import priority
from ..infrastructure.config import COLUMNS, EFFORTS
from . import task_format, task_repository

def today():
    return task_format.today()

def load_tasks():
    return task_repository.load_tasks()

def save_tasks(tasks):
    task_repository.save_tasks(tasks)

def untouched_days(t):
    return task_format.untouched_days(t)

def prio(t):
    return task_format.prio(t)

def task_line(t):
    return task_format.task_line(t)

def sorted_column(tasks, column):
    return sorted((t for t in tasks if t["column"] == column), key=prio, reverse=True)

def check_due(due):
    if due:
        datetime.date.fromisoformat(due)

def to_importance(value):
    return 0.5 if value in (None, "") else priority.clamp(float(value))

def to_window(value):
    return 0 if value in (None, "") else max(0, int(value))

def find_tasks(tasks, title):
    return [t for t in tasks if title.lower() in t["title"].lower()]

def query_tasks(filters=None):
    """Return task records matching a model-selected set of filters."""
    filters = filters or {}
    result = []
    for task in load_tasks():
        if filters.get("id") and task.get("id") != filters["id"]:
            continue
        if filters.get("title_contains") and filters["title_contains"].lower() not in task["title"].lower():
            continue
        if filters.get("subject") and task.get("subject", "").lower() != filters["subject"].lower():
            continue
        if filters.get("column") and task.get("column") != filters["column"]:
            continue
        if filters.get("tag") and filters["tag"].lower() not in [str(x).lower() for x in task.get("tags", [])]:
            continue
        if filters.get("due_before") and (not task.get("due") or task["due"] >= filters["due_before"]):
            continue
        if filters.get("due_after") and (not task.get("due") or task["due"] <= filters["due_after"]):
            continue
        result.append(task)
    return [_task_snapshot(task) for task in result]

def _task_snapshot(task):
    return {key: task.get(key) for key in (
        "id", "title", "column", "due", "effort", "minutes", "importance",
        "subject", "tags", "related_ids", "blocked_by", "parent_id"
    )}

def propose_task_changes(operations):
    """Validate and render a batch of ID-based changes without applying it."""
    if not isinstance(operations, list) or not operations:
        return "План изменений должен содержать непустой список operations"
    current = {task["id"]: task for task in load_tasks()}
    preview = []
    allowed = {"delete", "archive", "move", "update", "link", "block", "unblock"}
    for operation in operations:
        if not isinstance(operation, dict) or operation.get("action") not in allowed:
            return "Неизвестная операция. Разрешены: " + ", ".join(sorted(allowed))
        action = operation["action"]
        task_id = operation.get("task_id")
        if task_id not in current:
            return f"Задача с id «{task_id}» не найдена"
        other_id = operation.get("other_task_id")
        if action in {"link", "block", "unblock"} and other_id not in current:
            return f"Задача с id «{other_id}» не найдена"
        if action == "move" and operation.get("column") not in COLUMNS:
            return f"Нет колонки «{operation.get('column')}». Есть: {', '.join(COLUMNS)}"
        preview.append({
            "action": action,
            "task_id": task_id,
            "other_task_id": other_id,
            "task": _task_snapshot(current[task_id]),
            "other_task": _task_snapshot(current[other_id]) if other_id else None,
            "column": operation.get("column"),
            "changes": operation.get("changes", {}),
            "reason": operation.get("reason", "")
        })
    return json.dumps({"operations": operations, "preview": preview}, ensure_ascii=False)

def apply_task_changes(operations):
    """Apply a previously previewed batch using stable task IDs."""
    preview = propose_task_changes(operations)
    if not preview.startswith("{"):
        return preview
    current = {task["id"]: task for task in load_tasks()}
    changed = []
    for operation in operations:
        action = operation["action"]
        task = current[operation["task_id"]]
        if action == "delete":
            current.pop(task["id"])
        elif action == "archive":
            task["column"] = "Архив"
        elif action == "move":
            task["column"] = operation["column"]
        elif action == "update":
            for key, value in operation.get("changes", {}).items():
                if key in {"title", "due", "effort", "minutes", "risk", "importance", "window_days", "subject", "tags", "column"}:
                    task[key] = value
        elif action in {"link", "block", "unblock"}:
            other = current[operation["other_task_id"]]
            field = "related_ids" if action == "link" else "blocked_by"
            if action == "block":
                if other["id"] not in task.setdefault(field, []):
                    task[field].append(other["id"])
            elif action == "unblock":
                if other["id"] in task.setdefault(field, []):
                    task[field].remove(other["id"])
            elif other["id"] not in task.setdefault(field, []):
                task[field].append(other["id"])
            if action == "link" and task["id"] not in other.setdefault("related_ids", []):
                other["related_ids"].append(task["id"])
        if action != "delete":
            task["touched"] = today().isoformat()
        changed.append({"action": action, "task_id": task["id"], "title": task["title"]})
    remaining_ids = set(current)
    for task in current.values():
        task["related_ids"] = [item for item in task.get("related_ids", []) if item in remaining_ids]
        task["blocked_by"] = [item for item in task.get("blocked_by", []) if item in remaining_ids]
    save_tasks(list(current.values()))
    return json.dumps({"applied": changed, "count": len(changed)}, ensure_ascii=False)

def add_task(column, title, due="", effort="", minutes=0, risk="", importance=None,
             window_days=None, subject="", parent_id="", tags=None):
    if column not in COLUMNS:
        return f"Нет колонки «{column}». Есть: {', '.join(COLUMNS)}"
    if effort and effort not in EFFORTS:
        return f"Сложность должна быть одной из: {', '.join(EFFORTS)}"
    try:
        check_due(due)
        imp = to_importance(importance)
        win = to_window(window_days)
    except ValueError:
        return "Дедлайн нужен в формате YYYY-MM-DD, важность числом от 0 до 1, окно в днях"
    tasks = load_tasks()
    if parent_id and not _get_task(tasks, parent_id):
        return f"Родительская задача «{parent_id}» не найдена"
    tasks.append({"title": title, "column": column, "due": due or "", "effort": effort or "",
                  "minutes": int(minutes or 0), "risk": risk or "", "importance": imp,
                  "window_days": win, "subject": str(subject or "").strip(),
                  "tags": _normalize_tags(tags, subject),
                  "parent_id": _get_task(tasks, parent_id)["id"] if parent_id else "",
                  "notes": [], "related_ids": [], "blocked_by": [],
                  "id": uuid.uuid4().hex[:8], "touched": today().isoformat()})
    save_tasks(tasks)
    return f"Добавлено: {task_line(tasks[-1])}"

def update_task(title, column="", due="", effort="", minutes=None, risk="", importance=None,
                window_days=None, subject=None, tags=None):
    tasks = load_tasks()
    matches = find_tasks(tasks, title)
    if not matches:
        return f"Задача «{title}» не найдена"
    if len(matches) > 1:
        return "Подходит несколько задач, уточните название: " + "; ".join(t["title"] for t in matches)
    task = matches[0]
    try:
        if column:
            if column not in COLUMNS:
                return f"Нет колонки «{column}»"
            task["column"] = column
        if due:
            check_due(due)
            task["due"] = due
        if effort:
            if effort not in EFFORTS:
                return f"Сложность должна быть одной из: {', '.join(EFFORTS)}"
            task["effort"] = effort
        if minutes is not None:
            task["minutes"] = int(minutes)
        if risk:
            task["risk"] = risk
        if importance is not None:
            task["importance"] = to_importance(importance)
        if window_days is not None:
            task["window_days"] = to_window(window_days)
        if subject is not None:
            task["subject"] = str(subject).strip()
        if tags is not None:
            task["tags"] = _normalize_tags(tags, task.get("subject", ""))
    except ValueError:
        return "Дедлайн нужен в формате YYYY-MM-DD, важность числом от 0 до 1, окно в днях"
    task["touched"] = today().isoformat()
    save_tasks(tasks)
    return f"Обновлено: {task_line(task)}"

def set_task_due(task_id, due):
    task_list = load_tasks()
    task = next((item for item in task_list if item.get("id") == task_id), None)
    if not task:
        return f"Задача с id «{task_id}» не найдена"
    try:
        check_due(due)
    except ValueError:
        return "Дедлайн нужен в формате YYYY-MM-DD"
    task["due"] = due
    task["touched"] = today().isoformat()
    save_tasks(task_list)
    return f"Обновлено: {task_line(task)}"

def _normalize_tags(tags, subject=""):
    return task_format.normalize_tags(tags, subject)

def add_task_tags(task_ids, tags):
    """Add tags to exact task IDs without replacing existing tags."""
    if not isinstance(task_ids, list) or not task_ids:
        return "Нужно указать хотя бы один id задачи"
    if not isinstance(tags, list) or not tags:
        return "Нужно указать хотя бы один тег"
    task_list = load_tasks()
    by_id = {task.get("id"): task for task in task_list}
    missing = [task_id for task_id in task_ids if task_id not in by_id]
    if missing:
        return f"Задачи с id не найдены: {', '.join(missing)}"
    normalized = _normalize_tags(tags)
    if not normalized:
        return "Теги не могут быть пустыми"
    changed = []
    for task_id in dict.fromkeys(task_ids):
        task = by_id[task_id]
        current = task.setdefault("tags", [])
        for tag in normalized:
            if tag.casefold() not in {str(item).casefold() for item in current}:
                current.append(tag)
        task["touched"] = today().isoformat()
        changed.append({"id": task_id, "title": task["title"], "tags": current})
    save_tasks(task_list)
    return json.dumps({"updated": changed, "count": len(changed)}, ensure_ascii=False)

def edit_task(task, title=None, importance=None, minutes=None, tags=None):
    tasks = load_tasks()
    target = _get_task(tasks, task)
    if not target:
        return f"Задача «{task}» не найдена или найдено несколько"
    new_title = str(title or "").strip()
    if title is not None and not new_title:
        return "Название задачи не может быть пустым"
    try:
        if title is not None:
            target["title"] = new_title
        if importance is not None:
            target["importance"] = to_importance(importance)
        if minutes is not None:
            target["minutes"] = max(0, int(minutes))
        if tags is not None:
            target["tags"] = _normalize_tags(tags)
            target["subject"] = target["tags"][0] if target["tags"] else ""
    except (TypeError, ValueError):
        return "Приоритет должен быть числом от 0 до 1, длительность — целым числом минут"
    target["touched"] = today().isoformat()
    save_tasks(tasks)
    return f"Обновлено: {task_line(target)}"

def delete_task(title="", task_id=""):
    tasks = load_tasks()
    requested_ids = re.findall(r"\b[a-f0-9]{8}\b", str(task_id or ""), re.IGNORECASE)
    if not requested_ids:
        requested_ids = re.findall(r"\b[a-f0-9]{8}\b", str(title or ""), re.IGNORECASE)
    if requested_ids:
        by_id = {task.get("id"): task for task in tasks}
        missing = [item for item in requested_ids if item not in by_id]
        if missing:
            return f"Задачи с id не найдены: {', '.join(missing)}"
        removed = [by_id[item] for item in requested_ids]
        tasks = [task for task in tasks if task.get("id") not in requested_ids]
        save_tasks(tasks)
        names = "; ".join(f"«{task['title']}» ({task['id']})" for task in removed)
        return f"Удалено: {names}"
    matches = find_tasks(tasks, title)
    if not matches:
        return f"Задача «{title}» не найдена"
    if len(matches) > 1:
        return "Подходит несколько задач, уточните название: " + "; ".join(t["title"] for t in matches)
    tasks.remove(matches[0])
    save_tasks(tasks)
    return f"Удалено: «{matches[0]['title']}»"

def _get_task(tasks, key):
    key = str(key or "").strip().lower()
    matches = [task for task in tasks if task.get("id", "").lower() == key]
    if not matches:
        matches = [task for task in tasks if key and key in task["title"].lower()]
    return matches[0] if len(matches) == 1 else None

def _get_pair(tasks, first, second):
    left, right = _get_task(tasks, first), _get_task(tasks, second)
    if not left or not right:
        return None, None, "Обе задачи должны однозначно находиться по id или названию"
    if left["id"] == right["id"]:
        return None, None, "Нельзя связать задачу саму с собой"
    return left, right, ""

def add_task_note(task, text):
    tasks = load_tasks()
    target = _get_task(tasks, task)
    if not target:
        return f"Задача «{task}» не найдена или найдено несколько"
    text = str(text or "").strip()
    if not text:
        return "Заметка не может быть пустой"
    target.setdefault("notes", []).append({"text": text, "created": datetime.datetime.now().isoformat(timespec="seconds")})
    save_tasks(tasks)
    return f"Заметка добавлена к задаче «{target['title']}»"

def archive_task(task):
    tasks = load_tasks()
    target = _get_task(tasks, task)
    if not target:
        return f"Задача «{task}» не найдена или найдено несколько"
    target["column"] = "Архив"
    target["touched"] = today().isoformat()
    save_tasks(tasks)
    return f"Задача перемещена в архив: «{target['title']}»"


def move_task(task, column):
    if column not in COLUMNS:
        return f"Нет колонки «{column}»"
    tasks = load_tasks()
    target = _get_task(tasks, task)
    if not target:
        return f"Задача «{task}» не найдена или найдено несколько"
    if target.get("column") == column:
        return f"Задача уже находится в колонке «{column}»"
    previous = target.get("column", "Входящие")
    target["column"] = column
    target["touched"] = today().isoformat()
    save_tasks(tasks)
    return f"Задача перемещена: «{previous}» → «{column}»"


def delete_archived_task(task):
    tasks = load_tasks()
    target = _get_task(tasks, task)
    if not target:
        return f"Задача «{task}» не найдена или найдено несколько"
    if target.get("column") != "Архив":
        return "Окончательно удалить можно только задачу из колонки «Архив»"
    tasks.remove(target)
    save_tasks(tasks)
    return f"Удалено окончательно: «{target['title']}»"

def add_subtask(parent, title):
    title = str(title or "").strip()
    if not title:
        return "Название подзадачи не может быть пустым"
    tasks = load_tasks()
    target = _get_task(tasks, parent)
    if not target:
        return f"Родительская задача «{parent}» не найдена или найдено несколько"
    return add_task(target.get("column", "Входящие"), title, parent_id=target["id"])

def link_tasks(task, related_task):
    tasks = load_tasks()
    left, right, error = _get_pair(tasks, task, related_task)
    if error:
        return error
    if right["id"] not in left.setdefault("related_ids", []):
        left["related_ids"].append(right["id"])
    if left["id"] not in right.setdefault("related_ids", []):
        right["related_ids"].append(left["id"])
    save_tasks(tasks)
    return f"Задачи связаны: «{left['title']}» ↔ «{right['title']}»"

def block_task(task, blocked_by):
    tasks = load_tasks()
    target, blocker, error = _get_pair(tasks, task, blocked_by)
    if error:
        return error
    if blocker["id"] not in target.setdefault("blocked_by", []):
        target["blocked_by"].append(blocker["id"])
    save_tasks(tasks)
    return f"Задача «{target['title']}» заблокирована задачей «{blocker['title']}»"

def unblock_task(task, blocked_by):
    tasks = load_tasks()
    target, blocker, error = _get_pair(tasks, task, blocked_by)
    if error:
        return error
    if blocker["id"] in target.setdefault("blocked_by", []):
        target["blocked_by"].remove(blocker["id"])
    save_tasks(tasks)
    return f"Блокировка снята: «{target['title']}» ← «{blocker['title']}»"

def task_details(task):
    tasks = load_tasks()
    target = _get_task(tasks, task)
    if not target:
        return f"Задача «{task}» не найдена или найдено несколько"
    by_id = {item["id"]: item for item in tasks}
    children = [item for item in tasks if item.get("parent_id") == target["id"]]
    related = [by_id[item] for item in target.get("related_ids", []) if item in by_id]
    blockers = [by_id[item] for item in target.get("blocked_by", []) if item in by_id]
    lines = [task_line(target), f"id: {target['id']}"]
    if children:
        lines.append("Подтаски: " + "; ".join(item["title"] for item in children))
    if target.get("notes"):
        lines.append("Заметки:\n" + "\n".join(f"- {item['text']}" for item in target["notes"]))
    if related:
        lines.append("Связи: " + "; ".join(item["title"] for item in related))
    if blockers:
        lines.append("Блокирует выполнение: " + "; ".join(item["title"] for item in blockers))
    return "\n".join(lines)

def show_board():
    tasks = load_tasks()
    lines = []
    for c in COLUMNS:
        lines.append(f"[{c}]")
        for t in sorted_column(tasks, c):
            lines.append(f"  - {task_line(t)}")
    return "\n".join(lines)

def deadlines():
    tasks = [t for t in load_tasks() if t["column"] not in ("Готово", "Архив")]
    lines = []
    for t in sorted([t for t in tasks if t.get("due")], key=lambda t: t["due"]):
        days = (datetime.date.fromisoformat(t["due"]) - today()).days
        when = f"через {days} дн." if days >= 0 else f"просрочено на {-days} дн."
        lines.append(f"- {task_line(t)} ({when})")
    total = sum(int(t.get("minutes") or 0) for t in tasks)
    lines.append(f"Всего не завершено: {len(tasks)} задач, примерно {total // 60} ч {total % 60} мин работы.")
    return "\n".join(lines)