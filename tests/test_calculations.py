from app.views import (
    calculate_bmr,
    calculate_calories,
    calculate_goal_summary,
    calculate_macros,
    generate_training_plan,
)


def test_calculate_bmr_for_male():
    assert calculate_bmr(weight=80, height=180, age=25, gender="male") == 1805


def test_calculate_bmr_for_female():
    assert calculate_bmr(weight=65, height=170, age=30, gender="female") == 1401.5


def test_calculate_calories_for_weight_loss():
    result = calculate_calories(
        bmr=1805,
        weight=80,
        activity_level="light",
        goal="weight_loss",
        workouts_per_week=3,
        training_level="beginner",
    )

    assert result["lifestyle_calories"] == 2436.75
    assert result["training_calories"] == 160.29
    assert result["maintenance_calories"] == 2597.04
    assert result["target_calories"] == 2207.48


def test_calculate_macros_for_weight_loss():
    proteins, fats, carbs = calculate_macros(
        calories=2207.48,
        weight=80,
        goal="weight_loss",
    )

    assert proteins == 160
    assert fats == 68.68
    assert carbs == 237.35


def test_goal_summary_uses_realistic_weight_loss_duration():
    summary = calculate_goal_summary(
        current_weight=100,
        target_weight=90,
        goal="weight_loss",
        selected_duration=8,
    )

    assert summary["weight_difference"] == 10
    assert summary["recommended_weeks"] == 15
    assert summary["weekly_rate"] == 0.7


def test_training_plan_contains_selected_program_parameters():
    plan = generate_training_plan(
        goal="muscle_gain",
        training_level="beginner",
        workouts_per_week=3,
        training_place="home",
        program_duration=8,
    )

    assert "8" in plan
    assert "3" in plan
    assert "День 1" in plan
