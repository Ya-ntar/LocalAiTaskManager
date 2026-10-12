import datetime

URGENCY_RAMP = 2  # 1 — линейно, 2 — ближе к дате быстрее, 3 — резко в последние дни

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(x)))

def days_left(due, today=None):
    today = today or datetime.date.today()
    return (datetime.date.fromisoformat(due) - today).days

def urgency(due, window_days, today=None):
    if not due or window_days <= 0:
        return 0.0
    left = days_left(due, today)
    if left < 0:
        return 1.0
    if left >= window_days:
        return 0.0
    return clamp((1 - left / window_days) ** URGENCY_RAMP)

def neglect_bonus(untouched_days):
    return 0.2 * clamp(untouched_days / 60)

def priority(importance, due="", window_days=0, untouched_days=0, today=None):
    base = clamp(importance) * (1 + urgency(due, window_days, today))
    return round(base + neglect_bonus(untouched_days), 3)

if __name__ == "__main__":
    today = datetime.date(2026, 10, 11)
    examples = [
        ("Сдать главу, до дедлайна 2 дня, окно 14", 0.8, "2026-10-13", 14, 0),
        ("Сдать главу, до дедлайна 14 дней, окно 14", 0.8, "2026-10-25", 14, 0),
        ("Сдать главу, срок прошёл", 0.8, "2026-10-09", 14, 0),
        ("Книга, без срока, не трогали 45 дней", 0.6, "", 0, 45),
        ("Книга, без срока, сегодня открывали", 0.6, "", 0, 0),
    ]
    for title, imp, due, window, untouched in examples:
        p = priority(imp, due, window, untouched, today)
        print(f"{p:6.3f}  {title}")