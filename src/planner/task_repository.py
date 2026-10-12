import uuid

from ..infrastructure import store


def load_tasks():
    tasks = store.load("tasks")
    changed = False
    used = set()
    for task in tasks:
        if not task.get("id") or task["id"] in used:
            task["id"] = uuid.uuid4().hex[:8]
            changed = True
        used.add(task["id"])
        for field in ("notes", "related_ids", "blocked_by"):
            if not isinstance(task.get(field), list):
                task[field] = []
                changed = True
        if "parent_id" not in task:
            task["parent_id"] = ""
            changed = True
        if not isinstance(task.get("tags"), list):
            task["tags"] = [task["subject"]] if task.get("subject") else []
            changed = True
    if changed:
        store.save("tasks", tasks)
    return tasks


def save_tasks(tasks):
    store.save("tasks", tasks)
