import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key"

    DB_SERVER = os.environ.get("DB_SERVER") or "127.0.0.1"
    DB_NAME = os.environ.get("DB_NAME") or "fitness_app"
    DB_USER = os.environ.get("DB_USER") or "postgres"
    DB_PASSWORD = os.environ.get("DB_PASSWORD") or "1234"
    DB_PORT = os.environ.get("DB_PORT") or "5432"