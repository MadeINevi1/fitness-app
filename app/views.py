from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from app.forms import RegistrationForm, LoginForm, FitnessForm
from app.models import User, get_user_by_email
from app.db import get_db_connection, close_db_connection


def calculate_bmr(weight, height, age, gender):
    if gender == "male":
        return 10 * weight + 6.25 * height - 5 * age + 5
    else:
        return 10 * weight + 6.25 * height - 5 * age - 161


def calculate_calories(bmr, activity_level, goal):
    activity_factors = {
        "low": 1.2,
        "medium": 1.55,
        "high": 1.725
    }

    calories = bmr * activity_factors.get(activity_level, 1.2)

    if goal == "weight_loss":
        calories -= 300
    elif goal == "muscle_gain":
        calories += 300

    return round(calories, 2)


def calculate_macros(calories, weight, goal):
    if goal == "weight_loss":
        protein_per_kg = 2.0
        fat_percent = 0.25
    elif goal == "muscle_gain":
        protein_per_kg = 1.8
        fat_percent = 0.25
    else:
        protein_per_kg = 1.5
        fat_percent = 0.25

    proteins = round(weight * protein_per_kg, 2)

    protein_calories = proteins * 4
    fat_calories = calories * fat_percent
    fats = round(fat_calories / 9, 2)

    carb_calories = calories - protein_calories - fat_calories
    carbs = round(carb_calories / 4, 2)

    return proteins, fats, carbs

def generate_training_plan(goal, training_level, workouts_per_week, training_place):
    place_text = {
        "home": "дома",
        "gym": "в тренажёрном зале"
    }

    level_text = {
        "beginner": "для новичка",
        "intermediate": "для среднего уровня",
        "advanced": "для опытного пользователя"
    }

    if training_place == "home":
        base_exercises = {
            "beginner": [
                "приседания без веса",
                "отжимания от пола или от опоры",
                "планка",
                "выпады",
                "скручивания на пресс"
            ],
            "intermediate": [
                "приседания с рюкзаком",
                "классические отжимания",
                "болгарские выпады",
                "планка с подъёмом ног",
                "берпи"
            ],
            "advanced": [
                "пистолетики с опорой",
                "отжимания с узкой постановкой рук",
                "прыжковые выпады",
                "берпи",
                "планка 60–90 секунд"
            ]
        }
    else:
        base_exercises = {
            "beginner": [
                "жим в тренажёре",
                "тяга верхнего блока",
                "жим ногами",
                "гиперэкстензия",
                "скручивания на пресс"
            ],
            "intermediate": [
                "жим лёжа",
                "тяга горизонтального блока",
                "приседания со штангой",
                "румынская тяга",
                "жим гантелей сидя"
            ],
            "advanced": [
                "жим лёжа",
                "становая тяга",
                "приседания со штангой",
                "подтягивания",
                "армейский жим"
            ]
        }

    exercises = base_exercises.get(training_level, base_exercises["beginner"])

    if goal == "weight_loss":
        goal_text = (
            "Основной акцент: снижение веса, повышение общей активности "
            "и увеличение расхода энергии."
        )
        cardio_text = "После силовой части рекомендуется 15–25 минут кардио."
    elif goal == "muscle_gain":
        goal_text = (
            "Основной акцент: набор мышечной массы, постепенное увеличение нагрузки "
            "и соблюдение техники выполнения упражнений."
        )
        cardio_text = "Кардио можно выполнять 1–2 раза в неделю в лёгком режиме."
    else:
        goal_text = (
            "Основной акцент: поддержание физической формы, развитие выносливости "
            "и укрепление основных групп мышц."
        )
        cardio_text = "Кардио рекомендуется 2 раза в неделю по 20 минут."

    exercises_text = ", ".join(exercises)

    return (
        f"Рекомендуется тренироваться {workouts_per_week} раз(а) в неделю {place_text.get(training_place, 'дома')}. "
        f"Программа составлена {level_text.get(training_level, 'для новичка')}. "
        f"{goal_text} "
        f"Основные упражнения: {exercises_text}. "
        f"{cardio_text}"
    )


