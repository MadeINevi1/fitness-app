from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
import math

from app.forms import RegistrationForm, LoginForm, FitnessForm, ProgressForm
from app.models import User, get_user_by_email
from app.db import get_db_connection, close_db_connection


def calculate_bmr(weight, height, age, gender):
    """
    Расчёт базового обмена веществ по формуле Mifflin–St Jeor.
    """
    if gender == "male":
        return 10 * weight + 6.25 * height - 5 * age + 5

    return 10 * weight + 6.25 * height - 5 * age - 161


def calculate_daily_training_calories(weight, goal, workouts_per_week, training_level):
    """
    Ориентировочная оценка среднего расхода энергии от будущих тренировок.
    Недельный расход от тренировок делится на 7 дней.
    """
    workouts_per_week = int(workouts_per_week)

    if goal == "weight_loss":
        calories_per_workout = weight * 5.5
    elif goal == "muscle_gain":
        calories_per_workout = weight * 4.5
    else:
        calories_per_workout = weight * 4.0

    intensity_factors = {
        "beginner": 0.85,
        "intermediate": 1.0,
        "advanced": 1.15,
    }

    intensity_factor = intensity_factors.get(training_level, 1.0)

    weekly_training_calories = (
        calories_per_workout
        * workouts_per_week
        * intensity_factor
    )

    daily_training_calories = weekly_training_calories / 7

    return daily_training_calories


def calculate_calories(
    bmr,
    weight,
    activity_level,
    goal,
    workouts_per_week,
    training_level
):
    """
    Итоговая логика:
    1. Считается базовый обмен.
    2. Учитывается повседневная активность вне тренировок.
    3. Отдельно добавляется средний расход от будущих тренировок.
    4. Получается калорийность поддержания.
    5. Калорийность корректируется под цель.
    """
    lifestyle_factors = {
        "sedentary": 1.20,
        "light": 1.35,
        "moderate": 1.50,
        "physical": 1.70,
        "heavy_physical": 1.90,

        # Старые значения оставлены на случай, если в базе или форме ещё есть low/medium/high.
        "low": 1.20,
        "medium": 1.50,
        "high": 1.70,
    }

    lifestyle_factor = lifestyle_factors.get(activity_level, 1.20)

    lifestyle_calories = bmr * lifestyle_factor

    training_calories = calculate_daily_training_calories(
        weight=weight,
        goal=goal,
        workouts_per_week=workouts_per_week,
        training_level=training_level,
    )

    maintenance_calories = lifestyle_calories + training_calories

    if goal == "weight_loss":
        target_calories = maintenance_calories * 0.85
    elif goal == "muscle_gain":
        target_calories = maintenance_calories * 1.08
    else:
        target_calories = maintenance_calories

    return {
        "target_calories": round(target_calories, 2),
        "maintenance_calories": round(maintenance_calories, 2),
        "lifestyle_calories": round(lifestyle_calories, 2),
        "training_calories": round(training_calories, 2),
    }


def calculate_macros(calories, weight, goal):
    """
    Расчёт БЖУ.
    Белки считаются от массы тела.
    Жиры считаются как доля от калорийности.
    Углеводы считаются с ограничением, чтобы не получались чрезмерные значения.
    """
    if goal == "weight_loss":
        protein_per_kg = 2.0
        fat_percent = 0.28
        min_carb_percent = 0.35
        max_carb_percent = 0.50
    elif goal == "muscle_gain":
        protein_per_kg = 1.8
        fat_percent = 0.27
        min_carb_percent = 0.40
        max_carb_percent = 0.55
    else:
        protein_per_kg = 1.6
        fat_percent = 0.30
        min_carb_percent = 0.40
        max_carb_percent = 0.55

    proteins = weight * protein_per_kg
    protein_calories = proteins * 4

    fats = (calories * fat_percent) / 9
    fat_calories = fats * 9

    carbs = (calories - protein_calories - fat_calories) / 4

    min_carbs = (calories * min_carb_percent) / 4
    max_carbs = (calories * max_carb_percent) / 4

    if carbs > max_carbs:
        carbs = max_carbs
        remaining_calories = calories - protein_calories - carbs * 4
        fats = remaining_calories / 9

    if carbs < min_carbs:
        carbs = min_carbs
        remaining_calories = calories - protein_calories - carbs * 4
        fats = remaining_calories / 9

    if fats < 0:
        fats = (calories * 0.20) / 9
        carbs = (calories - protein_calories - fats * 9) / 4

    return round(proteins, 2), round(fats, 2), round(carbs, 2)


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
                ),
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
                f"Оптимальный расчётный срок для программы: около "
                f"{max(recommended_weeks, selected_duration)} недель.\n\n"
                "Рекомендуется отслеживать вес 1 раз в неделю. Если вес снижается слишком быстро, "
                "калорийность можно немного повысить. Если вес долго не меняется, можно скорректировать "
                "активность или питание."
            ),
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
                ),
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
            ),
        }

    return {
        "current_weight": current_weight,
        "target_weight": target_weight,
        "weight_difference": weight_difference,
        "recommended_weeks": selected_duration,
        "weekly_rate": 0,
        "description": (
            "Для поддержания формы основная задача — сохранить стабильный вес и уровень активности. "
            "Программа строится на выбранный срок с акцентом на регулярность тренировок "
            "и сбалансированное питание."
        ),
    }


