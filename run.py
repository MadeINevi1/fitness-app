from app import app
from app.db import init_db


init_db()


if __name__ == "__main__":
    app.run(debug=True)