def generate_nutrition_plan(goal, calories, proteins, fats, carbs):
    if goal == "weight_loss":
        goal_text = (
            "Цель питания — снижение массы тела за счёт умеренного дефицита калорий. "
            "Рацион должен сохранять достаточное количество белка, чтобы поддерживать мышечную массу."
        )
        breakfast = "овсяная каша, яйцо или творог, фрукт"
        lunch = "куриная грудка или рыба, гречка или рис, овощной салат"
        dinner = "рыба, творог или нежирное мясо, овощи"
        advice = "Желательно ограничить сладкие напитки, фастфуд и частые перекусы с высокой калорийностью."

    elif goal == "muscle_gain":
        goal_text = (
            "Цель питания — набор мышечной массы за счёт небольшого профицита калорий. "
            "Важно регулярно получать белок, сложные углеводы и достаточно энергии для восстановления."
        )
        breakfast = "овсянка с бананом, яйца, йогурт или творог"
        lunch = "рис или макароны из твёрдых сортов, курица или говядина, овощи"
        dinner = "рыба или мясо, картофель или крупа, овощной салат"
        advice = "Желательно распределять белок равномерно в течение дня и не пропускать приёмы пищи."

    else:
        goal_text = (
            "Цель питания — поддержание текущей формы и стабильной массы тела. "
            "Рацион должен быть сбалансированным без выраженного дефицита или избытка калорий."
        )
        breakfast = "каша, яйцо или творог, фрукт"
        lunch = "мясо или рыба, крупа, овощи"
        dinner = "лёгкий белковый продукт, овощи, небольшая порция гарнира"
        advice = "Желательно придерживаться стабильного режима питания и контролировать качество продуктов."

    return (
        f"{goal_text}\n\n"
        f"Рекомендуемая суточная калорийность: {calories} ккал.\n"
        f"Рекомендуемое количество белков: {proteins} г.\n"
        f"Рекомендуемое количество жиров: {fats} г.\n"
        f"Рекомендуемое количество углеводов: {carbs} г.\n\n"
        f"Пример завтрака: {breakfast}.\n"
        f"Пример обеда: {lunch}.\n"
        f"Пример ужина: {dinner}.\n\n"
        f"{advice}"
    )


def index_view():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    return render_template("index.html")


def register_view():
    form = RegistrationForm()

    if form.validate_on_submit():
        existing_user = get_user_by_email(form.email.data)

        if existing_user:
            flash("Пользователь с таким email уже существует.", "danger")
            return render_template("register.html", form=form)

        user = User.register_user(
            email=form.email.data,
            password=form.password.data
        )

        if user:
            flash("Регистрация выполнена успешно. Теперь войдите в систему.", "success")
            return redirect(url_for("login"))

        flash("Ошибка регистрации. Попробуйте снова.", "danger")

    return render_template("register.html", form=form)


def login_view():
    form = LoginForm()

    if form.validate_on_submit():
        user = get_user_by_email(form.email.data)

        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Вы успешно вошли в систему.", "success")
            return redirect(url_for("home"))

        flash("Неверный email или пароль.", "danger")

    return render_template("login.html", form=form)


@login_required
def logout_view():
    logout_user()
    flash("Вы вышли из системы.", "success")
    return redirect(url_for("login"))


@login_required
def home_view():
    return render_template("home.html")


@login_required
def calculator_view():
    form = FitnessForm()

    if form.validate_on_submit():
        bmr = calculate_bmr(
            weight=form.weight.data,
            height=form.height.data,
            age=form.age.data,
            gender=form.gender.data
        )

        calories = calculate_calories(
            bmr=bmr,
            activity_level=form.activity_level.data,
            goal=form.goal.data
        )

        proteins, fats, carbs = calculate_macros(
            calories=calories,
            weight=form.weight.data,
            goal=form.goal.data
        )

        training_plan = generate_training_plan(
            goal=form.goal.data,
            training_level=form.training_level.data,
            workouts_per_week=form.workouts_per_week.data,
            training_place=form.training_place.data
        )

        nutrition_plan = generate_nutrition_plan(
            goal=form.goal.data,
            calories=calories,
            proteins=proteins,
            fats=fats,
            carbs=carbs
        )

        conn = get_db_connection()

        if conn:
            cur = conn.cursor()

            try:
                cur.execute(
                    """
                    INSERT INTO user_profiles
                    (user_id, full_name, age, height, weight, gender, activity_level, training_level, workouts_per_week, training_place, goal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        current_user.id,
                        form.full_name.data,
                        form.age.data,
                        form.height.data,
                        form.weight.data,
                        form.gender.data,
                        form.activity_level.data,
                        form.training_level.data,
                        int(form.workouts_per_week.data),
                        form.training_place.data,
                        form.goal.data
                    )
                )

                cur.execute(
                    """
                    INSERT INTO fitness_results
                    (user_id, calories, proteins, fats, carbs, training_plan, nutrition_plan)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        current_user.id,
                        calories,
                        proteins,
                        fats,
                        carbs,
                        training_plan,
                        nutrition_plan
                    )
                )

                conn.commit()

            except Exception as e:
                print(f"Ошибка сохранения результата: {e}")
                conn.rollback()
                flash("Результат рассчитан, но не был сохранён в базе данных.", "warning")

            finally:
                close_db_connection(conn)

        return render_template(
            "result.html",
            calories=calories,
            proteins=proteins,
            fats=fats,
            carbs=carbs,
            training_plan=training_plan,
            nutrition_plan=nutrition_plan
        )

    return render_template("calculator.html", form=form)