def get_training_parameters(goal, training_level):
    """
    Возвращает параметры нагрузки в зависимости от цели и уровня подготовки.
    """

    if training_level == "beginner":
        base = {
            "level_name": "начальный уровень",
            "sets_main": "2–3",
            "sets_accessory": "2",
            "rest_main": "60–90 секунд",
            "rest_accessory": "45–60 секунд",
            "intensity": (
                "умеренная интенсивность. Упражнения выполняются с запасом 2–3 повторения, "
                "без работы до отказа."
            ),
            "progression": (
                "Сначала нужно освоить технику. Увеличивать нагрузку можно только после того, "
                "как упражнение выполняется уверенно во всех подходах. Обычно достаточно повышать "
                "рабочий вес или сложность на 2–3%."
            ),
        }
    elif training_level == "intermediate":
        base = {
            "level_name": "средний уровень",
            "sets_main": "3–4",
            "sets_accessory": "2–3",
            "rest_main": "90–120 секунд",
            "rest_accessory": "60–90 секунд",
            "intensity": (
                "средняя интенсивность. Последние повторения должны выполняться с заметным усилием, "
                "но без нарушения техники."
            ),
            "progression": (
                "Если во всех подходах выполнена верхняя граница повторений, на следующей тренировке "
                "можно увеличить вес или сложность упражнения на 2,5–5%."
            ),
        }
    else:
        base = {
            "level_name": "опытный уровень",
            "sets_main": "4–5",
            "sets_accessory": "3–4",
            "rest_main": "120–180 секунд",
            "rest_accessory": "60–120 секунд",
            "intensity": (
                "повышенная интенсивность. Основные упражнения выполняются тяжело, но технически чисто. "
                "Работа до отказа допускается только в отдельных изолирующих упражнениях."
            ),
            "progression": (
                "Нагрузка увеличивается постепенно: через рост рабочего веса, количества повторений "
                "или общего тренировочного объёма. Рабочий вес обычно повышается на 2,5–5%, "
                "а при ухудшении восстановления объём нужно снизить."
            ),
        }

    if goal == "weight_loss":
        base.update({
            "goal_name": "снижение веса",
            "main_reps": "10–15",
            "accessory_reps": "12–15",
            "cardio": (
                "Кардио: 20–40 минут умеренной интенсивности 2–4 раза в неделю. "
                "Подойдут быстрая ходьба, велотренажёр, эллипс или лёгкий бег."
            ),
            "goal_focus": (
                "Акцент программы — увеличение общего расхода энергии, сохранение мышечной массы "
                "и регулярность тренировок."
            ),
        })
    elif goal == "muscle_gain":
        base.update({
            "goal_name": "набор мышечной массы",
            "main_reps": "6–10",
            "accessory_reps": "8–12",
            "cardio": (
                "Кардио: 1–2 лёгкие сессии по 15–20 минут в неделю. "
                "Кардио не должно мешать восстановлению после силовых тренировок."
            ),
            "goal_focus": (
                "Акцент программы — прогрессия силовой нагрузки, достаточный тренировочный объём "
                "и восстановление между занятиями."
            ),
        })
    else:
        base.update({
            "goal_name": "поддержание формы",
            "main_reps": "8–12",
            "accessory_reps": "10–15",
            "cardio": (
                "Кардио: 20–30 минут 1–2 раза в неделю для поддержки выносливости "
                "и общего уровня активности."
            ),
            "goal_focus": (
                "Акцент программы — поддержание силы, общей физической формы, мобильности "
                "и стабильного уровня активности."
            ),
        })

    return base


def make_exercise(name, sets, reps, rest, note=""):
    """
    Структура одного упражнения.
    """
    return {
        "name": name,
        "sets": sets,
        "reps": reps,
        "rest": rest,
        "note": note
    }


