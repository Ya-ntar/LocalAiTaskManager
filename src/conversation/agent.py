import json, os, datetime, urllib.request
import re
from ..infrastructure.config import (API, MODEL, HISTORY_LIMIT, INSTR_DIR, WEEKDAYS,
                                     PROMPT_CHAR_LIMIT)
from ..planner import tasks, goals, schedule, themes
from . import topics, tools, chats, textcheck
from ..education import timetable, subjects
from ..infrastructure.journal import log_change
from .textcheck import foreign
from .chats import record

TASK_ID_RE = re.compile(r"\b[a-f0-9]{8}\b", re.IGNORECASE)

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
    pending = chats.current_chat().get("pending_plan")
    plan_text = f"\n\nОжидающий план изменений:\n{json.dumps(pending, ensure_ascii=False)}" if pending else ""
    context = (f"Расписание: {schedule.schedule_text()}\n\n"
            f"Занятия (есть = факт, хочу = план):\n{timetable.view('', 7)}\n\n"
            f"Предметы:\n{subjects.show_subjects()}\n\n"
            f"Сейчас стоит спросить: {subjects.subject_to_ask() or 'никого срочного, спрашивать не нужно'}\n\n"
            f"Доска:\n{tasks.show_board()}\n\n"
            f"Дедлайны:\n{tasks.deadlines()}\n\n"
            f"Цели:\n{goals.show_goals()}\n\n"
            f"Открытые темы:\n{topics.list_topics()}{plan_text}")
    # Keep the live state compact enough for 8K-context local models.
    return context[:10000]


def _bounded_messages(messages):
    """Trim old conversation content while keeping the current request intact."""
    limit = PROMPT_CHAR_LIMIT
    total = sum(len(str(item.get("content") or "")) for item in messages)
    if total <= limit:
        return messages
    current = messages[-1:] if messages and messages[-1].get("role") != "system" else []
    system = [item for item in messages if item.get("role") == "system"]
    middle = [item for item in messages if item.get("role") != "system" and item is not messages[-1]]
    current_size = sum(len(str(item.get("content") or "")) for item in current)
    remaining = max(0, limit - current_size)
    result = []
    for item in system:
        content = str(item.get("content") or "")
        if remaining <= 0:
            break
        if len(content) <= remaining:
            result.append(item)
            remaining -= len(content)
        else:
            result.append(dict(item, content=content[:remaining]))
            remaining = 0
            break
    result += current
    for item in reversed(middle):
        content = str(item.get("content") or "")
        if len(content) <= remaining:
            result.insert(len(system), item)
            remaining -= len(content)
        elif remaining > 200:
            result.insert(len(system), dict(item, content=content[-remaining:]))
            break
    return result

def system_prompt():
    return _read("agent.txt").replace("{now}", now_text()) + "\n\n" + context_block()

def _execution_context(chat):
    task_ids = chat.get("referenced_task_ids", [])
    if not task_ids:
        return ""
    selected = [task for task in tasks.load_tasks() if task.get("id") in task_ids]
    lines = [
        "Внутренний контекст для исполнения (не пересказывай его пользователю):",
        _read("task_analyzer.txt"),
        "Последние явно определённые задачи:"
    ]
    lines.extend(
        f"- id {task['id']}: {task['title']} | теги: {', '.join(task.get('tags', [])) or 'нет'}"
        for task in selected
    )
    lines.append("Если пользователь ссылается на «них/им/эти задачи», используй только эти id.")
    return "\n".join(lines)

def opening_text():
    active = [t for t in tasks.load_tasks() if t["column"] in ("Сегодня", "Входящие")]
    if not active:
        return _read("opening_empty")
    top = max(active, key=tasks.prio)
    return _read("opening_task.txt").replace("{title}", top["title"]).replace("{column}", top["column"])

def ask(messages):
    body = json.dumps({"model": MODEL, "messages": _bounded_messages(messages), "tools": tools.TOOLS,
                       "temperature": 0.4}).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["choices"][0]["message"]

def _write_requested(text):
    if not text:
        return False
    return bool(re.search(r"(добавь|добавить|запиши|записать|создай|создать|сохрани|сохранить|измени|изменить|удали|удалить|отмени|отменить|архивируй|архивировать|примени|применить|подтверди|подтверждаю|выполни|выполнить)",
                         text.lower()))

