from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FloatField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional


class RegistrationForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()]
    )

    password = PasswordField(
        "Пароль",
        validators=[DataRequired(), Length(min=4, max=50)]
    )

    confirm_password = PasswordField(
        "Повторите пароль",
        validators=[DataRequired(), EqualTo("password")]
    )

    submit = SubmitField("Зарегистрироваться")


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()]
    )

    password = PasswordField(
        "Пароль",
        validators=[DataRequired()]
    )

    submit = SubmitField("Войти")


class FitnessForm(FlaskForm):
    full_name = StringField(
        "ФИО",
        validators=[DataRequired(), Length(min=2, max=100)]
    )

    age = IntegerField(
        "Возраст",
        validators=[DataRequired(), NumberRange(min=10, max=100)]
    )

    height = FloatField(
        "Рост, см",
        validators=[DataRequired(), NumberRange(min=100, max=250)]
    )

    weight = FloatField(
        "Текущий вес, кг",
        validators=[DataRequired(), NumberRange(min=30, max=300)]
    )

    target_weight = FloatField(
        "Желаемый вес, кг",
        validators=[DataRequired(), NumberRange(min=30, max=300)]
    )

    gender = SelectField(
        "Пол",
        choices=[
            ("male", "Мужской"),
            ("female", "Женский")
        ],
        validators=[DataRequired()]
    )

    activity_level = SelectField(
        "Уровень активности",
        choices=[
            ("low", "Низкий"),
            ("medium", "Средний"),
            ("high", "Высокий")
        ],
        validators=[DataRequired()]
    )

    training_level = SelectField(
        "Уровень подготовки",
        choices=[
            ("beginner", "Новичок"),
            ("intermediate", "Средний"),
            ("advanced", "Опытный")
        ],
        validators=[DataRequired()]
    )

    workouts_per_week = SelectField(
        "Количество тренировок в неделю",
        choices=[
            ("2", "2 раза в неделю"),
            ("3", "3 раза в неделю"),
            ("4", "4 раза в неделю"),
            ("5", "5 раз в неделю")
        ],
        validators=[DataRequired()]
    )

    program_duration = SelectField(
        "Минимальный срок программы",
        choices=[
            ("4", "4 недели"),
            ("8", "8 недель"),
            ("12", "12 недель")
        ],
        validators=[DataRequired()]
    )

    training_place = SelectField(
        "Место тренировок",
        choices=[
            ("home", "Дома"),
            ("gym", "В тренажёрном зале")
        ],
        validators=[DataRequired()]
    )

    goal = SelectField(
        "Цель",
        choices=[
            ("weight_loss", "Снижение веса"),
            ("muscle_gain", "Набор мышечной массы"),
            ("maintenance", "Поддержание формы")
        ],
        validators=[DataRequired()]
    )

    submit = SubmitField("Рассчитать программу")


class ProgressForm(FlaskForm):
    week_number = IntegerField(
        "Номер недели",
        validators=[DataRequired(), NumberRange(min=1, max=200)]
    )

    weight = FloatField(
        "Текущий вес, кг",
        validators=[DataRequired(), NumberRange(min=30, max=300)]
    )

    note = TextAreaField(
        "Комментарий",
        validators=[Optional(), Length(max=500)]
    )

    submit = SubmitField("Добавить запись")