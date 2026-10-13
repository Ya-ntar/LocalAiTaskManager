from ..infrastructure.config import COLUMNS, EFFORTS, HORIZONS
from ..planner import tasks, goals, schedule, themes
from . import topics
from ..education import timetable, subjects

def fn(name, desc, props, required=()):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": list(required)}}}

TOOLS = [
    fn("query_tasks", "Найти задачи по структурированным фильтрам. Используй перед групповым анализом или изменением.", {
        "filters": {"type": "object", "properties": {
            "id": {"type": "string"}, "title_contains": {"type": "string"},
            "subject": {"type": "string"}, "column": {"type": "string", "enum": COLUMNS},
            "tag": {"type": "string"}, "due_before": {"type": "string"},
            "due_after": {"type": "string"}}}}),
    fn("propose_task_changes", "Проверить и показать план массовых изменений без применения. Всегда используй для групповых или неоднозначных изменений.", {
        "operations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["delete", "archive", "move", "update", "link", "block", "unblock"]},
                    "task_id": {"type": "string"},
                    "other_task_id": {"type": "string"},
                    "column": {"type": "string", "enum": COLUMNS},
                    "changes": {"type": "object"},
                    "reason": {"type": "string"}
                },
                "required": ["action", "task_id"]
            }
        }
    }, ["operations"]),
    fn("apply_task_changes", "Применить ранее показанный и подтверждённый пользователем план по точным ID. Не выдумывай операции заново.", {
        "operations": {"type": "array", "items": {"type": "object"}}}, ["operations"]),
    fn("show_board", "Показать все задачи по колонкам", {}),
    fn("list_themes", "Показать все темы-теги, включая темы без задач", {}),
    fn("add_theme", "Создать тему-тег. Тема создаётся независимо от задач и может пока быть пустой.", {
        "name": {"type": "string"}}, ["name"]),
    fn("rename_theme", "Переименовать тему-тег у всех связанных задач.", {
        "old_name": {"type": "string"},
        "new_name": {"type": "string"}}, ["old_name", "new_name"]),
    fn("delete_theme", "Удалить тему-тег и снять её у всех задач. Сами задачи не удаляются.", {
        "name": {"type": "string"}}, ["name"]),
    fn("task_details", "Показать задачу, ее подтаски, заметки, связи и блокировки", {
        "task": {"type": "string"}}, ["task"]),
    fn("deadlines", "Показать дедлайны, что горит и общий объём работы", {}),
    fn("show_goals", "Показать все цели", {}),
    fn("show_schedule", "Показать сон и рутину пользователя", {}),
    fn("show_subjects", "Показать предметы и количество открытых домашек", {}),
    fn("subject_detail", "Показать домашку и последние заметки по предмету", {
        "subject": {"type": "string"}}, ["subject"]),
    fn("show_timetable", "Показать занятия и свободные окна на дату (YYYY-MM-DD, по умолчанию сегодня) или на несколько дней", {
        "date": {"type": "string"},
        "days": {"type": "integer", "description": "От 1 до 7"}}),
    fn("list_topics", "Показать открытые темы, НЕ задачи. Для поиска, сравнения и групповой работы с задачами всегда используй query_tasks или show_board.", {
        "include_closed": {"type": "boolean"}}),
    fn("read_topic", "Прочитать записи по теме", {
        "topic": {"type": "string"}}, ["topic"]),
    fn("add_task", "Добавить задачу на доску", {
        "column": {"type": "string", "enum": COLUMNS},
        "title": {"type": "string"},
        "due": {"type": "string", "description": "Дедлайн YYYY-MM-DD или пусто"},
        "effort": {"type": "string", "enum": EFFORTS},
        "minutes": {"type": "integer", "description": "Оценка времени в минутах"},
        "risk": {"type": "string", "description": "Главный риск или пусто"},
        "importance": {"type": "number", "description": "Важность от 0 до 1, по умолчанию 0.5"},
        "window_days": {"type": "integer", "description": "За сколько дней до дедлайна задача становится срочной"},
        "subject": {"type": "string", "description": "Предмет, если задача относится к домашней работе"},
        "parent_id": {"type": "string", "description": "id или название родительской задачи для подтаска"},
        "tags": {"type": "array", "items": {"type": "string"}, "description": "Темы/теги задачи"}},
        ["column", "title"]),
    fn("update_task", "Изменить существующую задачу (найти по части названия)", {
        "title": {"type": "string"},
        "column": {"type": "string", "enum": COLUMNS},
        "due": {"type": "string"},
        "effort": {"type": "string", "enum": EFFORTS},
        "minutes": {"type": "integer"},
        "risk": {"type": "string"},
        "importance": {"type": "number"},
        "window_days": {"type": "integer"},
        "subject": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}}}, ["title"]),
    fn("delete_task", "Удалить одну или несколько задач навсегда. Для дубликатов используй точные id; только по явной просьбе пользователя", {
        "title": {"type": "string", "description": "Название только для одной однозначной задачи"},
        "task_id": {"type": "string", "description": "Один или несколько точных id задач"}}),
    fn("edit_task", "Изменить название, приоритет, длительность или темы задачи", {
        "task": {"type": "string"}, "title": {"type": "string"},
        "importance": {"type": "number"}, "minutes": {"type": "integer"},
        "tags": {"type": "array", "items": {"type": "string"}}}, ["task"]),
    fn("add_task_note", "Добавить заметку к существующей задаче", {
        "task": {"type": "string"}, "text": {"type": "string"}}, ["task", "text"]),
    fn("link_tasks", "Создать двустороннюю связь между двумя задачами", {
        "task": {"type": "string"}, "related_task": {"type": "string"}}, ["task", "related_task"]),
    fn("block_task", "Указать, что одна задача заблокирована другой", {
        "task": {"type": "string"}, "blocked_by": {"type": "string"}}, ["task", "blocked_by"]),
    fn("unblock_task", "Снять блокировку задачи", {
        "task": {"type": "string"}, "blocked_by": {"type": "string"}}, ["task", "blocked_by"]),
    fn("add_goal", "Добавить долгосрочную цель", {
        "title": {"type": "string"},
        "horizon": {"type": "string", "enum": HORIZONS},
        "note": {"type": "string"}}, ["title", "horizon"]),
    fn("open_topic", "Открыть новую тему, которой нет среди открытых", {
        "title": {"type": "string"},
        "first_note": {"type": "string"}}, ["title"]),
    fn("add_note", "Добавить запись в существующую открытую тему", {
        "topic": {"type": "string"},
        "text": {"type": "string"}}, ["topic", "text"]),
    fn("close_topic", "Закрыть тему с итоговой сводкой", {
        "topic": {"type": "string"},
        "summary": {"type": "string"}}, ["topic"]),
    fn("reopen_topic", "Снова открыть закрытую тему", {
        "topic": {"type": "string"}}, ["topic"]),
    fn("add_homework", "Записать домашку по предмету", {
        "subject": {"type": "string"},
        "title": {"type": "string"},
        "due": {"type": "string", "description": "Срок YYYY-MM-DD или пусто"}}, ["subject", "title"]),
    fn("done_homework", "Отметить домашку выполненной", {
        "subject": {"type": "string"},
        "title": {"type": "string"}}, ["subject", "title"]),
    fn("add_subject_note", "Записать ответ пользователя или заметку по предмету: что сделано, что непонятно, когда сдача", {
        "subject": {"type": "string"},
        "text": {"type": "string"}}, ["subject", "text"]),
    fn("set_schedule", "Сохранить сон и рутину, которые назвал пользователь. Время в формате ЧЧ:ММ. "
                       "Передавай только то, что пользователь сказал, остальное оставь пустым", {
        "sleep_from": {"type": "string", "description": "Время отхода ко сну, например 23:30"},
        "sleep_to": {"type": "string", "description": "Время подъёма, например 07:30"},
        "routine": {"type": "string", "description": "Свободный текст о рутине: работа, учёба, занятия"}}),
    fn("add_timetable_items", "Добавить одно или несколько занятий или событий. Разовое: date. "
                              "Повтор: anchor (первая дата повтора), every_days (интервал в днях: раз в неделю 7, "
                              "раз в 4 недели 28, раз в 10 дней 10), weekdays (необязательно, например «чт» или «пн, ср»), "
                              "until (необязательно, дата окончания). Если первой даты повтора нет, спроси её", {
        "items": {"type": "array", "items": {"type": "object", "properties": {
            "title": {"type": "string"},
            "start": {"type": "string", "description": "ЧЧ:ММ"},
            "end": {"type": "string", "description": "ЧЧ:ММ или пусто"},
            "date": {"type": "string", "description": "YYYY-MM-DD для разового"},
            "anchor": {"type": "string", "description": "YYYY-MM-DD, первая дата повтора"},
            "every_days": {"type": "integer"},
            "weekdays": {"type": "string"},
            "until": {"type": "string"},
            "source": {"type": "string", "enum": ["есть", "хочу"]},
            "kind": {"type": "string", "enum": ["обязательное", "дополнительное"]},
            "mode": {"type": "string", "enum": ["присутствие", "подключиться", "работа"]},
            "place": {"type": "string", "enum": ["офлайн", "онлайн"]},
            "commute": {"type": "boolean"}},
            "required": ["title", "start"]}}}, ["items"]),
    fn("skip_timetable_item", "Пропустить одно вхождение повторяющегося занятия (или удалить разовое)", {
        "key": {"type": "string", "description": "id, например 5, или часть названия"},
        "date": {"type": "string"}}, ["key", "date"]),
    fn("move_timetable_item", "Перенести одно вхождение занятия на другую дату", {
        "key": {"type": "string", "description": "id или часть названия"},
        "from_date": {"type": "string"},
        "to_date": {"type": "string"}}, ["key", "from_date", "to_date"]),
    fn("remove_timetable_item", "Удалить занятие из расписания полностью", {
        "key": {"type": "string", "description": "id или часть названия"}}, ["key"]),
]