@login_required
def history_view():
    conn = get_db_connection()
    results = []

    if conn:
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT result_id, calories, proteins, fats, carbs, created_at
                FROM fitness_results
                WHERE user_id = ?
                ORDER BY created_at DESC;
                """,
                (current_user.id,)
            )

            rows = cur.fetchall()

            results = [
                {
                    "result_id": row[0],
                    "calories": row[1],
                    "proteins": row[2],
                    "fats": row[3],
                    "carbs": row[4],
                    "created_at": row[5]
                }
                for row in rows
            ]

        except Exception as e:
            print(f"Ошибка получения истории расчётов: {e}")
            flash("Не удалось загрузить историю расчётов.", "danger")

        finally:
            close_db_connection(conn)

    return render_template("history.html", results=results)

@login_required
def history_detail_view(result_id):
    conn = get_db_connection()
    result = None

    if conn:
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT result_id, calories, proteins, fats, carbs,
                       training_plan, nutrition_plan, created_at
                FROM fitness_results
                WHERE result_id = ? AND user_id = ?;
                """,
                (result_id, current_user.id)
            )

            row = cur.fetchone()

            if row:
                result = {
                    "result_id": row[0],
                    "calories": row[1],
                    "proteins": row[2],
                    "fats": row[3],
                    "carbs": row[4],
                    "training_plan": row[5],
                    "nutrition_plan": row[6],
                    "created_at": row[7]
                }
            else:
                flash("Расчёт не найден.", "warning")
                return redirect(url_for("history"))

        except Exception as e:
            print(f"Ошибка получения подробного расчёта: {e}")
            flash("Не удалось загрузить подробную информацию о расчёте.", "danger")
            return redirect(url_for("history"))

        finally:
            close_db_connection(conn)

    return render_template("history_detail.html", result=result)

def methodology_view():
    return render_template("methodology.html")

def api_calculate_view():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Данные не были переданы"
        }), 400

    try:
        weight = float(data.get("weight"))
        height = float(data.get("height"))
        age = int(data.get("age"))
        gender = data.get("gender")
        activity_level = data.get("activity_level")
        goal = data.get("goal")
        training_level = data.get("training_level")
        workouts_per_week = data.get("workouts_per_week")
        training_place = data.get("training_place")

        bmr = calculate_bmr(
            weight=weight,
            height=height,
            age=age,
            gender=gender
        )

        calories = calculate_calories(
            bmr=bmr,
            activity_level=activity_level,
            goal=goal
        )

        proteins, fats, carbs = calculate_macros(
            calories=calories,
            weight=weight,
            goal=goal
        )

        training_plan = generate_training_plan(
            goal=goal,
            training_level=training_level,
            workouts_per_week=workouts_per_week,
            training_place=training_place
        )

        nutrition_plan = generate_nutrition_plan(
            goal=goal,
            calories=calories,
            proteins=proteins,
            fats=fats,
            carbs=carbs
        )

        return jsonify({
            "bmr": round(bmr, 2),
            "calories": calories,
            "proteins": proteins,
            "fats": fats,
            "carbs": carbs,
            "training_plan": training_plan,
            "nutrition_plan": nutrition_plan
        })

    except Exception as e:
        return jsonify({
            "error": f"Ошибка обработки данных: {str(e)}"
        }), 400