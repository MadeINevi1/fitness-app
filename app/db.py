import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "fitness_app.db"


def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return None


def close_db_connection(conn):
    if conn:
        conn.close()


def init_db():
    conn = get_db_connection()

    if conn:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                full_name TEXT,
                age INTEGER,
                height REAL,
                weight REAL,
                target_weight REAL,
                target_duration_weeks INTEGER,
                gender TEXT,
                activity_level TEXT,
                training_level TEXT,
                workouts_per_week INTEGER,
                program_duration INTEGER,
                training_place TEXT,
                goal TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS fitness_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                profile_id INTEGER,
                calories REAL,
                proteins REAL,
                fats REAL,
                carbs REAL,
                training_plan TEXT,
                nutrition_plan TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (profile_id) REFERENCES user_profiles(profile_id) ON DELETE CASCADE
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS progress_records (
                progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                profile_id INTEGER,
                week_number INTEGER,
                weight REAL NOT NULL,
                note TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (profile_id) REFERENCES user_profiles(profile_id) ON DELETE CASCADE
            );
            """
        )

        conn.commit()
        close_db_connection(conn)
