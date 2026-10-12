import html
import os
import datetime
import calendar
from ..infrastructure.config import BOARD_PAGE, COLUMNS
from ..planner import schedule
from ..education import timetable

def write_board(tasks, item_text, sorted_items):
    os.makedirs(os.path.dirname(BOARD_PAGE), exist_ok=True)
    with open(BOARD_PAGE, "w", encoding="utf-8") as f:
        f.write(render_board(tasks, item_text, sorted_items))

def render_board(tasks, item_text, sorted_items):
    cols = render_columns(tasks, item_text, sorted_items)
    relations = render_relations(tasks)
    task_details = render_task_details(tasks)
    themes = render_themes(tasks, item_text)
    recurring = render_recurring()
    calendar = render_calendar()
    routine = html.escape(schedule.schedule_text())
    deadlines = render_deadline_calendar(tasks, item_text)
    return f"""<!doctype html><html lang='ru'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Планировщик</title>
<style>body{{font-family:system-ui,sans-serif;margin:0;padding:16px;background:#fafafa;color:#222}}
.nav{{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}} .nav button{{padding:8px 12px;border:1px solid #ccc;border-radius:7px;background:#fff;cursor:pointer}}
.nav button.active,.nav button:hover{{background:#2d6cdf;color:#fff;border-color:#2d6cdf}} .tab{{display:none}} .tab.active{{display:block}}
.board{{display:flex;gap:12px;align-items:flex-start;overflow-x:auto}} .col{{flex:1;min-width:220px;background:#eee;border-radius:8px;padding:8px}}
li{{list-style:none;background:#fff;margin:6px 0;padding:8px;border-radius:4px;box-shadow:0 1px 2px #ddd}}
ul{{padding:0;margin:0}} h1{{margin-top:0;font-size:22px}} h2{{font-size:18px}}
.text{{white-space:pre-wrap;background:#fff;border:1px solid #ddd;border-radius:8px;padding:12px;overflow:auto}}
.relations{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:12px;margin-bottom:14px}}
.relations form{{display:flex;flex-wrap:wrap;gap:8px;align-items:end}}
.relations label{{display:flex;flex-direction:column;gap:4px;font-size:13px}}
.relations select,.relations input{{min-width:220px;padding:7px;border:1px solid #bbb;border-radius:5px;background:#fff}}
.relation-buttons{{display:flex;flex-wrap:wrap;gap:6px}}
.relation-buttons button{{padding:7px 10px;border:1px solid #bbb;border-radius:5px;background:#f7f7f7;cursor:pointer}}
.relation-buttons button:hover{{background:#e8f0ff;border-color:#2d6cdf}}
.task-card{{display:block;width:100%;padding:0;border:0;background:transparent;text-align:left;font:inherit;color:inherit;cursor:pointer}}
.task-card:hover{{color:#2d6cdf}}
.modal{{position:fixed;inset:0;z-index:10;background:rgba(0,0,0,.4);padding:3vh 16px;overflow:auto}}
.modal-content{{position:relative;max-width:760px;min-height:82vh;max-height:92vh;overflow-y:auto;margin:auto;background:#fff;border-radius:10px;padding:24px;box-shadow:0 8px 30px #3338}}
.modal-close{{position:absolute;right:12px;top:12px;padding:6px 10px;border:1px solid #bbb;border-radius:5px;background:#fff;cursor:pointer}}
.task-details h2{{margin-top:0;padding-right:90px}} .task-details li{{box-shadow:none;border:1px solid #eee}}
#task-modal-body label{{display:flex;flex-direction:column;gap:5px;margin:10px 0;font-weight:600}}
#task-modal-body input,#task-modal-body select{{box-sizing:border-box;width:100%;max-width:560px;padding:9px;border:1px solid #bbb;border-radius:5px;font:inherit;font-weight:400}}
#task-modal-body>button,#task-modal-body p>button{{margin:6px 6px 6px 0;padding:8px 12px;border:1px solid #aaa;border-radius:5px;background:#fff;cursor:pointer}}
#task-modal-body>button:hover,#task-modal-body p>button:hover{{background:#e8f0ff;border-color:#2d6cdf}}
#task-modal-body hr{{margin:20px 0 10px;border:0;border-top:1px solid #ddd}}
.task-title{{cursor:pointer}} .task-title:hover{{text-decoration:underline;text-decoration-style:dashed}}
.column-heading{{display:flex;align-items:center;justify-content:space-between;gap:8px}}
.add-task-button{{width:28px;height:28px;border:1px solid #aaa;border-radius:50%;background:#fff;font-size:20px;line-height:20px;cursor:pointer}}
.add-task-button:hover{{background:#2d6cdf;color:#fff;border-color:#2d6cdf}}
.quick-add{{display:flex;flex-direction:column;gap:10px}} .quick-add input{{padding:8px;border:1px solid #bbb;border-radius:5px}}
.theme{{margin:0 0 14px}} .muted{{color:#777}}
.calendar-title{{margin-bottom:8px;text-transform:capitalize}}
.calendar{{background:#fff;border:1px solid #ddd;border-radius:8px;overflow:hidden}}
.weekdays,.days{{display:grid;grid-template-columns:repeat(7,minmax(110px,1fr))}}
.weekday{{padding:8px;text-align:center;font-weight:600;background:#eee;border-bottom:1px solid #ddd}}
.day{{min-height:110px;padding:6px;border-right:1px solid #eee;border-bottom:1px solid #eee}}
.day:nth-child(7n){{border-right:0}} .day-number{{font-weight:700;margin-bottom:5px}}
.day.outside{{background:#f5f5f5;color:#999}} .day.today{{outline:2px solid #2d6cdf;outline-offset:-2px}}
.event{{font-size:12px;background:#e8f0ff;border-radius:4px;padding:3px 4px;margin:3px 0;overflow-wrap:anywhere}}
.deadline{{background:#fff1d6}} .overdue{{background:#fff0f0}}</style>
</head><body><p><a href='/'>← Вернуться в планировщик</a></p><h1>Планировщик</h1>
<nav class='nav'>{''.join(f"<button data-tab='{tab}'>{label}</button>" for tab, label in (
    ("kanban", "Канбан"), ("themes", "По темам"), ("recurring", "Повторяемое"),
    ("calendar", "Расписание"), ("deadlines", "Дедлайны")))}</nav>
<section id='kanban' class='tab active'>{relations}{cols}</section>
<section id='themes' class='tab'>{themes}</section>
<section id='recurring' class='tab'>{recurring}</section>
<section id='calendar' class='tab'><div class='text'><strong>Режим и рутина</strong>\n{routine}</div>{calendar}</section>
<section id='deadlines' class='tab'>{deadlines}</section>
<script>
document.querySelectorAll('[data-tab]').forEach(button => button.onclick = () => {{
  document.querySelectorAll('.tab').forEach(tab => tab.classList.toggle('active', tab.id === button.dataset.tab));
  document.querySelectorAll('[data-tab]').forEach(item => item.classList.toggle('active', item === button));
}});
document.querySelector('[data-tab]').classList.add('active');
async function boardAction(action) {{
  const form = document.querySelector('#relation-form');
  const data = new FormData(form);
  const payload = {{action, task: data.get('task'), related_task: data.get('related_task'), text: data.get('text')}};
  const response = await fetch('/board/action', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(payload)
  }});
  const result = await response.json();
  if (!response.ok) {{ alert(result.error || 'Ошибка операции'); return; }}
  alert(result.result);
  location.reload();
}}
async function taskAction(action, task) {{
  const related = document.querySelector('#related-' + CSS.escape(task));
  const subtask = document.querySelector('#subtask-' + CSS.escape(task));
  const selected = related ? related.value : '';
  const text = subtask ? subtask.value : '';
  const title = document.querySelector('#title-' + CSS.escape(task));
  const importance = document.querySelector('#importance-' + CSS.escape(task));
  const minutes = document.querySelector('#minutes-' + CSS.escape(task));
  const tags = document.querySelector('#tags-' + CSS.escape(task));
  if (action === 'archive' && !confirm('Переместить задачу в архив?')) return;
  if (action === 'delete' && !confirm('Удалить задачу окончательно? Это действие нельзя отменить.')) return;
  if (action === 'subtask' && !text.trim()) {{ alert('Введите название подзадачи'); return; }}
  if (action === 'edit' && (!title.value.trim() || Number(importance.value) < 0 || Number(importance.value) > 1 || Number(minutes.value) < 0)) {{
    alert('Проверьте название, приоритет от 0 до 1 и длительность'); return;
  }}
  const response = await fetch('/board/action', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{action, task, related_task: selected, text,
      title: title ? title.value : null,
      importance: importance ? Number(importance.value) : null,
      minutes: minutes ? Number(minutes.value) : null,
      tags: tags ? tags.value.split(',').map(item => item.trim()).filter(Boolean) : null}})
  }});
  const result = await response.json();
  if (!response.ok) {{ alert(result.error || 'Ошибка операции'); return; }}
  alert(result.result);
  location.reload();
}}
function showTask(id) {{
  const source = document.querySelector('#task-details-' + CSS.escape(id));
  const body = document.querySelector('#task-modal-body');
  const modal = document.querySelector('#task-modal');
  if (!source || !body || !modal) return;
  body.innerHTML = source.innerHTML;
  modal.hidden = false;
}}
function editTitle(id) {{
  const title = document.querySelector('#task-modal .task-title') ||
    document.querySelector('#task-details-' + CSS.escape(id) + ' .task-title');
  if (!title || title.querySelector('input')) return;
  const input = document.createElement('input');
  input.value = title.textContent;
  input.className = 'inline-title';
  input.addEventListener('keydown', event => {{
    if (event.key === 'Enter') saveInlineTitle(id, input.value);
    if (event.key === 'Escape') showTask(id);
  }});
  input.addEventListener('blur', () => saveInlineTitle(id, input.value));
  title.replaceChildren(input);
  input.focus();
  input.select();
}}
async function saveInlineTitle(id, value) {{
  if (!value.trim()) return;
  await sendBoardAction({{action:'edit', task:id, title:value, importance:null, minutes:null, tags:null}});
}}
async function addTask(column) {{
  const title = prompt('Название новой задачи:');
  if (!title || !title.trim()) return;
  const tags = prompt('Темы/теги через запятую (необязательно):') || '';
  await sendBoardAction({{action:'add', column, title:title.trim(), tags:tags.split(',').map(item => item.trim()).filter(Boolean)}});
}}
async function sendBoardAction(payload) {{
  const response = await fetch('/board/action', {{
    method: 'POST', headers: {{'Content-Type':'application/json'}}, body: JSON.stringify(payload)
  }});
  const result = await response.json();
  if (!response.ok) {{ alert(result.error || 'Ошибка операции'); return; }}
  alert(result.result);
  location.reload();
}}
function closeTask() {{
  const modal = document.querySelector('#task-modal');
  if (modal) modal.hidden = true;
}}
document.addEventListener('DOMContentLoaded', () => {{
  const modal = document.querySelector('#task-modal');
  if (modal) modal.addEventListener('click', event => {{
    if (event.target.id === 'task-modal') closeTask();
  }});
}});
document.addEventListener('keydown', event => {{
  if (event.key === 'Escape') closeTask();
}});
</script>{task_details}</body></html>"""

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
            f"<li><button class='task-card' type='button' data-task-id='{html.escape(t['id'], quote=True)}' "
            f"onclick=\"showTask('{html.escape(t['id'], quote=True)}')\">"
            f"{html.escape(item_text(t))}</button></li>"
            for t in sorted_items(tasks, c)
        )
        cols += (
            f"<div class='col'><div class='column-heading'><h2>{c}</h2>"
            f"<button class='add-task-button' type='button' title='Добавить задачу в колонку "
            f"{html.escape(c, quote=True)}' onclick=\"addTask('{html.escape(c, quote=True)}')\">+</button>"
            f"</div><ul>{items}</ul></div>"
        )
    return f"<div class='board'>{cols}</div>"

