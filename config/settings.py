import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def load_config(api_key=None):
    return {
        "api_key":    api_key or os.getenv("GROQ_API_KEY", ""),
        "model":      os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "max_chars":  int(os.getenv("MAX_CHARS_PER_PAGE", "5000")),
        "output_dir": os.getenv("OUTPUT_DIR", "./output"),
        "log_dir":    os.getenv("LOG_DIR", "./logs"),
        "table_name": os.getenv("DB_TABLE", "register"),
    }
