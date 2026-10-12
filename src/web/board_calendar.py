import calendar
import datetime
import html

from ..education import timetable

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