def _explicit_task_ids(text):
    return list(dict.fromkeys(TASK_ID_RE.findall(text or "")))

def _deletion_requested(text):
    return bool(re.search(r"(удал|отмен)", text or "", re.IGNORECASE))

def _explicit_deletion_ids(text):
    """Extract only IDs from an explicitly named deletion section."""
    text = text or ""
    markers = (
        r"(?:теперь\s+удаляю\s+дубликаты|удалить\s+следующие\s+задачи|"
        r"удаляемые\s+задачи|план\s+удаления|удаление\s+задач)\s*:?"
    )
    matches = list(re.finditer(markers, text, re.IGNORECASE))
    if not matches:
        return []
    section = text[matches[-1].end():]
    boundary = re.search(
        r"\n\s*(?:я\s+одобряю|подтверждаю|да[, ]|план\s+одобрен|"
        r"удаление\s+завершено|хотите\s+продолжить)",
        section, re.IGNORECASE)
    if boundary:
        section = section[:boundary.start()]
    return _explicit_task_ids(section)

def _confirmation(text):
    return bool(re.fullmatch(
        r"\s*(?:да\s*[,!.]?\s*)?(подтверждаю(?:\s+план)?|применяй|применить|"
        r"выполняй|выполни|удали(?:\s+их|\s+по\s+названным\s+айди)?)\s*[.!]*\s*|"
        r"\s*да\s*[.!]?\s*(?:удали|удаляй)(?:\s+их)?\s*[.!]*\s*",
        text or "", re.IGNORECASE))

def _deletion_ids_from_history(history):
    for message in reversed(history or []):
        if message.get("role") != "assistant":
            continue
        content = message.get("content") or ""
        match = re.search(
            r"(?:план удаления|удаляемые задачи|удалим\s*:|удаление задач)\s*:?(.*)",
            content, re.IGNORECASE | re.DOTALL)
        if match:
            section = match.group(1)
            boundary = re.search(
                r"\n\s*(?:вы согласны|хотите продолжить|подтверждаю|да\s*[.!])",
                section, re.IGNORECASE)
            if boundary:
                section = section[:boundary.start()]
            ids = _explicit_task_ids(section)
            if ids:
                return ids
    return []


def _task_title_key(title):
    return re.sub(r"\s+", " ", (title or "")).strip().lower()


def _duplicate_groups_for_tasks(task_list):
    groups = {}
    for task in task_list:
        key = _task_title_key(task.get("title") or "")
        if not key:
            continue
        groups.setdefault(key, []).append(task)
    return {key: group for key, group in groups.items() if len(group) > 1}

def _theme_mentions(text):
    lowered = (text or "").casefold()
    return [
        name for name in themes.load()
        if name != themes.DEFAULT_THEME and name.casefold() in lowered
    ]

def _tasks_mentioned(text):
    task_list = tasks.load_tasks()
    lowered = (text or "").casefold()
    ids = _explicit_task_ids(text)
    ids.extend(
        task["id"] for task in sorted(
            task_list, key=lambda item: len(item.get("title", "")), reverse=True
        )
        if task.get("title", "").casefold() in lowered
    )
    return list(dict.fromkeys(task_id for task_id in ids
                             if any(item.get("id") == task_id for item in task_list)))

def _remember_references(user_text, chat):
    task_ids = _tasks_mentioned(user_text)
    mentioned_themes = _theme_mentions(user_text)
    if not task_ids:
        for name in mentioned_themes:
            task_ids.extend(
                task["id"] for task in tasks.load_tasks()
                if any(str(tag).casefold() == name.casefold()
                       for tag in task.get("tags", []))
            )
    if task_ids or mentioned_themes:
        chats.set_references(chat, task_ids or None, mentioned_themes or None)
    return task_ids or list(chat.get("referenced_task_ids", []))

def _requested_tags(text):
    text = (text or "").strip()
    known = _theme_mentions(text)
    lowered = text.casefold()
    for marker in ("в тему", "в темы", "в тег", "в теги", "в задачи",
                   "тег", "теги", "тему"):
        position = lowered.rfind(marker)
        if position >= 0:
            tail = text[position + len(marker):].strip(" \t:,.!?")
            if tail:
                known.append(tail)
                break
    result = []
    for tag in known:
        normalized = " ".join(str(tag).split()).strip(" ,.!?")
        if normalized and normalized.casefold() not in {item.casefold() for item in result}:
            result.append(normalized)
    return result

