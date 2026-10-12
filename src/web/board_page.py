import html
import os
from ..infrastructure.config import BOARD_PAGE, COLUMNS
from ..planner import schedule, themes as theme_model
from ..education import timetable
from .board_calendar import render_calendar, render_deadline_calendar

DRAG_COLUMNS = {"Входящие", "В процессе", "Готово"}

def write_board(tasks, item_text, sorted_items):
    os.makedirs(os.path.dirname(BOARD_PAGE), exist_ok=True)
    with open(BOARD_PAGE, "w", encoding="utf-8") as f:
        f.write(render_board(tasks, item_text, sorted_items))

def render_board(tasks, item_text, sorted_items):
    theme_names = theme_model.load(tasks)
    cols = render_columns(tasks, item_text, sorted_items)
    relations = render_relations(tasks)
    task_details = render_task_details(tasks, theme_names)
    themes = render_themes(tasks, item_text, theme_names)
    recurring = render_recurring()
    calendar = render_calendar()
    routine = html.escape(schedule.schedule_text())
    deadlines = render_deadline_calendar(tasks, item_text)
    return f"""<!doctype html><html lang='ru'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Планировщик</title>
<link rel='stylesheet' href='/board.css'>
</head><body><p><a href='/'>← Вернуться в планировщик</a></p><h1>Планировщик</h1>
<nav class='nav'>{''.join(f"<button data-tab='{tab}'>{label}</button>" for tab, label in (
    ("kanban", "Канбан"), ("themes", "По темам"), ("recurring", "Повторяемое"),
    ("calendar", "Расписание"), ("deadlines", "Дедлайны")))}</nav>
<section id='kanban' class='tab active'>{relations}{cols}</section>
<section id='themes' class='tab'>{themes}</section>
<section id='recurring' class='tab'>{recurring}</section>
<section id='calendar' class='tab'><div class='text'><strong>Режим и рутина</strong>\n{routine}</div>{calendar}</section>
<section id='deadlines' class='tab'>{deadlines}</section>
<script src='/board.js'></script>{render_task_creator(theme_names)}{task_details}</body></html>"""

def render_relations(tasks):
    if not tasks:
        return ""
    options = "".join(
        f"<option value='{html.escape(task['id'], quote=True)}'>"
        f"{html.escape(task['title'])} [{html.escape(task['id'])}]</option>"
        for task in sorted(tasks, key=lambda item: item["title"].lower())
    )
    return f"""<section class='relations'>
<h2>Связи и заметки</h2>
<p class='muted'>Эти действия выполняются напрямую и не обращаются к ИИ-агенту.</p>
<form id='relation-form' onsubmit='return false'>
<label>Задача <select name='task'>{options}</select></label>
<label>Связанная или блокирующая задача <select name='related_task'>{options}</select></label>
<label>Заметка <input name='text' type='text' placeholder='Текст заметки'></label>
<div class='relation-buttons'>
<button type='button' onclick="boardAction('link')">Связать</button>
<button type='button' onclick="boardAction('block')">Заблокировать</button>
<button type='button' onclick="boardAction('unblock')">Снять блокировку</button>
<button type='button' onclick="boardAction('note')">Добавить заметку</button>
</div></form></section>"""

def render_columns(tasks, item_text, sorted_items):
    cols = ""
    for c in COLUMNS:
        items = "".join(
            f"<li class='task-item' draggable='true' data-task-id='{html.escape(t['id'], quote=True)}' "
            f"data-column='{html.escape(c, quote=True)}'><button class='task-card' type='button' "
            f"onclick=\"showTask('{html.escape(t['id'], quote=True)}')\">"
            f"{html.escape(item_text(t))}</button></li>"
            for t in sorted_items(tasks, c)
        )
        drop_attribute = (
            f" data-drop-column='{html.escape(c, quote=True)}'"
            if c in DRAG_COLUMNS else ""
        )
        cols += (
            f"<div class='col'{drop_attribute}><div class='column-heading'><h2>{c}</h2>"
            f"<button class='add-task-button' type='button' title='Добавить задачу в колонку "
            f"{html.escape(c, quote=True)}' onclick=\"addTask('{html.escape(c, quote=True)}')\">+</button>"
            f"</div><ul>{items}</ul></div>"
        )
    return f"<div class='board'>{cols}</div>"