WRITE = {"add_task", "update_task", "edit_task", "delete_task", "add_task_note",
         "link_tasks", "block_task", "unblock_task", "add_goal",
         "add_theme", "rename_theme", "delete_theme",
         "open_topic", "add_note", "close_topic", "reopen_topic", "set_schedule",
         "add_timetable_items", "skip_timetable_item", "move_timetable_item", "remove_timetable_item",
         "add_homework", "done_homework", "add_subject_note", "apply_task_changes"}

FUNCS = {
    "query_tasks": tasks.query_tasks,
    "propose_task_changes": tasks.propose_task_changes,
    "apply_task_changes": tasks.apply_task_changes,
    "show_board": tasks.show_board, "deadlines": tasks.deadlines,
    "list_themes": themes.load,
    "add_theme": themes.add,
    "rename_theme": themes.rename,
    "delete_theme": themes.remove,
    "add_task": tasks.add_task, "update_task": tasks.update_task, "delete_task": tasks.delete_task,
    "task_details": tasks.task_details, "edit_task": tasks.edit_task,
    "add_task_note": tasks.add_task_note,
    "link_tasks": tasks.link_tasks, "block_task": tasks.block_task, "unblock_task": tasks.unblock_task,
    "show_goals": goals.show_goals, "add_goal": goals.add_goal,
    "show_schedule": schedule.schedule_text, "set_schedule": schedule.set_schedule,
    "show_subjects": subjects.show_subjects, "subject_detail": subjects.subject_detail,
    "add_homework": subjects.add_homework, "done_homework": subjects.done_homework,
    "add_subject_note": subjects.add_subject_note,
    "show_timetable": timetable.view, "add_timetable_items": timetable.add_items,
    "skip_timetable_item": timetable.skip_occurrence,
    "move_timetable_item": timetable.move_occurrence,
    "remove_timetable_item": timetable.remove_item,
    "list_topics": topics.list_topics, "read_topic": topics.read_topic,
    "open_topic": topics.open_topic, "add_note": topics.add_note,
    "close_topic": topics.close_topic, "reopen_topic": topics.reopen_topic,
}

# Keep the batch operations available to internal callers as well as the
# model dispatcher. This prevents older call paths from bypassing FUNCS.
query_tasks = tasks.query_tasks
propose_task_changes = tasks.propose_task_changes
apply_task_changes = tasks.apply_task_changes