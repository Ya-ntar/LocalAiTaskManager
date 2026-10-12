import json, os
from http.server import BaseHTTPRequestHandler
from ..infrastructure.config import UI_DIR, BOARD_PAGE
from ..conversation import chats, agent, topics
from ..planner import tasks, goals, schedule
from ..education import subjects, timetable
from . import board_page
from ..infrastructure.journal import show_journal

def _page():
    with open(os.path.join(UI_DIR, "chat.html"), encoding="utf-8") as f:
        return f.read()

def state_payload():
    chat = chats.current_chat()
    return {"chat": {"id": chat["id"], "title": chat["title"], "messages": chat["messages"]},
            "chats": chats.chats_summary()}

LOCAL_COMMANDS = {
    "show_board": tasks.show_board,
    "deadlines": tasks.deadlines,
    "show_goals": goals.show_goals,
    "show_schedule": schedule.schedule_text,
    "show_subjects": subjects.show_subjects,
    "show_timetable": lambda: timetable.view("", 2),
    "list_topics": topics.list_topics,
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def do_GET(self):
        if self.path == "/":
            self._send(200, _page(), "text/html; charset=utf-8")
        elif self.path in ("/board.css", "/board.js"):
            return self._serve_asset(self.path[1:])
        elif self.path == "/board":
            return self._serve_board()
        elif self.path == "/board.html":
            return self._serve_board()
        elif self.path == "/state":
            with chats.LOCK:
                self._json(state_payload())
        else:
            self._json({"error": "нет такого адреса"}, 404)

    def _serve_asset(self, name):
        content_types = {
            "board.css": "text/css; charset=utf-8",
            "board.js": "application/javascript; charset=utf-8",
        }
        path = os.path.join(UI_DIR, name)
        try:
            with open(path, encoding="utf-8") as file:
                body = file.read()
        except OSError:
            return self._json({"error": "ресурс не найден"}, 404)
        self._send(200, body, content_types[name])

    def _serve_board(self):
        page = board_page.render_board(tasks.load_tasks(), tasks.task_line,
                                       tasks.sorted_column)
        board_page.write_board(tasks.load_tasks(), tasks.task_line, tasks.sorted_column)
        self._send(200, page, "text/html; charset=utf-8")

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json({"error": "некорректный запрос"}, 400)
        with chats.LOCK:
            try:
                return self._route(body)
            except Exception as e:
                self._json({"error": f"модель не ответила или ошибка: {e}"}, 500)

    def _route(self, body):
        p = self.path
        if p == "/chat/new":
            chat = chats.create_chat()
            chats.STATE["chat_id"] = chat["id"]
            return self._json({"ok": True})
        if p == "/chat/open":
            err = chats.switch_chat(body.get("id", ""))
            return self._json({"error": err} if err else {"ok": True})
        if p == "/chat/clear":
            err = chats.clear_chat(body.get("id") or None)
            return self._json({"error": err} if err else {"ok": True})
        if p == "/chat/delete":
            err = chats.delete_chat(body.get("id", ""))
            return self._json({"error": err} if err else {"ok": True})
        if p == "/chat/rename":
            err = chats.rename_chat(body.get("id", ""), body.get("title", ""))
            return self._json({"error": err} if err else {"ok": True})
        if p == "/open":
            chat = chats.current_chat()
            if chat["messages"]:
                return self._json({"reply": ""})
            text, _ = agent.start_session(chat)
            return self._json({"reply": text})
        if p == "/send":
            text = str(body.get("text") or "").strip()
            if not text:
                return self._json({"error": "пустое сообщение"}, 400)
            if text == "/журнал":
                return self._json({"reply": show_journal(), "events": []})
            chat = chats.current_chat()
            sent = agent.expand(text)
            reply, events = agent.run_turn(sent, chat["messages"])
            chats.record(chat, sent, reply)
            return self._json({"reply": reply, "events": events})
        if p == "/command":
            name = str(body.get("name") or "")
            fn = LOCAL_COMMANDS.get(name)
            if fn is None:
                return self._json({"error": "неизвестная локальная команда"}, 400)
            return self._json({"name": name, "result": str(fn())})
        if p == "/board/action":
            action = str(body.get("action") or "")
            first = str(body.get("task") or "")
            second = str(body.get("related_task") or "")
            if action == "link":
                result = tasks.link_tasks(first, second)
            elif action == "block":
                result = tasks.block_task(first, second)
            elif action == "unblock":
                result = tasks.unblock_task(first, second)
            elif action == "note":
                result = tasks.add_task_note(first, str(body.get("text") or ""))
            elif action == "subtask":
                result = tasks.add_subtask(first, str(body.get("text") or ""))
            elif action == "archive":
                result = tasks.archive_task(first)
            elif action == "delete":
                result = tasks.delete_archived_task(first)
            elif action == "edit":
                result = tasks.edit_task(
                    first, body.get("title"), body.get("importance"),
                    body.get("minutes"), body.get("tags"))
            elif action == "add":
                result = tasks.add_task(
                    str(body.get("column") or "Входящие"),
                    str(body.get("title") or "").strip(),
                    tags=body.get("tags"))
            else:
                return self._json({"error": "неизвестное действие доски"}, 400)
            return self._json({"result": result})
        return self._json({"error": "нет такого адреса"}, 404)