def render_task_details(tasks):
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
            f"<label>Теги/темы <input id='tags-{html.escape(task['id'], quote=True)}' value='{html.escape(', '.join(task.get('tags', [])), quote=True)}' placeholder='через запятую'></label>"
            f"<button type='button' onclick=\"taskAction('edit','{html.escape(task['id'], quote=True)}')\">Сохранить изменения</button>"
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

def render_themes(tasks, item_text):
    groups = {}
    for task in tasks:
        tags = task.get("tags") or ([task["subject"]] if task.get("subject") else [])
        for tag in tags or ["Без темы"]:
            groups.setdefault(tag, []).append(task)
    if not groups:
        return "<p class='muted'>Задач нет.</p>"
    return "".join(
        f"<div class='theme'><h2>{html.escape(name)}</h2><ul>" +
        "".join(f"<li>{html.escape(item_text(task))}</li>" for task in sorted(items, key=item_text)) +
        "</ul></div>"
        for name, items in sorted(groups.items(), key=lambda pair: pair[0].lower())
    )

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

def render_calendar():
    today = datetime.date.today()
    month_names = (
        "", "январь", "февраль", "март", "апрель", "май", "июнь",
        "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
    )
    first = today.replace(day=1)
    grid_start = first - datetime.timedelta(days=first.weekday())
    last = calendar.monthrange(today.year, today.month)[1]
    grid_end = today.replace(day=last)
    grid_end += datetime.timedelta(days=6 - grid_end.weekday())
    cells = []
    day = grid_start
    while day <= grid_end:
        items = timetable.items_on(day)
        events = "".join(
            f"<div class='event'><strong>{html.escape(item.get('start', ''))}</strong> "
            f"{html.escape(item.get('title', ''))}</div>"
            for item in items
        )
        classes = ["day"]
        if day.month != today.month:
            classes.append("outside")
        if day == today:
            classes.append("today")
        event_markup = events or "<span class='muted'>—</span>"
        cells.append(
            f"<div class='{' '.join(classes)}'><div class='day-number'>{day.day}</div>"
            f"{event_markup}</div>"
        )
        day += datetime.timedelta(days=1)
    weekdays = "".join(f"<div class='weekday'>{name}</div>" for name in (
        "Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"))
    return (
        f"<h2 class='calendar-title'>{month_names[today.month]} "
        f"{today.year}</h2><div class='calendar'><div class='weekdays'>{weekdays}</div>"
        f"<div class='days'>{''.join(cells)}</div></div>"
    )

