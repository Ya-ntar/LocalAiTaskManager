import json, os, datetime, urllib.request, html

BASE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(store.USER_DATA_DIR, "tasks.json")
GOALS = os.path.join(store.USER_DATA_DIR, "goals.json")
LOG = os.path.join(store.USER_DATA_DIR, "chat_log.json")
PAGE = os.path.join(store.USER_DATA_DIR, "board.html")
API = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "qwen2.5-7b-instruct-1m"
COLUMNS = ["Входящие", "Сегодня", "В процессе", "Готово"]
HORIZONS = ["неделя", "месяц", "год", "долгосрочно"]
EFFORTS = ["лёгкая", "средняя", "тяжёлая"]
HISTORY_LIMIT = 40
MODE = {"value": "советник"}
WRITE = {"add_task", "update_task", "add_goal"}

OPENING = ("Начни сессию в режиме советника: коротко оцени доску, ближайшие дедлайны и риски, "
           "назови одну вещь, которая важнее всего сейчас, и задай один вопрос.")
PROMPTS = {
    "/неделя": "Проведём планирование на неделю. Посмотри дедлайны и предложи, что делать по дням и колонкам.",
    "/месяц": "Проведём обзор на месяц. Посмотри цели по горизонтам и дедлайны, спроси, что продвинулось, и предложи 2-3 шага.",
    "/итог": "Подведи итог: спроси, что сделано, что застряло и что можно убрать из списка.",
    "/дедлайны": "Посмотри дедлайны и риски. Скажи, что горит, что можно отложить, и в каком порядке делать.",
}

def read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_tasks():
    return read_json(TASKS, [])

def save_tasks(tasks):
    write_json(TASKS, tasks)
    write_html(tasks)

def task_line(t):
    parts = [t["title"]]
    if t.get("due"):
        parts.append(f"дедлайн {t['due']}")
    if t.get("effort"):
        parts.append(f"сложность: {t['effort']}")
    if t.get("minutes"):
        parts.append(f"~{t['minutes']} мин")
    if t.get("risk"):
        parts.append(f"риск: {t['risk']}")
    return " | ".join(parts)

def write_html(tasks):
    cols = ""
    for c in COLUMNS:
        items = "".join(f"<li>{html.escape(task_line(t))}</li>" for t in tasks if t["column"] == c)
        cols += f"<div class='col'><h2>{c}</h2><ul>{items}</ul></div>"
    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>Доска</title>
