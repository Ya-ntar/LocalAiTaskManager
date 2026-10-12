import os, html
import store

PAGE = os.path.join(store.USER_DATA_DIR, "board.html")

CSS = """body{font-family:sans-serif;display:flex;gap:12px;padding:12px}
.col{flex:1;background:#eee;border-radius:8px;padding:8px}
li{list-style:none;background:#fff;margin:6px 0;padding:6px;border-radius:4px}"""

def render(columns):
    """columns: {название колонки: [строки карточек]}. Экранирование делается здесь."""
    parts = []
    for name, cards in columns.items():
        items = "".join(f"<li>{html.escape(card)}</li>" for card in cards)
        parts.append(f"<div class='col'><h2>{html.escape(name)}</h2><ul>{items}</ul></div>")
    return ("<!doctype html><html><head><meta charset='utf-8'><title>Доска</title>"
            f"<style>{CSS}</style></head><body>{''.join(parts)}</body></html>")

def write(columns):
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(render(columns))