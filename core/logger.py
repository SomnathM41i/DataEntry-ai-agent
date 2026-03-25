from datetime import datetime

def make_log_entry(level, msg):
    return {
        "time": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "msg": msg
    }