<style>body{{font-family:sans-serif;display:flex;gap:12px;padding:12px}}
.col{{flex:1;background:#eee;border-radius:8px;padding:8px}}
li{{list-style:none;background:#fff;margin:6px 0;padding:6px;border-radius:4px}}</style>
</head><body>{cols}</body></html>"""
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(page)

def check_due(due):
    if due:
        datetime.date.fromisoformat(due)  # бросит ошибку, если формат неверный

def add_task(column, title, due="", effort="", minutes=0, risk=""):
    if column not in COLUMNS:
        return f"Нет колонки «{column}». Есть: {', '.join(COLUMNS)}"
    if effort and effort not in EFFORTS:
        return f"Сложность должна быть одной из: {', '.join(EFFORTS)}"
    try:
        check_due(due)
    except ValueError:
        return "Дедлайн нужен в формате YYYY-MM-DD"
    tasks = load_tasks()
    tasks.append({"title": title, "column": column, "due": due or "",
                  "effort": effort or "", "minutes": int(minutes or 0), "risk": risk or ""})
    save_tasks(tasks)
    return f"Добавлено: {task_line(tasks[-1])}"

def update_task(title, column="", due="", effort="", minutes=None, risk=""):
    tasks = load_tasks()
    task = next((t for t in tasks if title.lower() in t["title"].lower()), None)
    if task is None:
        return f"Задача «{title}» не найдена"
    if column:
        if column not in COLUMNS:
            return f"Нет колонки «{column}»"
        task["column"] = column
    if due:
        try:
            check_due(due)
        except ValueError:
            return "Дедлайн нужен в формате YYYY-MM-DD"
        task["due"] = due
    if effort:
        if effort not in EFFORTS:
            return f"Сложность должна быть одной из: {', '.join(EFFORTS)}"
        task["effort"] = effort
    if minutes is not None:
        task["minutes"] = int(minutes)
    if risk:
        task["risk"] = risk
    save_tasks(tasks)
    return f"Обновлено: {task_line(task)}"

def show_board():
    tasks = load_tasks()
    lines = []
    for c in COLUMNS:
        lines.append(f"[{c}]")
        for t in tasks:
            if t["column"] == c:
                lines.append(f"  - {task_line(t)}")
    return "\n".join(lines)

def deadlines():
    tasks = [t for t in load_tasks() if t["column"] != "Готово"]
    today = datetime.date.today()
    lines = []
    for t in sorted([t for t in tasks if t.get("due")], key=lambda t: t["due"]):
        try:
            days = (datetime.date.fromisoformat(t["due"]) - today).days
            when = f"через {days} дн." if days >= 0 else f"просрочено на {-days} дн."
        except ValueError:
            when = "дата не распознана"
        lines.append(f"- {task_line(t)} ({when})")
    total = sum(int(t.get("minutes") or 0) for t in tasks)
    lines.append(f"Всего не завершено: {len(tasks)} задач, примерно {total // 60} ч {total % 60} мин работы.")
    return "\n".join(lines)

def add_goal(title, horizon, note=""):
    if horizon not in HORIZONS:
        return f"Горизонт должен быть одним из: {', '.join(HORIZONS)}"
    goals = read_json(GOALS, [])
    goals.append({"title": title, "horizon": horizon, "note": note})
    write_json(GOALS, goals)
    return f"Цель добавлена: «{title}» ({horizon})"

def show_goals():
    goals = read_json(GOALS, [])
    if not goals:
        return "Целей пока нет"
    return "\n".join(f"[{g['horizon']}] {g['title']}" + (f" — {g['note']}" if g.get("note") else "")
                     for g in goals)

def fn(name, desc, props, required=()):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": list(required)}}}

READ_TOOLS = [
    fn("show_board", "Показать все задачи по колонкам", {}),
    fn("deadlines", "Показать дедлайны, что горит и общий объём работы", {}),
    fn("show_goals", "Показать все цели", {}),
]
WRITE_TOOLS = [
    fn("add_task", "Добавить задачу", {
        "column": {"type": "string", "enum": COLUMNS},
        "title": {"type": "string"},
        "due": {"type": "string", "description": "Дедлайн YYYY-MM-DD или пусто"},
        "effort": {"type": "string", "enum": EFFORTS},
        "minutes": {"type": "integer", "description": "Оценка времени в минутах"},
        "risk": {"type": "string", "description": "Главный риск или пусто"}}, ["column", "title"]),
    fn("update_task", "Изменить существующую задачу (найти по части названия)", {
        "title": {"type": "string"},
        "column": {"type": "string", "enum": COLUMNS},
        "due": {"type": "string"},
        "effort": {"type": "string", "enum": EFFORTS},
        "minutes": {"type": "integer"},
        "risk": {"type": "string"}}, ["title"]),
    fn("add_goal", "Добавить долгосрочную цель", {
        "title": {"type": "string"},
        "horizon": {"type": "string", "enum": HORIZONS},
        "note": {"type": "string"}}, ["title", "horizon"]),
]
TOOLS = READ_TOOLS + WRITE_TOOLS
FUNCS = {"add_task": add_task, "update_task": update_task, "show_board": show_board,
         "deadlines": deadlines, "show_goals": show_goals, "add_goal": add_goal}

def system_prompt():
    today = datetime.date.today().isoformat()
    base = (f"Ты личный планировщик и собеседник пользователя. Сегодня {today}. "
            "Общайся по-русски, тепло и по делу. ")
    if MODE["value"] == "советник":
        rules = ("Сейчас режим СОВЕТНИКА. Помогай решить, что делать: опирайся на дедлайны, риски, "
                 "сложность и оценку времени. Помоги выбрать 3 главных дела на сегодня, назови риски, "
                 "предложи порядок и 1-2 задачи, которых пользователь ещё не называл. "
                 "Ничего не записывай. Если пользователь сообщает новые факты, скажи, что для записи нужна команда /запись. "
                 "Отвечай коротко.")
    else:
        rules = ("Сейчас режим ЗАПИСИ. Из сообщения пользователя вытащи задачи, дедлайны, сложность "
                 "(лёгкая, средняя, тяжёлая), оценку времени в минутах и риски, и сохрани через add_task, "
                 "update_task или add_goal. Если важной детали нет (дедлайн, оценка), спроси одним коротким вопросом. "
                 "Если сложность или время не названы, можешь предложить свою оценку, но явно пометь её как предположение. "
                 "После записи коротко подтверди, что записано.")
    return base + rules + f"\n\nДоска:\n{show_board()}\n\nДедлайны:\n{deadlines()}\n\nЦели:\n{show_goals()}"

def ask(messages, tools):
    body = json.dumps({"model": MODEL, "messages": messages, "tools": tools,
                       "temperature": 0.4}).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["choices"][0]["message"]

def turn(user_text, log, store=True):
    tools = TOOLS if MODE["value"] == "запись" else READ_TOOLS
    messages = [{"role": "system", "content": system_prompt()}] + log[-HISTORY_LIMIT:]
    if user_text:
        messages.append({"role": "user", "content": user_text})
    msg = ask(messages, tools)
    while msg.get("tool_calls"):
        messages.append(msg)
        for call in msg["tool_calls"]:
            name = call["function"]["name"]
            try:
                if name in WRITE and MODE["value"] != "запись":
                    result = "Сейчас режим советника, записи нет. Переключитесь командой /запись."
                else:
                    args = json.loads(call["function"].get("arguments") or "{}")
                    result = FUNCS[name](**args)
            except Exception as e:
                result = f"Ошибка: {e}"
            print(f"  [{name}] {result}")
            messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": str(result)})
        msg = ask(messages, tools)
    text = msg.get("content") or ""
    print("\n" + text)
    if store:
        if user_text:
            log.append({"role": "user", "content": user_text})
        log.append({"role": "assistant", "content": text})
        log[:] = log[-200:]
        write_json(LOG, log)

def main():
    log = read_json(LOG, [])
    save_tasks(load_tasks())
    print("Команды: /советник /запись /неделя /месяц /итог /дедлайны /выход")
    print(f"Режим: {MODE['value']}")
    turn(OPENING, log, store=False)
    while True:
        text = input("\n[" + MODE["value"] + "] > ").strip()
        if not text:
            continue
        if text == "/выход":
            break
        if text in ("/советник", "/запись"):
            MODE["value"] = text[1:]
            print(f"Режим: {MODE['value']}")
            continue
        turn(PROMPTS.get(text, text), log)

if __name__ == "__main__":
    main()