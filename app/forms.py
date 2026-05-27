from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FloatField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional



class RegistrationForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Укажите email."),
            Email(message="Введите корректный email.")
        ],
    )

    password = PasswordField(
        "Пароль",
        validators=[
            DataRequired(message="Укажите пароль."),
            Length(min=4, max=50, message="Пароль должен быть от 4 до 50 символов.")
        ],
    )

    confirm_password = PasswordField(
        "Повторите пароль",
        validators=[
            DataRequired(message="Повторите пароль."),
            EqualTo("password", message="Пароли должны совпадать.")
        ],
    )

    submit = SubmitField("Зарегистрироваться")


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Укажите email."),
            Email(message="Введите корректный email.")
        ],
    )

    password = PasswordField(
        "Пароль",
        validators=[
            DataRequired(message="Укажите пароль.")
        ],
    )

    submit = SubmitField("Войти")


class FitnessForm(FlaskForm):
    full_name = StringField(
        "ФИО",
        validators=[
            DataRequired(message="Укажите ФИО."),
            Length(min=2, max=100, message="ФИО должно быть от 2 до 100 символов.")
        ],
    )

    age = IntegerField(
        "Возраст",
        validators=[
            DataRequired(message="Укажите возраст."),
            NumberRange(min=10, max=100, message="Возраст должен быть от 10 до 100 лет.")
        ],
    )

    height = FloatField(
        "Рост, см",
        validators=[
            DataRequired(message="Укажите рост."),
            NumberRange(min=100, max=250, message="Рост должен быть от 100 до 250 см.")
        ],
    )

    weight = FloatField(
        "Текущий вес, кг",
        validators=[
            DataRequired(message="Укажите текущий вес."),
            NumberRange(min=30, max=300, message="Текущий вес должен быть от 30 до 300 кг.")
        ],
    )

    target_weight = FloatField(
        "Желаемый вес, кг",
        validators=[
            DataRequired(message="Укажите желаемый вес."),
            NumberRange(min=30, max=300, message="Желаемый вес должен быть от 30 до 300 кг.")
        ],
    )

    gender = SelectField(
        "Пол",
        choices=[
            ("male", "Мужской"),
            ("female", "Женский"),
        ],
        validators=[
            DataRequired(message="Выберите пол.")
        ],
    )

    activity_level = SelectField(
        "Повседневная активность вне тренировок",
        choices=[
            (
                "sedentary",
                "Сидячий образ жизни: учёба, офисная работа, мало ходьбы"
            ),
            (
                "light",
                "Низкая активность: лёгкая ходьба и обычные бытовые дела"
            ),
            (
                "moderate",
                "Средняя активность: много ходьбы, активный день без тяжёлой работы"
            ),
            (
                "physical",
                "Высокая активность: работа на ногах или регулярная физическая нагрузка"
            ),
            (
                "heavy_physical",
                "Очень высокая активность: тяжёлый физический труд"
            ),
        ],
        validators=[
            DataRequired(message="Выберите уровень повседневной активности.")
        ],
    )

    training_level = SelectField(
        "Уровень подготовки",
        choices=[
            ("beginner", "Новичок"),
            ("intermediate", "Средний уровень"),
            ("advanced", "Опытный уровень"),
        ],
        validators=[
            DataRequired(message="Выберите уровень подготовки.")
        ],
    )

    workouts_per_week = SelectField(
        "Планируемое количество тренировок в неделю",
        choices=[
            ("2", "2 тренировки в неделю"),
            ("3", "3 тренировки в неделю"),
            ("4", "4 тренировки в неделю"),
            ("5", "5 тренировок в неделю"),
        ],
        validators=[
            DataRequired(message="Выберите количество тренировок в неделю.")
        ],
    )

    program_duration = SelectField(
        "Минимальный срок программы",
        choices=[
            ("4", "4 недели"),
            ("8", "8 недель"),
            ("12", "12 недель"),
        ],
        validators=[
            DataRequired(message="Выберите минимальный срок программы.")
        ],
    )

    training_place = SelectField(
        "Место тренировок",
        choices=[
            ("home", "Дома"),
            ("gym", "В тренажёрном зале"),
        ],
        validators=[
            DataRequired(message="Выберите место тренировок.")
        ],
    )

    goal = SelectField(
        "Цель",
        choices=[
            ("weight_loss", "Снижение веса"),
            ("muscle_gain", "Набор мышечной массы"),
            ("maintenance", "Поддержание формы"),
        ],
        validators=[
            DataRequired(message="Выберите цель.")
        ],
    )

    submit = SubmitField("Рассчитать программу")


class ProgressForm(FlaskForm):
    week_number = IntegerField(
        "Номер недели",
        validators=[
            DataRequired(message="Укажите номер недели."),
            NumberRange(min=1, max=200, message="Номер недели должен быть от 1 до 200.")
        ],
    )

    weight = FloatField(
        "Текущий вес, кг",
        validators=[
            DataRequired(message="Укажите текущий вес."),
            NumberRange(min=30, max=300, message="Вес должен быть от 30 до 300 кг.")
        ],
    )

    note = TextAreaField(
        "Комментарий",
        validators=[
            Optional(),
            Length(max=500, message="Комментарий не должен превышать 500 символов.")
        ],
    )

    submit = SubmitField("Добавить запись")