def get_workout_templates(training_place, training_level, goal, params):
    """
    Возвращает набор тренировочных дней.
    Упражнения отличаются по месту занятий и уровню подготовки.
    """

    main_sets = params["sets_main"]
    accessory_sets = params["sets_accessory"]
    main_reps = params["main_reps"]
    accessory_reps = params["accessory_reps"]
    rest_main = params["rest_main"]
    rest_accessory = params["rest_accessory"]

    if training_place == "gym":
        if training_level == "beginner":
            full_body_a = {
                "title": "Тренировка A — всё тело",
                "description": "Базовая тренировка для освоения техники и равномерной нагрузки на основные мышцы.",
                "exercises": [
                    make_exercise("Жим ногами в тренажёре", main_sets, main_reps, rest_main, "Основной акцент на мышцы ног."),
                    make_exercise("Тяга верхнего блока к груди", main_sets, main_reps, rest_main, "Упражнение для спины."),
                    make_exercise("Жим в тренажёре сидя", main_sets, main_reps, rest_main, "Грудь, плечи и трицепс."),
                    make_exercise("Сгибание ног в тренажёре", accessory_sets, accessory_reps, rest_accessory, "Задняя поверхность бедра."),
                    make_exercise("Планка", accessory_sets, "30–45 секунд", rest_accessory, "Мышцы корпуса."),
                ],
            }

            full_body_b = {
                "title": "Тренировка B — всё тело",
                "description": "Вторая тренировка недели с другим набором упражнений для снижения однообразия.",
                "exercises": [
                    make_exercise("Приседание с гантелью у груди", main_sets, main_reps, rest_main, "Ноги и ягодичные мышцы."),
                    make_exercise("Тяга горизонтального блока", main_sets, main_reps, rest_main, "Средняя часть спины."),
                    make_exercise("Жим гантелей лёжа", main_sets, main_reps, rest_main, "Грудные мышцы."),
                    make_exercise("Гиперэкстензия", accessory_sets, accessory_reps, rest_accessory, "Поясница и ягодичные мышцы."),
                    make_exercise("Скручивания на пресс", accessory_sets, accessory_reps, rest_accessory, "Мышцы живота."),
                ],
            }

            upper = full_body_a
            lower = full_body_b

        elif training_level == "intermediate":
            full_body_a = {
                "title": "Тренировка A — силовая база",
                "description": "Тренировка с акцентом на базовые многосуставные упражнения.",
                "exercises": [
                    make_exercise("Приседания со штангой", main_sets, main_reps, rest_main, "Основное упражнение для ног."),
                    make_exercise("Жим штанги лёжа", main_sets, main_reps, rest_main, "Грудь, плечи и трицепс."),
                    make_exercise("Тяга горизонтального блока", main_sets, main_reps, rest_main, "Упражнение для спины."),
                    make_exercise("Румынская тяга", accessory_sets, accessory_reps, rest_accessory, "Задняя поверхность бедра и ягодичные мышцы."),
                    make_exercise("Планка", accessory_sets, "45–60 секунд", rest_accessory, "Мышцы корпуса."),
                ],
            }

            full_body_b = {
                "title": "Тренировка B — силовая и вспомогательная нагрузка",
                "description": "Тренировка дополняет первый день и развивает остальные мышечные группы.",
                "exercises": [
                    make_exercise("Становая тяга в умеренном весе", main_sets, main_reps, rest_main, "Спина, ноги и корпус."),
                    make_exercise("Жим гантелей сидя", main_sets, main_reps, rest_main, "Плечи."),
                    make_exercise("Подтягивания или тяга верхнего блока", main_sets, main_reps, rest_main, "Широчайшие мышцы спины."),
                    make_exercise("Выпады с гантелями", accessory_sets, accessory_reps, rest_accessory, "Ноги и ягодицы."),
                    make_exercise("Подъём ног или скручивания на пресс", accessory_sets, accessory_reps, rest_accessory, "Мышцы живота."),
                ],
            }

            upper = {
                "title": "Тренировка — верх тела",
                "description": "Акцент на грудь, спину, плечи и руки.",
                "exercises": [
                    make_exercise("Жим штанги лёжа", main_sets, main_reps, rest_main, "Грудь и трицепс."),
                    make_exercise("Тяга горизонтального блока", main_sets, main_reps, rest_main, "Спина."),
                    make_exercise("Жим гантелей сидя", main_sets, main_reps, rest_main, "Плечи."),
                    make_exercise("Тяга верхнего блока к груди", accessory_sets, accessory_reps, rest_accessory, "Широчайшие мышцы спины."),
                    make_exercise("Подъём гантелей на бицепс", accessory_sets, accessory_reps, rest_accessory, "Изолирующее упражнение для бицепса."),
                    make_exercise("Разгибание рук на верхнем блоке на трицепс", accessory_sets, accessory_reps, rest_accessory, "Изолирующее упражнение для трицепса."),
                ],
            }

            lower = {
                "title": "Тренировка — низ тела",
                "description": "Акцент на ноги, ягодичные мышцы и корпус.",
                "exercises": [
                    make_exercise("Приседания со штангой", main_sets, main_reps, rest_main, "Квадрицепсы и ягодичные мышцы."),
                    make_exercise("Румынская тяга", main_sets, main_reps, rest_main, "Задняя поверхность бедра."),
                    make_exercise("Жим ногами в тренажёре", accessory_sets, accessory_reps, rest_accessory, "Дополнительная нагрузка на ноги."),
                    make_exercise("Сгибание ног в тренажёре", accessory_sets, accessory_reps, rest_accessory, "Задняя поверхность бедра."),
                    make_exercise("Подъём на носки стоя или сидя", accessory_sets, accessory_reps, rest_accessory, "Икроножные мышцы."),
                    make_exercise("Планка", accessory_sets, "45–60 секунд", rest_accessory, "Мышцы корпуса."),
                ],
            }

        else:
            full_body_a = {
                "title": "Тренировка A — тяжёлая силовая",
                "description": "Основной день с тяжёлыми многосуставными упражнениями.",
                "exercises": [
                    make_exercise("Приседания со штангой", main_sets, main_reps, rest_main, "Главное упражнение дня."),
                    make_exercise("Жим штанги лёжа", main_sets, main_reps, rest_main, "Грудь, плечи и трицепс."),
                    make_exercise("Подтягивания или тяга верхнего блока", main_sets, main_reps, rest_main, "Спина."),
                    make_exercise("Румынская тяга", accessory_sets, accessory_reps, rest_accessory, "Задняя поверхность бедра."),
                    make_exercise("Подъём ног в висе", accessory_sets, accessory_reps, rest_accessory, "Пресс."),
                ],
            }

            full_body_b = {
                "title": "Тренировка B — объёмная силовая",
                "description": "День с повышенным тренировочным объёмом и дополнительными упражнениями.",
                "exercises": [
                    make_exercise("Становая тяга", main_sets, main_reps, rest_main, "Спина, ноги и корпус."),
                    make_exercise("Армейский жим стоя", main_sets, main_reps, rest_main, "Плечи."),
                    make_exercise("Тяга штанги в наклоне", main_sets, main_reps, rest_main, "Спина."),
                    make_exercise("Болгарские выпады", accessory_sets, accessory_reps, rest_accessory, "Ноги и ягодицы."),
                    make_exercise("Планка с дополнительным весом", accessory_sets, "45–60 секунд", rest_accessory, "Мышцы корпуса."),
                ],
            }

            upper = {
                "title": "Тренировка — верх тела",
                "description": "Силовая тренировка для груди, спины, плеч и рук.",
                "exercises": [
                    make_exercise("Жим штанги лёжа", main_sets, main_reps, rest_main, "Грудь и трицепс."),
                    make_exercise("Подтягивания", main_sets, main_reps, rest_main, "Спина и бицепс."),
                    make_exercise("Армейский жим стоя", main_sets, main_reps, rest_main, "Плечи."),
                    make_exercise("Тяга штанги в наклоне", main_sets, main_reps, rest_main, "Спина."),
                    make_exercise("Подъём штанги на бицепс", accessory_sets, accessory_reps, rest_accessory, "Изолирующее упражнение для бицепса."),
                    make_exercise("Французский жим или разгибание рук на блоке на трицепс", accessory_sets, accessory_reps, rest_accessory, "Изолирующее упражнение для трицепса."),
                ],
            }

            lower = {
                "title": "Тренировка — низ тела",
                "description": "Тяжёлая тренировка для ног, ягодиц и корпуса.",
                "exercises": [
                    make_exercise("Приседания со штангой", main_sets, main_reps, rest_main, "Основное упражнение для ног."),
                    make_exercise("Становая тяга или румынская тяга", main_sets, main_reps, rest_main, "Задняя цепь: спина, ягодицы и бицепс бедра."),
                    make_exercise("Жим ногами в тренажёре", accessory_sets, accessory_reps, rest_accessory, "Дополнительный объём для ног."),
                    make_exercise("Болгарские выпады", accessory_sets, accessory_reps, rest_accessory, "Ноги, ягодицы и баланс."),
                    make_exercise("Подъём на носки стоя или сидя", accessory_sets, accessory_reps, rest_accessory, "Икроножные мышцы."),
                    make_exercise("Подъём ног в висе", accessory_sets, accessory_reps, rest_accessory, "Пресс."),
                ],
            }

    else:
        if training_level == "beginner":
            full_body_a = {
                "title": "Тренировка A — всё тело дома",
                "description": "Простая домашняя тренировка для освоения регулярной нагрузки.",
                "exercises": [
                    make_exercise("Приседания без веса", main_sets, main_reps, rest_main, "Ноги и ягодицы."),
                    make_exercise("Отжимания от опоры", main_sets, main_reps, rest_main, "Грудь и трицепс."),
                    make_exercise("Ягодичный мост", accessory_sets, accessory_reps, rest_accessory, "Ягодичные мышцы."),
                    make_exercise("Планка", accessory_sets, "20–40 секунд", rest_accessory, "Мышцы корпуса."),
                    make_exercise("Скручивания на пресс", accessory_sets, accessory_reps, rest_accessory, "Мышцы живота."),
                ],
            }

            full_body_b = {
                "title": "Тренировка B — всё тело дома",
                "description": "Вторая домашняя тренировка с акцентом на ноги, спину и корпус.",
                "exercises": [
                    make_exercise("Выпады назад", main_sets, main_reps, rest_main, "Ноги и ягодицы."),
                    make_exercise("Тяга рюкзака в наклоне", main_sets, main_reps, rest_main, "Спина и бицепс."),
                    make_exercise("Отжимания от пола или опоры", main_sets, main_reps, rest_main, "Грудь и трицепс."),
                    make_exercise("Упражнение «птица-собака»", accessory_sets, accessory_reps, rest_accessory, "Корпус и стабилизация."),
                    make_exercise("Боковая планка", accessory_sets, "20–30 секунд на сторону", rest_accessory, "Косые мышцы живота."),
                ],
            }

            upper = full_body_a
            lower = full_body_b

        elif training_level == "intermediate":
            full_body_a = {
                "title": "Тренировка A — силовая дома",
                "description": "Домашняя тренировка с использованием веса тела и подручного отягощения.",
                "exercises": [
                    make_exercise("Приседания с рюкзаком", main_sets, main_reps, rest_main, "Ноги."),
                    make_exercise("Отжимания от пола", main_sets, main_reps, rest_main, "Грудь и трицепс."),
                    make_exercise("Тяга рюкзака в наклоне", main_sets, main_reps, rest_main, "Спина и бицепс."),
                    make_exercise("Болгарские выпады", accessory_sets, accessory_reps, rest_accessory, "Ноги и ягодицы."),
                    make_exercise("Планка с касанием плеч", accessory_sets, accessory_reps, rest_accessory, "Мышцы корпуса."),
                ],
            }

            full_body_b = {
                "title": "Тренировка B — функциональная дома",
                "description": "Тренировка для силы, выносливости и контроля корпуса.",
                "exercises": [
                    make_exercise("Выпады вперёд или назад", main_sets, main_reps, rest_main, "Ноги."),
                    make_exercise("Отжимания с узкой постановкой рук", main_sets, main_reps, rest_main, "Трицепс и грудь."),
                    make_exercise("Ягодичный мост на одной ноге", accessory_sets, accessory_reps, rest_accessory, "Ягодицы."),
                    make_exercise("Берпи в умеренном темпе", accessory_sets, "8–12", rest_accessory, "Общая выносливость."),
                    make_exercise("Боковая планка", accessory_sets, "30–45 секунд", rest_accessory, "Мышцы корпуса."),
                ],
            }

            upper = {
                "title": "Тренировка — верх тела дома",
                "description": "Акцент на грудь, плечи, руки, спину и корпус.",
                "exercises": [
                    make_exercise("Отжимания от пола", main_sets, main_reps, rest_main, "Грудь и трицепс."),
                    make_exercise("Тяга рюкзака в наклоне", main_sets, main_reps, rest_main, "Спина и бицепс."),
                    make_exercise("Отжимания в положении «домик»", accessory_sets, accessory_reps, rest_accessory, "Плечи."),
                    make_exercise("Обратные отжимания от стула на трицепс", accessory_sets, accessory_reps, rest_accessory, "Трицепс."),
                    make_exercise("Планка", accessory_sets, "45–60 секунд", rest_accessory, "Мышцы корпуса."),
                ],
            }

            lower = {
                "title": "Тренировка — низ тела дома",
                "description": "Акцент на ноги, ягодицы и корпус.",
                "exercises": [
                    make_exercise("Приседания с рюкзаком", main_sets, main_reps, rest_main, "Ноги."),
                    make_exercise("Болгарские выпады", main_sets, main_reps, rest_main, "Ноги и ягодицы."),
                    make_exercise("Ягодичный мост на одной ноге", accessory_sets, accessory_reps, rest_accessory, "Ягодицы."),
                    make_exercise("Подъём на носки", accessory_sets, accessory_reps, rest_accessory, "Икроножные мышцы."),
                    make_exercise("Скручивания на пресс", accessory_sets, accessory_reps, rest_accessory, "Мышцы живота."),
                ],
            }

        else:
            full_body_a = {
                "title": "Тренировка A — сложная домашняя",
                "description": "Интенсивная домашняя тренировка для опытного пользователя.",
                "exercises": [
                    make_exercise("Приседания на одной ноге с опорой", main_sets, main_reps, rest_main, "Ноги и баланс."),
                    make_exercise("Отжимания с ногами на возвышении", main_sets, main_reps, rest_main, "Грудь, плечи и трицепс."),
                    make_exercise("Тяга тяжёлого рюкзака в наклоне", main_sets, main_reps, rest_main, "Спина и бицепс."),
                    make_exercise("Прыжковые выпады", accessory_sets, accessory_reps, rest_accessory, "Ноги и выносливость."),
                    make_exercise("Планка", accessory_sets, "60–90 секунд", rest_accessory, "Мышцы корпуса."),
                ],
            }

            full_body_b = {
                "title": "Тренировка B — интенсивная домашняя",
                "description": "Тренировка с повышенной плотностью и сложными упражнениями.",
                "exercises": [
                    make_exercise("Болгарские выпады с рюкзаком", main_sets, main_reps, rest_main, "Ноги."),
                    make_exercise("Отжимания с узкой постановкой рук", main_sets, main_reps, rest_main, "Трицепс и грудь."),
                    make_exercise("Берпи", accessory_sets, "10–15", rest_accessory, "Общая выносливость."),
                    make_exercise("Ягодичный мост на одной ноге", accessory_sets, accessory_reps, rest_accessory, "Ягодицы."),
                    make_exercise("Боковая планка", accessory_sets, "45–60 секунд", rest_accessory, "Мышцы корпуса."),
                ],
            }

            upper = full_body_a
            lower = full_body_b

    conditioning = {
        "title": "Кардио и восстановительная тренировка",
        "description": "День для повышения расхода энергии, выносливости и восстановления.",
        "exercises": [
            make_exercise("Быстрая ходьба или велотренажёр", "1", "20–40 минут", "по самочувствию", "Умеренная интенсивность."),
            make_exercise("Мобилизация плеч и таза", "2", "8–12 движений", "30 секунд", "Подготовка суставов."),
            make_exercise("Лёгкая растяжка", "1", "5–10 минут", "без отдыха", "Без боли и резких движений."),
        ],
    }

    return {
        "full_body_a": full_body_a,
        "full_body_b": full_body_b,
        "upper": upper,
        "lower": lower,
        "conditioning": conditioning,
    }


