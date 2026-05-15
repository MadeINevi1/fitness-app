from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_bootstrap import Bootstrap5

from app.config import Config


app = Flask(__name__)
app.config.from_object(Config)

bootstrap = Bootstrap5(app)
csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Для доступа к этой странице необходимо войти в систему."


@login_manager.user_loader
def load_user(user_id):
    from app.models import get_user_by_id
    return get_user_by_id(int(user_id))


from app import routes