def render_deadlines(tasks, item_text):
    dated = [task for task in tasks
             if task.get("due") and task.get("column") not in ("Готово", "Архив")]
    dated.sort(key=lambda task: task["due"])
    if not dated:
        return "<p class='muted'>Активных дедлайнов нет.</p>"
    return "<ul>" + "".join(
        f"<li><strong>{html.escape(task['due'])}</strong> — {html.escape(item_text(task))}</li>"
        for task in dated
    ) + "</ul>"

def render_deadline_calendar(tasks, item_text):
    today = datetime.date.today()
    month_names = (
        "", "январь", "февраль", "март", "апрель", "май", "июнь",
        "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
    )
    grouped = {}
    for task in tasks:
        if task.get("column") in ("Готово", "Архив") or not task.get("due"):
            continue
        try:
            due = datetime.date.fromisoformat(task["due"])
        except (TypeError, ValueError):
            continue
        grouped.setdefault(due, []).append(task)

    first = today.replace(day=1)
    grid_start = first - datetime.timedelta(days=first.weekday())
    last = calendar.monthrange(today.year, today.month)[1]
    grid_end = today.replace(day=last)
    grid_end += datetime.timedelta(days=6 - grid_end.weekday())
    cells = []
    day = grid_start
    while day <= grid_end:
        classes = ["day"]
        if day.month != today.month:
            classes.append("outside")
        if day == today:
            classes.append("today")
        if day < today and day in grouped:
            classes.append("overdue")
        items = "".join(
            f"<div class='event deadline'><strong>{html.escape(task.get('title', ''))}</strong>"
            f"<br><span>{html.escape(item_text(task))}</span></div>"
            for task in grouped.get(day, [])
        )
        event_markup = items or "<span class='muted'>—</span>"
        cells.append(
            f"<div class='{' '.join(classes)}'><div class='day-number'>{day.day}</div>"
            f"{event_markup}</div>"
        )
        day += datetime.timedelta(days=1)
    weekdays = "".join(f"<div class='weekday'>{name}</div>" for name in (
        "Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"))
    return (
        f"<h2 class='calendar-title'>{month_names[today.month]} {today.year}</h2>"
        f"<div class='calendar'><div class='weekdays'>{weekdays}</div>"
        f"<div class='days'>{''.join(cells)}</div></div>"
    )