def build_week_plan(workouts_per_week, goal, templates):
    """
    Формирует недельный план в зависимости от количества тренировок.
    """

    workouts_per_week = int(workouts_per_week)

    if workouts_per_week == 2:
        return [
            templates["full_body_a"],
            templates["full_body_b"],
        ]

    if workouts_per_week == 3:
        if goal == "muscle_gain":
            return [
                templates["full_body_a"],
                templates["full_body_b"],
                templates["full_body_a"],
            ]

        return [
            templates["full_body_a"],
            templates["conditioning"],
            templates["full_body_b"],
        ]

    if workouts_per_week == 4:
        return [
            templates["upper"],
            templates["lower"],
            templates["upper"],
            templates["lower"],
        ]

    return [
        templates["upper"],
        templates["lower"],
        templates["upper"],
        templates["lower"],
        templates["conditioning"],
    ]


def format_workout_day(day_number, workout):
    """
    Превращает один тренировочный день в текст.
    """

    text = (
        f"День {day_number}. {workout['title']}\n"
        f"{workout['description']}\n\n"
        f"Разминка: 5–10 минут лёгкой активности, суставная гимнастика, "
        f"1–2 лёгких разминочных подхода перед первым упражнением.\n\n"
        f"Основная часть:\n"
    )

    for index, exercise in enumerate(workout["exercises"], start=1):
        note = f" {exercise['note']}" if exercise.get("note") else ""
        text += (
            f"{index}. {exercise['name']} — {exercise['sets']} подхода, "
            f"{exercise['reps']} повторений, отдых {exercise['rest']}.{note}\n"
        )

    text += (
        "\nЗаминка: 5 минут спокойной ходьбы или лёгкой растяжки.\n"
    )

    return text


