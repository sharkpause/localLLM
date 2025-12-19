def debug_log(msg: str):
    with open("debug_log", "a", encoding="utf-8") as f:
        f.write(msg + "\n")