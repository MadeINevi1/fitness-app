from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FloatField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange


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
        "Вес, кг",
        validators=[DataRequired(), NumberRange(min=30, max=250)]
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