def generate_training_plan(goal, training_level, workouts_per_week, training_place, program_duration):
    """
    Формирует подробную тренировочную программу.
    """

    workouts_per_week = int(workouts_per_week)
    program_duration = int(program_duration)

    place_text = {
        "home": "дома",
        "gym": "в тренажёрном зале",
    }

    params = get_training_parameters(goal, training_level)
    templates = get_workout_templates(training_place, training_level, goal, params)
    week_plan = build_week_plan(workouts_per_week, goal, templates)

    workout_days_text = "\n\n".join(
        format_workout_day(index, workout)
        for index, workout in enumerate(week_plan, start=1)
    )

    if program_duration <= 4:
        stages = (
            "Этапы программы:\n"
            "- Неделя 1: освоение техники и подбор комфортной нагрузки.\n"
            "- Неделя 2: закрепление режима тренировок.\n"
            "- Неделя 3: небольшое увеличение нагрузки или количества повторений.\n"
            "- Неделя 4: контроль результата и корректировка программы."
        )
    elif program_duration <= 8:
        stages = (
            "Этапы программы:\n"
            "- Недели 1–2: адаптация к нагрузке и отработка техники.\n"
            "- Недели 3–4: постепенное увеличение объёма тренировки.\n"
            "- Недели 5–6: повышение интенсивности при сохранении техники.\n"
            "- Недели 7–8: закрепление результата и анализ прогресса."
        )
    else:
        stages = (
            "Этапы программы:\n"
            "- Недели 1–3: адаптация и формирование стабильного режима.\n"
            "- Недели 4–6: увеличение тренировочного объёма.\n"
            "- Недели 7–9: основной этап прогрессии нагрузки.\n"
            "- Недели 10–12: закрепление результата и корректировка дальнейшего плана."
        )

    return (
        f"Индивидуальная программа тренировок на {program_duration} недель.\n\n"
        f"Цель: {params['goal_name']}.\n"
        f"Уровень подготовки: {params['level_name']}.\n"
        f"Место тренировок: {place_text.get(training_place, 'дома')}.\n"
        f"Количество тренировок: {workouts_per_week} раз(а) в неделю.\n\n"
        f"{params['goal_focus']}\n\n"
        f"Общая интенсивность: {params['intensity']}\n\n"
        f"{stages}\n\n"
        f"Недельный тренировочный план:\n\n"
        f"{workout_days_text}\n\n"
        f"Кардио-рекомендации:\n"
        f"{params['cardio']}\n\n"
        f"Правило прогрессии:\n"
        f"{params['progression']}\n\n"
        f"Контроль восстановления:\n"
        f"- Если сохраняется сильная мышечная боль, ухудшается сон или падает работоспособность, "
        f"следующую тренировку лучше сделать легче.\n"
        f"- Между тяжёлыми тренировками одной мышечной группы желательно оставлять не менее 48 часов.\n"
        f"- При боли в суставах, головокружении или резком ухудшении самочувствия тренировку нужно прекратить.\n\n"
        f"Критерий успешности:\n"
        f"Программа считается подходящей, если пользователь выполняет тренировки регулярно, "
        f"сохраняет технику упражнений и постепенно улучшает повторения, рабочий вес или общую выносливость."
    )


