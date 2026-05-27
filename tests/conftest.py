import pytest

from app import app
from app import db as app_db


def delete_test_user():
    conn = app_db.get_db_connection()

    if conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM users WHERE email = ?;",
            ("student@example.com",)
        )
        conn.commit()
        app_db.close_db_connection(conn)


@pytest.fixture()
def client():
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )

    app_db.init_db()
    delete_test_user()

    with app.test_client() as test_client:
        yield test_client

    delete_test_user()
