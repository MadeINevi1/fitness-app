import pytest

from app import app
from app import db as app_db


@pytest.fixture()
def client(tmp_path):
    original_db_path = app_db.DB_PATH
    app_db.DB_PATH = tmp_path / "test_fitness_app.db"

    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )

    app_db.init_db()

    with app.test_client() as test_client:
        yield test_client

    app_db.DB_PATH = original_db_path
