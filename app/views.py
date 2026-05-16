from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
import math

from app.forms import RegistrationForm, LoginForm, FitnessForm, ProgressForm
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


def calculate_goal_summary(current_weight, target_weight, goal, selected_duration):
    current_weight = float(current_weight)
    target_weight = float(target_weight)
    selected_duration = int(selected_duration)

    weight_difference = round(abs(current_weight - target_weight), 2)

    if goal == "weight_loss":
        if target_weight >= current_weight:
            return {
                "current_weight": current_weight,
                "target_weight": target_weight,
                "weight_difference": 0,
                "recommended_weeks": selected_duration,
                "weekly_rate": 0,
                "description": (
                    "Для цели снижения веса желаемый вес должен быть меньше текущего. "
                    "Сейчас приложение будет использовать выбранный минимальный срок программы."
                )
            }

        recommended_rate = 0.7
        min_weeks = math.ceil(weight_difference / 1.0)
        max_weeks = math.ceil(weight_difference / 0.5)
        recommended_weeks = math.ceil(weight_difference / recommended_rate)

        return {
            "current_weight": current_weight,
            "target_weight": target_weight,
            "weight_difference": weight_difference,
            "recommended_weeks": max(recommended_weeks, selected_duration),
            "weekly_rate": recommended_rate,
            "description": (
                f"Для снижения веса на {weight_difference} кг рекомендуется постепенный подход.\n"
                f"Минимальный ориентировочный срок при быстром темпе: около {min_weeks} недель.\n"
                f"Более мягкий срок при медленном темпе: около {max_weeks} недель.\n"
                f"Оптимальный расчётный срок для программы: около {max(recommended_weeks, selected_duration)} недель.\n\n"
                "Рекомендуется отслеживать вес 1 раз в неделю. Если вес снижается слишком быстро, "
                "калорийность можно немного повысить. Если вес долго не меняется, можно скорректировать "
                "активность или питание."
            )
        }

    if goal == "muscle_gain":
        if target_weight <= current_weight:
            return {
                "current_weight": current_weight,
                "target_weight": target_weight,
                "weight_difference": 0,
                "recommended_weeks": selected_duration,
                "weekly_rate": 0,
                "description": (
                    "Для цели набора мышечной массы желаемый вес обычно должен быть выше текущего. "
                    "Сейчас приложение будет использовать выбранный минимальный срок программы."
                )
            }

        recommended_rate = 0.35
        recommended_weeks = math.ceil(weight_difference / recommended_rate)

        return {
            "current_weight": current_weight,
            "target_weight": target_weight,
            "weight_difference": weight_difference,
            "recommended_weeks": max(recommended_weeks, selected_duration),
            "weekly_rate": recommended_rate,
            "description": (
                f"Для набора примерно {weight_difference} кг рекомендуется постепенный подход.\n"
                f"Оптимальный расчётный срок: около {max(recommended_weeks, selected_duration)} недель.\n\n"
                "При наборе массы важно контролировать не только вес, но и качество питания, "
                "силовые показатели и восстановление."
            )
        }

    return {
        "current_weight": current_weight,
        "target_weight": target_weight,
        "weight_difference": weight_difference,
        "recommended_weeks": selected_duration,
        "weekly_rate": 0,
        "description": (
            "Для поддержания формы основная задача — сохранить стабильный вес и уровень активности. "
            "Программа строится на выбранный срок с акцентом на регулярность тренировок и сбалансированное питание."
        )
    }