def _handle_tag_request(user_text, chat):
    if not re.search(r"(добавь|добавить|присоедини|прикрепи)", user_text or "", re.IGNORECASE):
        return None
    if not re.search(r"(тег|теги|тему|темы)", user_text or "", re.IGNORECASE):
        return None
    task_ids = _remember_references(user_text, chat)
    source_match = re.search(r"из\s+(.+?)(?:\s+в\s+|\s*$)", user_text, re.IGNORECASE)
    if source_match:
        source_text = source_match.group(1).casefold()
        for name in themes.load():
            if name != themes.DEFAULT_THEME and name.casefold() in source_text:
                task_ids = [
                    task["id"] for task in tasks.load_tasks()
                    if any(str(tag).casefold() == name.casefold()
                           for tag in task.get("tags", []))
                ]
                break
    tags = _requested_tags(user_text)
    if not task_ids or not tags:
        return None
    for tag in tags:
        if tag.casefold() != themes.DEFAULT_THEME.casefold():
            themes.add(tag)
    result = tools.FUNCS["add_task_tags"](task_ids=task_ids, tags=tags)
    if not str(result).startswith("{"):
        return f"Не удалось добавить теги: {result}", []
    payload = json.loads(result)
    log_change("add_task_tags", {"task_ids": task_ids, "tags": tags}, result)
    names = ", ".join(item["title"] for item in payload["updated"])
    return f"Добавлены теги «{', '.join(tags)}» к задачам: {names}", [
        f"[add_task_tags] {result}"
    ]

def _handle_duplicate_analysis(user_text, chat):
    if not re.search(
        r"(дубликат|дубли|сгруппируй|сравни|"
        r"найди.*дублик|посмотри.*дублик|повторяющ(?:иеся|ихся)\s+задач)",
        user_text,
        re.IGNORECASE,
    ):
        return None
    task_list = tasks.load_tasks()
    groups = _duplicate_groups_for_tasks(task_list)
    if not groups:
        return "По совпадению названия дубликатов не найдено.", []
    operations = []
    summary_lines = ["Найдены дубликаты по совпадению названия:"]
    for index, (_, group) in enumerate(sorted(groups.items()), 1):
        keep = min(group, key=lambda item: (item.get("column") or "", item.get("touched") or "", item.get("id") or ""))
        delete_ids = [item["id"] for item in group if item["id"] != keep["id"]]
        summary_lines.append(f"{index}. {keep['title']} — сохранить id {keep['id']}; удалить {', '.join(delete_ids) or '—'}")
        for task_id in delete_ids:
            operations.append({
                "action": "delete",
                "task_id": task_id,
                "reason": f"Дубликат названия: {keep['title']}"
            })
    if not operations:
        return "По совпадению названия дубликатов не найдено.", []
    preview = tools.FUNCS["propose_task_changes"](operations)
    if not str(preview).startswith("{"):
        return f"Не удалось сформировать план удаления: {preview}", []
    payload = json.loads(preview)
    chats.set_pending_plan(chat, payload)
    summary = "\n".join(summary_lines) + "\n\nПодтвердите удаление этих дубликатов."
    return summary, [f"[propose_task_changes] {preview}"]

def _handle_due_from_next_class(user_text, history=()):
    lowered = (user_text or "").casefold()
    if not all(word in lowered for word in ("дедлайн", "задач")):
        return None
    if "заняти" not in lowered:
        return None
    if "следующ" not in lowered and "когда" not in lowered:
        return None
    candidates = [task for task in tasks.load_tasks()
                  if "проверить наличие домашки" in task.get("title", "").casefold()]
    history_text = " ".join(str(item.get("content") or "")
                            for item in history if isinstance(item, dict))
    mentioned = [task for task in candidates if task.get("title", "") in history_text]
    if mentioned:
        candidates = mentioned
    if len(candidates) != 1:
        return None
    task = candidates[0]
    subject = (task.get("subject") or "").casefold()
    if not subject:
        return None
    day = tasks.today()
    occurrence = None
    for offset in range(0, 366):
        current = day + datetime.timedelta(days=offset)
        matching = [item for item in timetable.items_on(current)
                    if subject in item.get("title", "").casefold()]
        if matching:
            occurrence = current
            break
    if occurrence is None:
        return "Не удалось найти ближайшее занятие для предмета «%s»." % task["subject"], []
    due = occurrence.isoformat()
    result = tools.FUNCS["set_task_due"](task_id=task["id"], due=due)
    if not str(result).startswith("Обновлено:"):
        return f"Не удалось установить дедлайн: {result}", []
    log_change("set_task_due", {"task_id": task["id"], "due": due}, result)
    return (f"Дедлайн задачи «{task['title']}» установлен на {due} "
            f"по ближайшему занятию «{subject}».", [f"[set_task_due] {result}"])

