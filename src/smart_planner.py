import sys
from http.server import ThreadingHTTPServer
from .infrastructure import store
from .conversation import chats
from .planner import tasks
from .infrastructure.config import PORT
from .web.web_server import Handler
from .web.console import console_main

def main():
    store.migrate_user_data()
    if "--console" in sys.argv:
        console_main()
        return
    chats.ensure_current()
    tasks.save_tasks(tasks.load_tasks())
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Откройте в браузере: http://127.0.0.1:{PORT}")
    print("Остановить: Ctrl+C. Консольный режим: python smart_planner.py --console")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено")

if __name__ == "__main__":
    main()