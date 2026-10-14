import os
from . import store

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
USER_DATA_DIR = store.USER_DATA_DIR
API = os.environ.get("AI_API_URL", "http://127.0.0.1:1234/v1/chat/completions")
MODEL = os.environ.get("AI_MODEL", "qwen2.5-7b-instruct-1m")
PORT = 8765
INSTR_DIR = os.path.join(BASE, "instructions")
UI_DIR = os.path.join(BASE, "ui")
BOARD_PAGE = os.path.join(USER_DATA_DIR, "board.html")
CHANGES = os.path.join(USER_DATA_DIR, "changes.log")
SCHEDULE = os.path.join(USER_DATA_DIR, "schedule.json")
CHATS_DIR = os.path.join(USER_DATA_DIR, "chats")
OLD_LOG = os.path.join(USER_DATA_DIR, "chat_log.json")
COLUMNS = ["Входящие", "Сегодня", "В процессе", "Готово", "Архив"]
HORIZONS = ["неделя", "месяц", "год", "долгосрочно"]
EFFORTS = ["лёгкая", "средняя", "тяжёлая"]
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
HISTORY_LIMIT = int(os.environ.get("AI_HISTORY_LIMIT", "8"))
PROMPT_CHAR_LIMIT = int(os.environ.get("AI_PROMPT_CHAR_LIMIT", "14000"))
