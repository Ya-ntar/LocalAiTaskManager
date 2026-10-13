import os, datetime, threading
from ..infrastructure import store
from ..infrastructure.config import CHATS_DIR, OLD_LOG
from .textcheck import foreign

STATE = {"chat_id": None}
LOCK = threading.RLock()

def _chat_file(cid):
    return os.path.join(CHATS_DIR, f"{cid}.json")

def _read_chat(cid):
    if not cid:
        return None
    return store.read_json(_chat_file(cid), None)

def _write_chat(chat):
    os.makedirs(CHATS_DIR, exist_ok=True)
    store.write_json(_chat_file(chat["id"]), chat)

def _now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")

def list_chats():
    if not os.path.isdir(CHATS_DIR):
        return []
    chats = []
    for name in os.listdir(CHATS_DIR):
        if name.endswith(".json"):
            c = store.read_json(os.path.join(CHATS_DIR, name), None)
            if c and "id" in c:
                chats.append(c)
    return sorted(chats, key=lambda c: c.get("updated", ""), reverse=True)

def create_chat(title="Новый чат"):
    now = datetime.datetime.now()
    cid = f"{now:%Y%m%d-%H%M%S}-{now.microsecond // 1000:03d}"
    chat = {"id": cid, "title": title, "created": _now_iso(), "updated": _now_iso(),
            "messages": [], "pending_plan": None,
            "referenced_task_ids": [], "referenced_theme_names": []}
    _write_chat(chat)
    return chat

def ensure_current():
    if STATE["chat_id"] and _read_chat(STATE["chat_id"]):
        return
    chats = list_chats()
    if not chats:
        old = store.read_json(OLD_LOG, [])
        chat = create_chat("Перенесённый чат" if old else "Новый чат")
        if old:
            chat["messages"] = [m for m in old[-200:] if not foreign(m.get("content", ""))]
            _write_chat(chat)
        chats = [chat]
    STATE["chat_id"] = chats[0]["id"]

def current_chat():
    ensure_current()
    chat = _read_chat(STATE["chat_id"])
    if not chat:
        return None
    chat.setdefault("title", "Новый чат")
    chat.setdefault("messages", [])
    chat.setdefault("pending_plan", None)
    chat.setdefault("referenced_task_ids", [])
    chat.setdefault("referenced_theme_names", [])
    return chat

def switch_chat(cid):
    if not _read_chat(cid):
        return "Чат не найден"
    STATE["chat_id"] = cid
    return None

def clear_chat(cid=None):
    chat = _read_chat(cid) if cid else current_chat()
    if not chat:
        return "Чат не найден"
    chat["messages"] = []
    chat["updated"] = _now_iso()
    _write_chat(chat)
    return None

def rename_chat(cid, title):
    chat = _read_chat(cid)
    if not chat:
        return "Чат не найден"
    chat["title"] = (title or "Без названия").strip()[:80]
    _write_chat(chat)
    return None

def delete_chat(cid):
    if not _read_chat(cid):
        return "Чат не найден"
    os.remove(_chat_file(cid))
    if STATE["chat_id"] == cid:
        STATE["chat_id"] = None
        ensure_current()
    return None

def record(chat, user_text, reply):
    latest = _read_chat(chat["id"])
    if latest is not None:
        chat["pending_plan"] = latest.get("pending_plan")
    if user_text:
        if chat["title"] == "Новый чат":
            chat["title"] = user_text.strip().replace("\n", " ")[:40]
        chat["messages"].append({"role": "user", "content": user_text})
    chat["messages"].append({"role": "assistant", "content": reply})
    chat["messages"] = chat["messages"][-200:]
    chat["updated"] = _now_iso()
    _write_chat(chat)

def set_pending_plan(chat, plan):
    chat["pending_plan"] = plan
    chat["updated"] = _now_iso()
    _write_chat(chat)

def set_references(chat, task_ids=None, theme_names=None):
    if task_ids is not None:
        chat["referenced_task_ids"] = list(dict.fromkeys(task_ids))
    if theme_names is not None:
        chat["referenced_theme_names"] = list(dict.fromkeys(theme_names))
    chat["updated"] = _now_iso()
    _write_chat(chat)

def chats_summary():
    return [{"id": c["id"], "title": c.get("title", "Новый чат"),
             "count": len(c.get("messages", []))}
            for c in list_chats()]