def _apply_saved_plan(chat, history):
    pending = chat.get("pending_plan")
    if not pending:
        ids = _deletion_ids_from_history(history)
        if ids:
            pending = {
                "operations": [
                    {"action": "delete", "task_id": task_id,
                     "reason": "Подтверждён ранее показанный план удаления"}
                    for task_id in ids
                ]
            }
    if not pending or not pending.get("operations"):
        return None
    operations = pending["operations"]
    result = tools.FUNCS["apply_task_changes"](operations)
    if not str(result).startswith("{"):
        return f"Не удалось применить план: {result}", []
    chats.set_pending_plan(chat, None)
    log_change("apply_task_changes", {"operations": operations}, result)
    return "План применён. Изменено операций: " + str(json.loads(result).get("count", 0)), [
        f"[apply_task_changes] {result}"
    ]

def _write_succeeded(name, result):
    prefixes = {
        "add_task": "Добавлено:",
        "add_task_tags": "{\"updated\":",
        "update_task": "Обновлено:",
        "set_task_due": "Обновлено:",
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
        "apply_task_changes": "{\"applied\":",
    }
    return str(result).startswith(prefixes.get(name, "\0"))

def run_turn(user_text, history, hint=""):
    """Считает ответ модели. История не меняется: запись делает chats.record()."""
    events = []
    chat = chats.current_chat()
    if user_text and _confirmation(user_text):
        applied = _apply_saved_plan(chat, history)
        if applied:
            return applied
    if user_text:
        _remember_references(user_text, chat)
        due_result = _handle_due_from_next_class(user_text, history)
        if due_result is not None:
            return due_result
        duplicate_summary = _handle_duplicate_analysis(user_text, chat)
        if duplicate_summary is not None:
            return duplicate_summary
        tag_result = _handle_tag_request(user_text, chat)
        if tag_result is not None:
            return tag_result
    explicit_ids = _explicit_deletion_ids(user_text)
    if not explicit_ids and user_text and _deletion_requested(user_text):
        explicit_ids = _explicit_task_ids(user_text)
    if user_text and explicit_ids and _deletion_requested(user_text):
        operations = [{"action": "delete", "task_id": task_id, "reason": "Явно указано пользователем"}
                      for task_id in explicit_ids]
        result = tools.FUNCS["apply_task_changes"](operations)
        if str(result).startswith("{"):
            log_change("apply_task_changes", {"operations": operations}, result)
            return "Удалены указанные задачи. Операций: " + str(json.loads(result).get("count", 0)), [
                f"[apply_task_changes] {result}"
            ]
    messages = [{"role": "system", "content": system_prompt()}]
    execution_context = _execution_context(chat)
    if execution_context:
        messages.append({"role": "system", "content": execution_context})
    messages.extend(history[-HISTORY_LIMIT:])
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
                if name == "apply_task_changes":
                    pending = chats.current_chat().get("pending_plan")
                    if not pending:
                        raise ValueError("Нет ожидающего плана изменений. Сначала подготовьте preview.")
                    if args.get("operations") != pending.get("operations"):
                        raise ValueError("Операции не совпадают с последним показанным планом.")
                result = tools.FUNCS[name](**args)
                if name == "propose_task_changes" and str(result).startswith("{"):
                    chats.set_pending_plan(chats.current_chat(), json.loads(result))
                    successful_writes += 1
                elif name == "apply_task_changes" and str(result).startswith("{"):
                    chats.set_pending_plan(chats.current_chat(), None)
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