def render_theme_picker(task_id, selected, theme_names):
    options = "".join(
        f"<label><input type='checkbox' value='{html.escape(name, quote=True)}'"
        f"{' checked' if (name in selected or (name == theme_model.DEFAULT_THEME and not selected)) else ''}>"
        f"{html.escape(name)}</label>"
        for name in theme_names
    )
    return (
        f"<div class='theme-picker' id='theme-picker-{html.escape(task_id, quote=True)}'>"
        "<input class='theme-search' type='search' placeholder='Поиск темы'>"
        f"<div class='theme-options'>{options or '<span class=\"muted\">Тем пока нет</span>'}</div></div>"
    )


def render_task_details(tasks, theme_names):
    by_id = {task["id"]: task for task in tasks}
    blocks = []
    for task in tasks:
        options = "".join(
            f"<option value='{html.escape(item['id'], quote=True)}'>{html.escape(item['title'])} [{html.escape(item['id'])}]</option>"
            for item in tasks if item["id"] != task["id"] and item.get("column") != "Архив"
        )
        children = [item for item in tasks if item.get("parent_id") == task["id"]]
        related = [by_id[item] for item in task.get("related_ids", []) if item in by_id]
        blockers = [by_id[item] for item in task.get("blocked_by", []) if item in by_id]
        rows = [f"<h2 class='task-title' ondblclick=\"editTitle('{html.escape(task['id'], quote=True)}')\">"
                f"{html.escape(task['title'])}</h2>",
                f"<p class='muted'>ID: {html.escape(task['id'])}</p>",
                f"<p>{html.escape(task['column'])}</p>"]
        if children:
            rows.append("<h3>Подтаски</h3><ul>" + "".join(
                f"<li>{html.escape(item['title'])}</li>" for item in children) + "</ul>")
        if task.get("notes"):
            rows.append("<h3>Заметки</h3><ul>" + "".join(
                f"<li>{html.escape(note.get('text', ''))}</li>" for note in task["notes"]) + "</ul>")
        if related:
            rows.append("<h3>Связанные задачи</h3><ul>" + "".join(
                f"<li>{html.escape(item['title'])}</li>" for item in related) + "</ul>")
        if blockers:
            rows.append("<h3>Блокируется задачами</h3><ul>" + "".join(
                f"<li>{html.escape(item['title'])}</li>" for item in blockers) + "</ul>")
        rows.append(
            "<hr><h3>Действия</h3>"
            f"<label>Название <input id='title-{html.escape(task['id'], quote=True)}' value='{html.escape(task['title'], quote=True)}'></label>"
            f"<label>Приоритет <input id='importance-{html.escape(task['id'], quote=True)}' type='number' min='0' max='1' step='0.05' value='{task.get('importance', 0.5)}'></label>"
            f"<label>Минуты <input id='minutes-{html.escape(task['id'], quote=True)}' type='number' min='0' step='5' value='{int(task.get('minutes') or 0)}'></label>"
            "<label>Темы</label>"
            + render_theme_picker(task["id"], task.get("tags", []), theme_names)
            + f"<button type='button' onclick=\"taskAction('edit','{html.escape(task['id'], quote=True)}')\">Сохранить изменения</button>"
            f"<label>Связать с задачей <select id='related-{html.escape(task['id'], quote=True)}'>{options}</select></label> "
            f"<button type='button' onclick=\"taskAction('link','{html.escape(task['id'], quote=True)}')\">Связать</button> "
            f"<button type='button' onclick=\"taskAction('block','{html.escape(task['id'], quote=True)}')\">Сделать блокирующей</button>"
            f"<p><input id='subtask-{html.escape(task['id'], quote=True)}' placeholder='Название подзадачи'> "
            f"<button type='button' onclick=\"taskAction('subtask','{html.escape(task['id'], quote=True)}')\">Добавить подзадачу</button></p>"
            + (f"<button type='button' class='archive-button' onclick=\"taskAction('archive','{html.escape(task['id'], quote=True)}')\">Переместить в архив</button>"
               if task.get("column") != "Архив" else "")
            + (f" <button type='button' class='delete-button' onclick=\"taskAction('delete','{html.escape(task['id'], quote=True)}')\">Удалить окончательно</button>"
               if task.get("column") == "Архив" else "")
        )
        blocks.append(
            f"<div class='task-details' id='task-details-{html.escape(task['id'], quote=True)}'>"
            + "".join(rows) + "</div>"
        )
    return (
        "<div id='task-modal' class='modal' hidden><div class='modal-content'>"
        "<button class='modal-close' type='button' onclick='closeTask()'>Закрыть</button>"
        "<div id='task-modal-body'></div></div></div>"
        "<div id='task-details-store' hidden>" + "".join(blocks) + "</div>"
    )

