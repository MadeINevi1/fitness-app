import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key"
    DB_PATH = os.environ.get("DB_PATH") or os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "fitness_app.db"
    )
