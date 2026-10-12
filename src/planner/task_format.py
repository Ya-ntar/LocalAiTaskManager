import datetime

from . import priority


def today():
    return datetime.date.today()


def untouched_days(task):
    try:
        touched = datetime.date.fromisoformat(
            task.get("touched") or today().isoformat())
    except ValueError:
        touched = today()
    return max(0, (today() - touched).days)


def prio(task):
    return priority.priority(
        importance=task.get("importance", 0.5),
        due=task.get("due", ""),
        window_days=task.get("window_days", 0),
        untouched_days=untouched_days(task))


def task_line(task):
    parts = [task["title"], f"приоритет {prio(task):.2f}",
             f"id: {task.get('id', '')}"]
    if task.get("parent_id"):
        parts.append("подтаск")
    if task.get("blocked_by"):
        parts.append(f"заблокирована ({len(task['blocked_by'])})")
    if task.get("notes"):
        parts.append(f"заметок: {len(task['notes'])}")
    if task.get("related_ids"):
        parts.append(f"связей: {len(task['related_ids'])}")
    if task.get("subject"):
        parts.append(f"предмет: {task['subject']}")
    if task.get("tags"):
        parts.append("теги: " + ", ".join(task["tags"]))
    if task.get("due"):
        parts.append(f"дедлайн {task['due']}")
    if task.get("effort"):
        parts.append(f"сложность: {task['effort']}")
    if task.get("minutes"):
        parts.append(f"~{task['minutes']} мин")
    if task.get("risk"):
        parts.append(f"риск: {task['risk']}")
    return " | ".join(parts)


def normalize_tags(tags, subject=""):
    if tags is None:
        tags = [subject] if str(subject).strip() else []
    if isinstance(tags, str):
        tags = tags.split(",")
    return list(dict.fromkeys(
        str(tag).strip() for tag in tags if str(tag).strip()))