def generate_training_plan(goal, training_level, workouts_per_week, training_place, program_duration):
    workouts_per_week = int(workouts_per_week)
    program_duration = int(program_duration)

    place_text = {
        "home": "дома",
        "gym": "в тренажёрном зале"
    }

    level_text = {
        "beginner": "начальный уровень",
        "intermediate": "средний уровень",
        "advanced": "опытный уровень"
    }

    goal_text = {
        "weight_loss": "снижение веса",
        "muscle_gain": "набор мышечной массы",
        "maintenance": "поддержание формы"
    }

    if training_place == "home":
        exercises_by_level = {
            "beginner": [
                "приседания без веса — 3 подхода по 12 повторений",
                "отжимания от пола или от опоры — 3 подхода по 8–10 повторений",
                "планка — 3 подхода по 30 секунд",
                "выпады — 3 подхода по 10 повторений на каждую ногу",
                "скручивания на пресс — 3 подхода по 15 повторений"
            ],
            "intermediate": [
                "приседания с рюкзаком — 4 подхода по 12 повторений",
                "классические отжимания — 4 подхода по 10–12 повторений",
                "болгарские выпады — 3 подхода по 10 повторений на каждую ногу",
                "планка с подъёмом ног — 3 подхода по 40 секунд",
                "берпи — 3 подхода по 10 повторений"
            ],
            "advanced": [
                "приседания на одной ноге с опорой — 4 подхода по 8 повторений",
                "отжимания с узкой постановкой рук — 4 подхода по 10 повторений",
                "прыжковые выпады — 4 подхода по 12 повторений",
                "берпи — 4 подхода по 12 повторений",
                "планка — 4 подхода по 60–90 секунд"
            ]
        }
    else:
        exercises_by_level = {
            "beginner": [
                "жим ногами — 3 подхода по 12 повторений",
                "жим в тренажёре сидя — 3 подхода по 10 повторений",
                "тяга верхнего блока — 3 подхода по 12 повторений",
                "гиперэкстензия — 3 подхода по 12 повторений",
                "скручивания на пресс — 3 подхода по 15 повторений"
            ],
            "intermediate": [
                "жим лёжа — 4 подхода по 8–10 повторений",
                "тяга горизонтального блока — 4 подхода по 10 повторений",
                "приседания со штангой — 4 подхода по 8–10 повторений",
                "румынская тяга — 3 подхода по 10 повторений",
                "жим гантелей сидя — 3 подхода по 10 повторений"
            ],
            "advanced": [
                "жим лёжа — 5 подходов по 5–8 повторений",
                "становая тяга — 4 подхода по 5–6 повторений",
                "приседания со штангой — 5 подходов по 5–8 повторений",
                "подтягивания — 4 подхода по максимуму",
                "армейский жим — 4 подхода по 6–8 повторений"
            ]
        }

    exercises = exercises_by_level.get(training_level, exercises_by_level["beginner"])

    if goal == "weight_loss":
        goal_description = (
            "Основная цель программы — повышение расхода энергии, снижение массы тела "
            "и улучшение общей выносливости."
        )
        cardio = "После основной тренировки рекомендуется выполнять 20–30 минут кардио в умеренном темпе."
        progression = (
            "Каждые 2–3 недели можно увеличивать длительность кардио на 5 минут "
            "или немного повышать общий объём тренировки."
        )
    elif goal == "muscle_gain":
        goal_description = (
            "Основная цель программы — увеличение мышечной массы за счёт силовых тренировок "
            "и постепенного повышения нагрузки."
        )
        cardio = "Кардио рекомендуется выполнять 1–2 раза в неделю в лёгком режиме, чтобы не мешать восстановлению."
        progression = (
            "Если все подходы выполняются уверенно, на следующей неделе можно увеличить рабочий вес "
            "или сложность упражнения на 2,5–5%."
        )
    else:
        goal_description = (
            "Основная цель программы — поддержание физической формы, укрепление основных групп мышц "
            "и сохранение стабильного уровня активности."
        )
        cardio = "Кардио рекомендуется выполнять 2 раза в неделю по 20 минут."
        progression = (
            "Нагрузку следует увеличивать постепенно, сохраняя комфортный уровень интенсивности."
        )

    if program_duration <= 4:
        stages = (
            "Структура программы:\n"
            "Неделя 1 — адаптация к нагрузке и отработка техники упражнений.\n"
            "Неделя 2 — закрепление режима тренировок.\n"
            "Неделя 3 — небольшое увеличение нагрузки.\n"
            "Неделя 4 — контроль результатов и корректировка дальнейшего плана."
        )
    elif program_duration <= 8:
        stages = (
            "Структура программы:\n"
            "Недели 1–2 — адаптация к нагрузке и изучение техники упражнений.\n"
            "Недели 3–4 — постепенное увеличение объёма тренировки.\n"
            "Недели 5–6 — повышение интенсивности и контроль восстановления.\n"
            "Недели 7–8 — закрепление результата и оценка изменений."
        )
    elif program_duration <= 12:
        stages = (
            "Структура программы:\n"
            "Недели 1–3 — адаптация организма к регулярным тренировкам.\n"
            "Недели 4–6 — постепенное увеличение нагрузки и объёма упражнений.\n"
            "Недели 7–9 — основной тренировочный этап с контролем прогресса.\n"
            "Недели 10–12 — закрепление результата и подготовка к следующему циклу."
        )
    else:
        part = max(program_duration // 4, 1)
        stages = (
            "Структура долгосрочной программы:\n"
            f"Недели 1–{part} — адаптация к режиму питания и регулярным тренировкам.\n"
            f"Недели {part + 1}–{part * 2} — основной этап снижения веса и закрепление привычек.\n"
            f"Недели {part * 2 + 1}–{part * 3} — контроль прогресса, корректировка нагрузки и питания.\n"
            f"Недели {part * 3 + 1}–{program_duration} — закрепление результата и переход к поддержанию формы."
        )

    if workouts_per_week == 2:
        weekly_split = (
            "Распределение тренировок по неделе:\n"
            "Тренировка 1 — всё тело, акцент на ноги и спину.\n"
            "Тренировка 2 — всё тело, акцент на грудь, плечи и пресс."
        )
    elif workouts_per_week == 3:
        weekly_split = (
            "Распределение тренировок по неделе:\n"
            "Тренировка 1 — ноги и пресс.\n"
            "Тренировка 2 — грудь и спина.\n"
            "Тренировка 3 — плечи, руки и лёгкое кардио."
        )
    elif workouts_per_week == 4:
        weekly_split = (
            "Распределение тренировок по неделе:\n"
            "Тренировка 1 — ноги.\n"
            "Тренировка 2 — грудь и трицепс.\n"
            "Тренировка 3 — спина и бицепс.\n"
            "Тренировка 4 — плечи, пресс и кардио."
        )
    else:
        weekly_split = (
            "Распределение тренировок по неделе:\n"
            "Тренировка 1 — ноги.\n"
            "Тренировка 2 — грудь.\n"
            "Тренировка 3 — спина.\n"
            "Тренировка 4 — плечи и руки.\n"
            "Тренировка 5 — кардио, пресс и восстановительная нагрузка."
        )

    exercises_text = "\n".join([f"- {exercise}" for exercise in exercises])

    return (
        f"Индивидуальная программа тренировок на {program_duration} недель.\n\n"
        f"Цель: {goal_text.get(goal, 'поддержание формы')}.\n"
        f"Уровень подготовки: {level_text.get(training_level, 'начальный уровень')}.\n"
        f"Место тренировок: {place_text.get(training_place, 'дома')}.\n"
        f"Количество тренировок: {workouts_per_week} раз(а) в неделю.\n\n"
        f"{goal_description}\n\n"
        f"{stages}\n\n"
        f"{weekly_split}\n\n"
        f"Основные упражнения:\n"
        f"{exercises_text}\n\n"
        f"{cardio}\n\n"
        f"Правило прогрессии:\n"
        f"{progression}"
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
        snack = "кефир, йогурт без сахара, фрукт или небольшая порция орехов"
        advice = "Желательно ограничить сладкие напитки, фастфуд и частые перекусы с высокой калорийностью."

    elif goal == "muscle_gain":
        goal_text = (
            "Цель питания — набор мышечной массы за счёт небольшого профицита калорий. "
            "Важно регулярно получать белок, сложные углеводы и достаточно энергии для восстановления."
        )
        breakfast = "овсянка с бананом, яйца, йогурт или творог"
        lunch = "рис или макароны из твёрдых сортов, курица или говядина, овощи"
        dinner = "рыба или мясо, картофель или крупа, овощной салат"
        snack = "творог, протеиновый йогурт, банан или бутерброд с нежирным мясом"
        advice = "Желательно распределять белок равномерно в течение дня и не пропускать приёмы пищи."

    else:
        goal_text = (
            "Цель питания — поддержание текущей формы и стабильной массы тела. "
            "Рацион должен быть сбалансированным без выраженного дефицита или избытка калорий."
        )
        breakfast = "каша, яйцо или творог, фрукт"
        lunch = "мясо или рыба, крупа, овощи"
        dinner = "лёгкий белковый продукт, овощи, небольшая порция гарнира"
        snack = "фрукт, йогурт, орехи или творог"
        advice = "Желательно придерживаться стабильного режима питания и контролировать качество продуктов."

    return (
        f"{goal_text}\n\n"
        f"Рекомендуемая суточная калорийность: {calories} ккал.\n"
        f"Рекомендуемое количество белков: {proteins} г.\n"
        f"Рекомендуемое количество жиров: {fats} г.\n"
        f"Рекомендуемое количество углеводов: {carbs} г.\n\n"
        f"Пример завтрака: {breakfast}.\n"
        f"Пример обеда: {lunch}.\n"
        f"Пример ужина: {dinner}.\n"
        f"Пример перекуса: {snack}.\n\n"
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
        goal_summary = calculate_goal_summary(
            current_weight=form.weight.data,
            target_weight=form.target_weight.data,
            goal=form.goal.data,
            selected_duration=form.program_duration.data
        )

        effective_duration = goal_summary["recommended_weeks"] or int(form.program_duration.data)

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
            training_place=form.training_place.data,
            program_duration=effective_duration
        )

        nutrition_plan = generate_nutrition_plan(
            goal=form.goal.data,
            calories=calories,
            proteins=proteins,
            fats=fats,
            carbs=carbs
        )

        conn = get_db_connection()
        profile_id = None

        if conn:
            cur = conn.cursor()

            try:
                cur.execute(
                    """
                    INSERT INTO user_profiles
                    (user_id, full_name, age, height, weight, target_weight, target_duration_weeks,
                     gender, activity_level, training_level, workouts_per_week, program_duration,
                     training_place, goal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        current_user.id,
                        form.full_name.data,
                        form.age.data,
                        form.height.data,
                        form.weight.data,
                        form.target_weight.data,
                        effective_duration,
                        form.gender.data,
                        form.activity_level.data,
                        form.training_level.data,
                        int(form.workouts_per_week.data),
                        int(form.program_duration.data),
                        form.training_place.data,
                        form.goal.data
                    )
                )

                profile_id = cur.lastrowid

                cur.execute(
                    """
                    INSERT INTO fitness_results
                    (user_id, profile_id, calories, proteins, fats, carbs, training_plan, nutrition_plan)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        current_user.id,
                        profile_id,
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
            nutrition_plan=nutrition_plan,
            goal_summary=goal_summary,
            profile_id=profile_id
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
                SELECT result_id, profile_id, calories, proteins, fats, carbs, created_at
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
                    "profile_id": row[1],
                    "calories": row[2],
                    "proteins": row[3],
                    "fats": row[4],
                    "carbs": row[5],
                    "created_at": row[6]
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
        target_weight = float(data.get("target_weight", weight))
        height = float(data.get("height"))
        age = int(data.get("age"))
        gender = data.get("gender")
        activity_level = data.get("activity_level")
        goal = data.get("goal")
        training_level = data.get("training_level")
        workouts_per_week = data.get("workouts_per_week")
        training_place = data.get("training_place")
        program_duration = data.get("program_duration", 8)

        goal_summary = calculate_goal_summary(
            current_weight=weight,
            target_weight=target_weight,
            goal=goal,
            selected_duration=program_duration
        )

        effective_duration = goal_summary["recommended_weeks"] or int(program_duration)

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
            training_place=training_place,
            program_duration=effective_duration
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
            "goal_summary": goal_summary,
            "training_plan": training_plan,
            "nutrition_plan": nutrition_plan
        })

    except Exception as e:
        return jsonify({
            "error": f"Ошибка обработки данных: {str(e)}"
        }), 400

@login_required
def progress_latest_view():
    conn = get_db_connection()

    if conn:
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT profile_id
                FROM fitness_results
                WHERE user_id = ? AND profile_id IS NOT NULL
                ORDER BY result_id DESC
                LIMIT 1;
                """,
                (current_user.id,)
            )

            row = cur.fetchone()

            if row:
                return redirect(url_for("progress", profile_id=row[0]))

        except Exception as e:
            print(f"Ошибка поиска последнего прогресса: {e}")
            flash("Не удалось открыть последний прогресс.", "danger")

        finally:
            close_db_connection(conn)

    flash("У вас пока нет расчёта с отслеживанием прогресса. Сначала выполните новый расчёт программы.", "warning")
    return redirect(url_for("calculator"))


@login_required
def progress_view(profile_id):
    form = ProgressForm()
    conn = get_db_connection()

    latest_profile = None
    progress_records = []
    progress_summary = None
    chart_labels = []
    chart_weights = []
    chart_plan_weights = []
    progress_message = None

    if conn:
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT profile_id, weight, target_weight, target_duration_weeks
                FROM user_profiles
                WHERE user_id = ? AND profile_id = ?;
                """,
                (current_user.id, profile_id)
            )

            profile_row = cur.fetchone()

            if profile_row:
                latest_profile = {
                    "profile_id": profile_row[0],
                    "start_weight": profile_row[1],
                    "target_weight": profile_row[2],
                    "target_duration_weeks": profile_row[3]
                }

            if not latest_profile:
                flash("Программа для отслеживания прогресса не найдена.", "warning")
                close_db_connection(conn)
                return redirect(url_for("history"))

            if form.validate_on_submit():
                cur.execute(
                    """
                    SELECT progress_id
                    FROM progress_records
                    WHERE user_id = ? AND profile_id = ? AND week_number = ?;
                    """,
                    (
                        current_user.id,
                        latest_profile["profile_id"],
                        form.week_number.data
                    )
                )

                existing_week = cur.fetchone()

                if existing_week:
                    flash("Запись за эту неделю уже существует. Укажите другой номер недели.", "warning")
                    return redirect(url_for("progress", profile_id=profile_id))

                cur.execute(
                    """
                    INSERT INTO progress_records (user_id, profile_id, week_number, weight, note)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (
                        current_user.id,
                        latest_profile["profile_id"],
                        form.week_number.data,
                        form.weight.data,
                        form.note.data
                    )
                )

                conn.commit()
                flash("Запись прогресса успешно добавлена.", "success")
                return redirect(url_for("progress", profile_id=profile_id))

            cur.execute(
                """
                SELECT progress_id, week_number, weight, note, created_at
                FROM progress_records
                WHERE user_id = ? AND profile_id = ?
                ORDER BY week_number ASC;
                """,
                (current_user.id, latest_profile["profile_id"])
            )

            rows = cur.fetchall()

            progress_records = [
                {
                    "progress_id": row[0],
                    "week_number": row[1],
                    "weight": row[2],
                    "note": row[3],
                    "created_at": row[4]
                }
                for row in rows
            ]

            initial_weight = latest_profile["start_weight"]
            target_weight = latest_profile["target_weight"]
            target_duration_weeks = latest_profile["target_duration_weeks"] or 1

            if progress_records:
                current_weight = progress_records[-1]["weight"]
                current_week = progress_records[-1]["week_number"] or 1
            else:
                current_weight = initial_weight
                current_week = 0

            total_change = round(current_weight - initial_weight, 2)

            if target_weight < initial_weight:
                goal_type = "weight_loss"
                completed = initial_weight - current_weight
                total_needed = initial_weight - target_weight
                remaining_to_target = round(current_weight - target_weight, 2)

            elif target_weight > initial_weight:
                goal_type = "muscle_gain"
                completed = current_weight - initial_weight
                total_needed = target_weight - initial_weight
                remaining_to_target = round(target_weight - current_weight, 2)

            else:
                goal_type = "maintenance"
                completed = 0
                total_needed = 0
                remaining_to_target = 0

            if total_needed > 0:
                progress_percent = round((completed / total_needed) * 100, 1)

                if progress_percent < 0:
                    progress_percent = 0

                if progress_percent > 100:
                    progress_percent = 100
            else:
                progress_percent = 0

            progress_summary = {
                "initial_weight": initial_weight,
                "current_weight": current_weight,
                "target_weight": target_weight,
                "total_change": total_change,
                "remaining_to_target": remaining_to_target,
                "progress_percent": progress_percent,
                "goal_type": goal_type,
                "target_duration_weeks": target_duration_weeks,
                "current_week": current_week
            }

            if progress_records:
                planned_step = (target_weight - initial_weight) / target_duration_weeks

                for record in progress_records:
                    week_number = record["week_number"] or 1

                    chart_labels.append(f"Неделя {week_number}")
                    chart_weights.append(record["weight"])

                    planned_weight = initial_weight + planned_step * (week_number - 1)
                    chart_plan_weights.append(round(planned_weight, 2))

                if len(progress_records) >= 2:
                    expected_weight_now = initial_weight + planned_step * (current_week - 1)
                    difference_from_plan = round(current_weight - expected_weight_now, 2)

                    if goal_type == "weight_loss":
                        if difference_from_plan < -0.5:
                            progress_message = {
                                "type": "success",
                                "text": (
                                    "Вы идёте быстрее планового темпа снижения веса. "
                                    "Важно следить за самочувствием и не снижать калорийность слишком резко."
                                )
                            }
                        elif difference_from_plan > 0.5:
                            progress_message = {
                                "type": "warning",
                                "text": (
                                    "Темп снижения веса ниже планового. "
                                    "Рекомендуется проверить соблюдение питания, активность и регулярность тренировок."
                                )
                            }
                        else:
                            progress_message = {
                                "type": "info",
                                "text": "Текущий темп снижения веса примерно соответствует плану."
                            }

                    elif goal_type == "muscle_gain":
                        if difference_from_plan > 0.5:
                            progress_message = {
                                "type": "success",
                                "text": (
                                    "Вес растёт быстрее планового темпа. "
                                    "Важно контролировать качество набора массы и не создавать слишком большой профицит калорий."
                                )
                            }
                        elif difference_from_plan < -0.5:
                            progress_message = {
                                "type": "warning",
                                "text": (
                                    "Темп набора массы ниже планового. "
                                    "Рекомендуется проверить калорийность питания, восстановление и прогрессию нагрузок."
                                )
                            }
                        else:
                            progress_message = {
                                "type": "info",
                                "text": "Текущий темп набора массы примерно соответствует плану."
                            }

                    else:
                        if abs(difference_from_plan) <= 1:
                            progress_message = {
                                "type": "info",
                                "text": "Вес остаётся примерно стабильным, что соответствует цели поддержания формы."
                            }
                        else:
                            progress_message = {
                                "type": "warning",
                                "text": "Вес заметно отклонился от исходного значения. Рекомендуется пересмотреть питание и активность."
                            }

        except Exception as e:
            print(f"Ошибка работы с прогрессом: {e}")
            flash("Не удалось загрузить или сохранить данные прогресса.", "danger")

        finally:
            close_db_connection(conn)

    return render_template(
        "progress.html",
        form=form,
        latest_profile=latest_profile,
        progress_records=progress_records,
        progress_summary=progress_summary,
        chart_labels=chart_labels,
        chart_weights=chart_weights,
        chart_plan_weights=chart_plan_weights,
        progress_message=progress_message
    )


@login_required
def delete_progress_record_view(profile_id, progress_id):
    conn = get_db_connection()

    if conn:
        cur = conn.cursor()

        try:
            cur.execute(
                """
                DELETE FROM progress_records
                WHERE progress_id = ? AND profile_id = ? AND user_id = ?;
                """,
                (progress_id, profile_id, current_user.id)
            )

            conn.commit()
            flash("Запись прогресса удалена.", "success")

        except Exception as e:
            print(f"Ошибка удаления записи прогресса: {e}")
            conn.rollback()
            flash("Не удалось удалить запись прогресса.", "danger")

        finally:
            close_db_connection(conn)

    return redirect(url_for("progress", profile_id=profile_id))


@login_required
def delete_history_result_view(result_id):
    conn = get_db_connection()

    if conn:
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT profile_id
                FROM fitness_results
                WHERE result_id = ? AND user_id = ?;
                """,
                (result_id, current_user.id)
            )

            row = cur.fetchone()

            profile_id = row[0] if row else None

            cur.execute(
                """
                DELETE FROM fitness_results
                WHERE result_id = ? AND user_id = ?;
                """,
                (result_id, current_user.id)
            )

            if profile_id:
                cur.execute(
                    """
                    DELETE FROM progress_records
                    WHERE profile_id = ? AND user_id = ?;
                    """,
                    (profile_id, current_user.id)
                )

                cur.execute(
                    """
                    DELETE FROM user_profiles
                    WHERE profile_id = ? AND user_id = ?;
                    """,
                    (profile_id, current_user.id)
                )

            conn.commit()
            flash("Расчёт и связанный с ним прогресс удалены.", "success")

        except Exception as e:
            print(f"Ошибка удаления расчёта: {e}")
            conn.rollback()
            flash("Не удалось удалить расчёт.", "danger")

        finally:
            close_db_connection(conn)

    return redirect(url_for("history"))