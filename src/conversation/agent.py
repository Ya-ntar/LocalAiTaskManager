import json, os, datetime, urllib.request
import re
from ..infrastructure.config import API, MODEL, HISTORY_LIMIT, INSTR_DIR, WEEKDAYS
from ..planner import tasks, goals, schedule
from . import topics, tools, chats, textcheck
from ..education import timetable, subjects
from ..infrastructure.journal import log_change
from .textcheck import foreign
from .chats import record

def _read(name):
    with open(os.path.join(INSTR_DIR, name), encoding="utf-8") as f:
        return f.read().strip()

def commands():
    return json.loads(_read("commands.json"))

def expand(text):
    return commands().get(text, text)

def now_text():
    now = datetime.datetime.now()
    return f"{WEEKDAYS[now.weekday()]}, {now:%Y-%m-%d %H:%M}"

def context_block():
    return (f"Расписание: {schedule.schedule_text()}\n\n"
            f"Занятия (есть = факт, хочу = план):\n{timetable.view('', 2)}\n\n"
            f"Предметы:\n{subjects.show_subjects()}\n\n"
            f"Сейчас стоит спросить: {subjects.subject_to_ask() or 'никого срочного, спрашивать не нужно'}\n\n"
            f"Доска:\n{tasks.show_board()}\n\n"
            f"Дедлайны:\n{tasks.deadlines()}\n\n"
            f"Цели:\n{goals.show_goals()}\n\n"
            f"Открытые темы:\n{topics.list_topics()}")

def system_prompt():
    return _read("agent.txt").replace("{now}", now_text()) + "\n\n" + context_block()

def opening_text():
    active = [t for t in tasks.load_tasks() if t["column"] in ("Сегодня", "Входящие")]
    if not active:
        return _read("opening_empty")
    top = max(active, key=tasks.prio)
    return _read("opening_task.txt").replace("{title}", top["title"]).replace("{column}", top["column"])

def ask(messages):
    body = json.dumps({"model": MODEL, "messages": messages, "tools": tools.TOOLS,
                       "temperature": 0.4}).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["choices"][0]["message"]

def _write_requested(text):
    if not text:
        return False
    return bool(re.search(r"\b(добавь|добавить|запиши|записать|создай|создать|сохрани|сохранить|измени|изменить|удали|удалить)\b",
                         text.lower()))

def _write_succeeded(name, result):
    prefixes = {
        "add_task": "Добавлено:",
        "update_task": "Обновлено:",
        "edit_task": "Обновлено:",
        "delete_task": "Удалено:",
        "add_task_note": "Заметка добавлена",
        "link_tasks": "Задачи связаны:",
        "block_task": "Задача ",
        "unblock_task": "Блокировка снята:",
        "add_homework": "Записано по",
        "done_homework": "Отмечено выполненным:",
        "add_subject_note": "Заметка по",
        "add_timetable_items": "Добавлено",
        "add_goal": "Цель добавлена:",
        "open_topic": "Открыта новая тема:",
        "add_note": "Запись добавлена:",
        "close_topic": "Тема закрыта:",
        "reopen_topic": "Тема снова открыта:",
        "set_schedule": "Расписание сохранено:",
        "skip_timetable_item": "Пропуск записан:",
        "move_timetable_item": "Перенесено:",
        "remove_timetable_item": "Удалено из расписания:",
    }
    return str(result).startswith(prefixes.get(name, "\0"))

def run_turn(user_text, history, hint=""):
    """Считает ответ модели. История не меняется: запись делает chats.record()."""
    events = []
    messages = [{"role": "system", "content": system_prompt()}] + history[-HISTORY_LIMIT:]
    if hint:
        messages.append({"role": "system", "content": hint})
    if user_text:
        messages.append({"role": "user", "content": user_text})
    msg = ask(messages)
    if user_text and _write_requested(user_text) and not msg.get("tool_calls"):
        messages.append({"role": "assistant", "content": msg.get("content") or ""})
        messages.append({"role": "system", "content":
                         "Пользователь просит изменить данные. Не отвечай подтверждением словами. "
                         "Сначала обязательно вызови подходящий инструмент для каждой записи. "
                         "Если данных недостаточно, задай уточняющий вопрос."})
        msg = ask(messages)
    successful_writes = 0
    while msg.get("tool_calls"):
        messages.append(msg)
        for call in msg["tool_calls"]:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
                result = tools.FUNCS[name](**args)
                if name in tools.WRITE:
                    log_change(name, args, result)
                    if _write_succeeded(name, result):
                        successful_writes += 1
            except Exception as e:
                result = f"Ошибка: {e}"
            line = f"[{name}] {result}"
            print("  " + line)
            events.append(line)
            messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": str(result)})
        messages[0] = {"role": "system", "content": system_prompt()}
        msg = ask(messages)
    text = msg.get("content") or ""
    if user_text and _write_requested(user_text) and successful_writes == 0:
        text = ("Я не подтверждаю запись: в этом ответе не было успешного вызова "
                "инструмента. Повторите просьбу, и я сначала выполню запись, затем покажу результат.")
    if foreign(text):
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content":
                         "Ответь заново, полностью по-русски, без иероглифов и без пересказа инструкций."})
        msg = ask(messages)
        text = msg.get("content") or ""
        if foreign(text):
            text = "Ответ пришёл с ошибкой. Повторите, пожалуйста, вопрос."
    return text, events

def start_session(chat):
    text, events = run_turn(None, chat["messages"], hint=opening_text())
    record(chat, None, text)
    return text, events