def render_theme_tasks(tasks, item_text, theme_name):
    if theme_name == theme_model.DEFAULT_THEME:
        selected = [task for task in tasks if not task.get("tags")]
    else:
        selected = [task for task in tasks if theme_name in task.get("tags", [])]
    if not selected:
        return "<p class='muted'>Для этой темы задач нет.</p>"
    return "<ul>" + "".join(
        f"<li><button class='task-card' type='button' onclick=\"showTask('{html.escape(task['id'], quote=True)}')\">"
        f"{html.escape(item_text(task))}</button></li>"
        for task in sorted(selected, key=item_text)
    ) + "</ul>"


def render_themes(tasks, item_text, theme_names):
    def rename_control(name):
        if name == theme_model.DEFAULT_THEME:
            return ""
        return "<span class='theme-rename' title='Переименовать'>✎</span>"

    items = "".join(
        f"<button class='theme-list-item' type='button' data-theme='{html.escape(name, quote=True)}'>"
        f"<span>{html.escape(name)}</span>"
        f"{rename_control(name)}</button>"
        for name in theme_names
    )
    panels = "".join(
        f"<div class='theme-task-panel' data-theme-panel='{html.escape(name, quote=True)}' hidden>"
        f"<h2>{html.escape(name)}</h2>{render_theme_tasks(tasks, item_text, name)}</div>"
        for name in theme_names
    )
    empty = "<p class='muted'>Тем пока нет.</p>" if not theme_names else ""
    return f"""<div class='themes-layout'>
<aside class='themes-sidebar'><div class='theme-sidebar-heading'><h2>Темы</h2>
<button type='button' class='add-theme-button' onclick='addTheme()'>+</button></div>
<input id='theme-search' type='search' placeholder='Поиск тем'>
<div id='theme-list'>{items}</div>{empty}</aside>
<div id='theme-tasks' class='themes-content'>{panels}
<p id='theme-task-empty' class='muted'>Выберите тему слева.</p></div></div>"""


def render_task_creator(theme_names):
    options = "".join(
        f"<label><input type='checkbox' value='{html.escape(name, quote=True)}'>{html.escape(name)}</label>"
        for name in theme_names
    )
    return f"""<div id='task-create-modal' class='modal' hidden><div class='modal-content'>
<button class='modal-close' type='button' onclick='closeTaskCreator()'>Закрыть</button>
<h2>Новая задача</h2>
<label>Название <input id='new-task-title'></label>
<label>Темы</label>
<div id='new-task-themes' class='theme-picker'><input class='theme-search' type='search' placeholder='Поиск темы'>
<div class='theme-options'>{options or '<span class="muted">Сначала добавьте тему</span>'}</div></div>
<button type='button' onclick='saveNewTask()'>Добавить задачу</button>
</div></div>"""

def render_recurring():
    items = [item for item in timetable._load() if not item.get("date") and item.get("anchor")]
    if not items:
        return "<p class='muted'>Повторяющихся событий нет.</p>"
    rows = []
    for item in items:
        days = ", ".join(timetable.DAY_NAMES[d] for d in item.get("weekdays", []))
        repeat = f"каждые {item.get('every_days', 7)} дн."
        if days:
            repeat += f"; дни: {days}"
        until = f"; до {item['until']}" if item.get("until") else ""
        rows.append(f"<li><strong>{html.escape(item.get('title', 'Без названия'))}</strong> — "
                    f"{html.escape(item.get('start', ''))}, {html.escape(repeat + until)}</li>")
    return "<ul>" + "".join(rows) + "</ul>"