def generate_nutrition_plan(goal, calories, proteins, fats, carbs):
    """
    Формирование подробных рекомендаций по питанию.

    Здесь намеренно не задаётся жёсткое количество калорий на завтрак, обед и ужин,
    потому что приложение формирует рекомендации, а не точное меню по граммам.
    Пользователь получает ориентиры по продуктам, структуре рациона и вариантам блюд.
    """

    if goal == "weight_loss":
        strategy = (
            "Цель питания — постепенное снижение массы тела за счёт умеренного дефицита калорий. "
            "Главная задача — уменьшить общую калорийность рациона без слишком резких ограничений, "
            "сохранив достаточное количество белка, клетчатки и жидкости."
        )

        protein_sources = (
            "Источники белка: куриная грудка, индейка, нежирная говядина, рыба, яйца, творог, "
            "греческий йогурт без сахара, бобовые."
        )

        carb_sources = (
            "Источники углеводов: гречка, рис, овсянка, картофель, цельнозерновой хлеб, "
            "макароны из твёрдых сортов пшеницы, овощи, фрукты и ягоды."
        )

        fat_sources = (
            "Источники жиров: оливковое масло, орехи, авокадо, жирная рыба, семена. "
            "Количество жиров не следует снижать слишком сильно, так как они участвуют в обменных процессах."
        )

        meal_examples = (
            "Примеры вариантов питания:\n"
            "- Завтрак: овсянка с ягодами и творогом; или омлет с овощами; или греческий йогурт с фруктом.\n"
            "- Обед: курица или рыба с гречкой и овощным салатом; или индейка с рисом и овощами.\n"
            "- Ужин: рыба или творог с овощами; или нежирное мясо с салатом; или яйца с овощами.\n"
            "- Перекус: кефир, йогурт без сахара, фрукт, творог, небольшая порция орехов."
        )

        practical_rules = (
            "Практические правила:\n"
            "- В каждый основной приём пищи желательно добавлять источник белка.\n"
            "- Овощи лучше включать 1–2 раза в день для насыщения и нормальной работы пищеварения.\n"
            "- Сладкие напитки, частые перекусы и фастфуд лучше ограничить, так как они быстро повышают калорийность.\n"
            "- Если вес не снижается 2 недели подряд, можно уменьшить рацион на 100–150 ккал "
            "или немного увеличить ежедневную активность."
        )

    elif goal == "muscle_gain":
        strategy = (
            "Цель питания — набор мышечной массы за счёт небольшого профицита калорий. "
            "Важно не просто есть больше, а обеспечить организм достаточным количеством белка, "
            "углеводов для тренировок и жиров для нормального обмена веществ."
        )

        protein_sources = (
            "Источники белка: курица, индейка, говядина, рыба, яйца, творог, молочные продукты, "
            "бобовые, морепродукты."
        )

        carb_sources = (
            "Источники углеводов: рис, гречка, овсянка, картофель, макароны из твёрдых сортов, "
            "цельнозерновой хлеб, фрукты. Углеводы особенно важны до и после силовых тренировок."
        )

        fat_sources = (
            "Источники жиров: орехи, оливковое масло, авокадо, жирная рыба, семена, яйца. "
            "Жиры помогают поддерживать нормальный гормональный фон и общую калорийность рациона."
        )

        meal_examples = (
            "Примеры вариантов питания:\n"
            "- Завтрак: овсянка с бананом и яйцами; или творог с фруктами и орехами; или омлет с хлебом.\n"
            "- Обед: рис или макароны с курицей, говядиной или рыбой и овощами.\n"
            "- Ужин: мясо или рыба с картофелем, крупой или овощами.\n"
            "- Перекус: творог, йогурт, банан, бутерброд с нежирным мясом, орехи.\n"
            "- После тренировки: белковый продукт и источник углеводов, например творог с фруктом "
            "или курица с рисом."
        )

        practical_rules = (
            "Практические правила:\n"
            "- Белок должен присутствовать в каждом основном приёме пищи.\n"
            "- Углеводы лучше распределять вокруг тренировок, чтобы поддерживать энергию и восстановление.\n"
            "- Если вес не растёт 2–3 недели, можно добавить 100–200 ккал в сутки.\n"
            "- Если вес растёт слишком быстро, а силовые показатели почти не увеличиваются, "
            "профицит калорий лучше уменьшить."
        )

    else:
        strategy = (
            "Цель питания — поддержание формы, стабильного веса и нормального уровня энергии. "
            "Рацион должен быть сбалансированным: без выраженного дефицита и без постоянного переедания."
        )

        protein_sources = (
            "Источники белка: мясо, рыба, яйца, творог, йогурт без сахара, бобовые, морепродукты."
        )

        carb_sources = (
            "Источники углеводов: крупы, картофель, цельнозерновой хлеб, макароны из твёрдых сортов, "
            "овощи, фрукты и ягоды."
        )

        fat_sources = (
            "Источники жиров: растительные масла, орехи, семена, авокадо, жирная рыба, яйца."
        )

        meal_examples = (
            "Примеры вариантов питания:\n"
            "- Завтрак: каша с фруктом; или омлет с овощами; или творог с ягодами.\n"
            "- Обед: мясо или рыба с крупой и овощами.\n"
            "- Ужин: белковый продукт с овощами и небольшим количеством гарнира.\n"
            "- Перекус: фрукт, йогурт, кефир, творог, орехи."
        )

        practical_rules = (
            "Практические правила:\n"
            "- Следите за регулярностью питания и достаточным количеством белка.\n"
            "- Не обязательно строго считать каждый продукт, но важно контролировать общий баланс рациона.\n"
            "- Если вес постепенно увеличивается, можно немного уменьшить порции углеводов или жиров.\n"
            "- Если вес снижается без такой цели, можно добавить дополнительный перекус или увеличить порцию гарнира."
        )

    return (
        f"{strategy}\n\n"
        f"Расчётные ориентиры на сутки:\n"
        f"- Калорийность: {calories} ккал.\n"
        f"- Белки: {proteins} г.\n"
        f"- Жиры: {fats} г.\n"
        f"- Углеводы: {carbs} г.\n\n"
        f"{protein_sources}\n\n"
        f"{carb_sources}\n\n"
        f"{fat_sources}\n\n"
        f"{meal_examples}\n\n"
        f"{practical_rules}"
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

        calorie_result = calculate_calories(
            bmr=bmr,
            weight=form.weight.data,
            activity_level=form.activity_level.data,
            goal=form.goal.data,
            workouts_per_week=form.workouts_per_week.data,
            training_level=form.training_level.data,
        )

        calories = calorie_result["target_calories"]

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
                    (user_id, full_name, age, height, weight, target_weight,
                     target_duration_weeks, gender, activity_level, training_level,
                     workouts_per_week, program_duration, training_place, goal)
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
                    (user_id, profile_id, calories, proteins, fats, carbs,
                     training_plan, nutrition_plan)
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
                SELECT fr.result_id, fr.profile_id, up.full_name,
                       fr.calories, fr.proteins, fr.fats, fr.carbs, fr.created_at
                FROM fitness_results fr
                LEFT JOIN user_profiles up ON up.profile_id = fr.profile_id
                WHERE fr.user_id = ?
                ORDER BY fr.created_at DESC;
                """,
                (current_user.id,)
            )

            rows = cur.fetchall()

            results = [
                {
                    "result_id": row[0],
                    "profile_id": row[1],
                    "full_name": row[2] or "Не указано",
                    "calories": row[3],
                    "proteins": row[4],
                    "fats": row[5],
                    "carbs": row[6],
                    "created_at": row[7].strftime("%d.%m.%Y %H:%M")
                    if hasattr(row[7], "strftime")
                    else str(row[7]).split(".")[0]
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
                    "created_at": row[7].strftime("%d.%m.%Y %H:%M")
                    if hasattr(row[7], "strftime")
                    else str(row[7]).split(".")[0]
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

        calorie_result = calculate_calories(
            bmr=bmr,
            weight=weight,
            activity_level=activity_level,
            goal=goal,
            workouts_per_week=workouts_per_week,
            training_level=training_level,
        )

        calories = calorie_result["target_calories"]

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
            "maintenance_calories": calorie_result["maintenance_calories"],
            "lifestyle_calories": calorie_result["lifestyle_calories"],
            "training_calories": calorie_result["training_calories"],
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
                    INSERT INTO progress_records
                    (user_id, profile_id, week_number, weight, note)
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
