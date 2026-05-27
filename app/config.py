import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key"
    DATABASE_URL = os.environ.get("DATABASE_URL") or "postgresql://neondb_owner:npg_T3veMjhxHOR7@ep-small-wind-aqos5hiu-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    DB_SERVER = os.environ.get("DB_SERVER") or "localhost"
    DB_PORT = os.environ.get("DB_PORT") or "5432"
    DB_NAME = os.environ.get("DB_NAME") or "fitness_app"
    DB_USER = os.environ.get("DB_USER") or "postgres"
    DB_PASSWORD = os.environ.get("DB_PASSWORD") or "1234"
