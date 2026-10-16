from commands import handle_command
from version import show_intro

show_intro()

while True:
    user_input = input(">> ").strip()

    if user_input in ["exit", "quit"]:
        print("Goodbye 👋")
        break

    handle_command(user_input)
