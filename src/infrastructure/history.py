import os, re, subprocess
from .store import USER_DATA_DIR

REPO = USER_DATA_DIR
IDENT = ["-c", "user.name=planner", "-c", "user.email=planner@localhost"]
IGNORE = "chats/\nboard.html\nchanges.log\n*.tmp\n"
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _git(*args):
    try:
        r = subprocess.run(["git", "-C", REPO, *IDENT, *args],
                           capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        raise RuntimeError("git не найден. Установите Git for Windows")
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "ошибка git")
    return r.stdout


def _check_sha(sha):
    if not SHA_RE.match(sha or ""):
        raise ValueError("некорректный идентификатор изменения")


def init():
    os.makedirs(REPO, exist_ok=True)
    if not os.path.isdir(os.path.join(REPO, ".git")):
        _git("init", "-q")
        with open(os.path.join(REPO, ".gitignore"), "w", encoding="utf-8") as f:
            f.write(IGNORE)
        _git("add", "-A")
        _git("commit", "-q", "--allow-empty", "-m", "начальное состояние")


def commit(message):
    _git("add", "-A")
    if _git("status", "--porcelain").strip():
        _git("commit", "-q", "-m", message[:300])


def commit_safe(message):
    """Коммит, который никогда не ломает основную работу, даже если git недоступен."""
    try:
        commit(message)
    except Exception as e:
        print(f"  [история] не удалось записать: {e}")


def log(limit=50):
    out = _git("log", f"-{limit}", "--format=%H%x09%ad%x09%s",
               "--date=format:%d.%m %H:%M")
    return [line.split("\t", 2) for line in out.splitlines() if line]


def show(sha):
    """Текст изменения: что поменялось в файлах (с ограничением по длине)."""
    _check_sha(sha)
    return _git("show", "--format=%ad  %s", "--date=format:%d.%m %H:%M",
                "--stat", "-p", sha)[:20000]


def rollback_to_before(sha):
    """Вернуть состояние, которое было до изменения sha."""
    _check_sha(sha)
    try:
        parent = _git("rev-parse", f"{sha}^").strip()
    except RuntimeError:
        raise RuntimeError("Это самое первое состояние, до него откатить нельзя")
    # Текущее состояние сохраняем отдельным коммитом, чтобы откат тоже можно было отменить.
    commit("перед откатом")
    _git("read-tree", "-u", "--reset", parent)
    _git("add", "-A")
    _git("commit", "-q", "--allow-empty", "-m", f"откат: до изменения {sha[:8]}")
