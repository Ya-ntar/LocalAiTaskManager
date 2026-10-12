from ..conversation import chats, agent
from ..infrastructure import journal
from ..planner import tasks

def read_message(prompt):
    parts = []
    while True:
        line = input(prompt if not parts else "... ")
        if line.endswith("\\"):
            parts.append(line[:-1])
            continue
        parts.append(line)
        break
    return "\n".join(parts).strip()

def console_main():
    tasks.save_tasks(tasks.load_tasks())
    chat = chats.current_chat()
    print("Команды: /чаты /новый /очистить /неделя /месяц /итог /дедлайны /журнал /выход")
    print("Строка с \\ на конце продолжается на следующей строке.")
    if not chat["messages"]:
        agent.start_session(chat)
    while True:
        text = read_message(f"\n{chat['title']} > ")
        if not text:
            continue
        if text == "/выход":
            break
        if text == "/журнал":
            print(journal.show_journal())
            continue
        if text == "/чаты":
            for c in chats.chats_summary():
                mark = "*" if c["id"] == chats.STATE["chat_id"] else " "
                print(f"{mark} {c['title']} ({c['count']}) id={c['id']}")
            continue
        if text == "/новый":
            chat = chats.create_chat()
            chats.STATE["chat_id"] = chat["id"]
            agent.start_session(chat)
            continue
        if text == "/очистить":
            chats.clear_chat()
            chat = chats.current_chat()
            agent.start_session(chat)
            continue
        sent = agent.expand(text)
        reply, _ = agent.run_turn(sent, chat["messages"])
        print("\n" + reply)
        chats.record(chat, sent, reply)
        chat = chats.current_chat()