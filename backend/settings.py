import os

MODELSPACE_API_KEY = os.environ.get("MODELSPACE_API_KEY", "")
MODELSPACE_BASE_URL = os.environ.get(
    "MODELSPACE_BASE_URL", "https://api-inference.modelscope.cn/v1"
)
MODELSPACE_MODEL = os.environ.get("MODELSPACE_MODEL", "Qwen/Qwen2.5-72B-Instruct")
DB_PATH = os.environ.get("DB_PATH", "sessions.db")