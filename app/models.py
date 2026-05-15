from flask_login import UserMixin
from app.db import get_db_connection, close_db_connection
import hashlib


class User(UserMixin):
    def __init__(self, user_id, email, role):
        self.id = user_id
        self.email = email
        self.role = role

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        conn = get_db_connection()

        if conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT password_hash FROM users WHERE user_id = ?",
                (self.id,)
            )

            result = cur.fetchone()
            close_db_connection(conn)

            if result and result[0] == self.hash_password(password):
                return True

        return False

    @staticmethod
    def register_user(email, password):
        conn = get_db_connection()

        if conn:
            cur = conn.cursor()

            try:
                password_hash = User.hash_password(password)

                cur.execute(
                    """
                    INSERT INTO users (email, password_hash, role)
                    VALUES (?, ?, ?);
                    """,
                    (email, password_hash, "user")
                )

                user_id = cur.lastrowid
                conn.commit()

                return User(user_id, email, "user")

            except Exception as e:
                print(f"Ошибка регистрации пользователя: {e}")
                conn.rollback()
                return None

            finally:
                close_db_connection(conn)

        return None


def get_user_by_id(user_id):
    conn = get_db_connection()

    if conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT user_id, email, role
            FROM users
            WHERE user_id = ?;
            """,
            (user_id,)
        )

        user_data = cur.fetchone()
        close_db_connection(conn)

        if user_data:
            return User(
                user_id=user_data[0],
                email=user_data[1],
                role=user_data[2]
            )

    return None


def get_user_by_email(email):
    conn = get_db_connection()

    if conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT user_id, email, role
            FROM users
            WHERE email = ?;
            """,
            (email,)
        )

        user_data = cur.fetchone()
        close_db_connection(conn)

        if user_data:
            return User(
                user_id=user_data[0],
                email=user_data[1],
                role=user_data[2]
            )

    return None