from ..infrastructure import store
from ..infrastructure.config import HORIZONS

def add_goal(title, horizon, note=""):
    if horizon not in HORIZONS:
        return f"Горизонт должен быть одним из: {', '.join(HORIZONS)}"
    goals = store.load("goals")
    goals.append({"title": title, "horizon": horizon, "note": note})
    store.save("goals", goals)
    return f"Цель добавлена: «{title}» ({horizon})"

def show_goals():
    goals = store.load("goals")
    if not goals:
        return "Целей пока нет"
    return "\n".join(f"[{g['horizon']}] {g['title']}" + (f" — {g['note']}" if g.get("note") else "")
                     for g in goals)