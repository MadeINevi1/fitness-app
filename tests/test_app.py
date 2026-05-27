from app import db as app_db


def register(client, email="student@example.com", password="12345"):
    return client.post(
        "/register",
        data={
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )


def login(client, email="student@example.com", password="12345"):
    return client.post(
        "/login",
        data={
            "email": email,
            "password": password,
        },
        follow_redirects=True,
    )


def test_api_calculate_returns_program_data(client):
    response = client.post(
        "/api/calculate",
        json={
            "age": 25,
            "height": 180,
            "weight": 80,
            "target_weight": 75,
            "gender": "male",
            "activity_level": "light",
            "training_level": "beginner",
            "workouts_per_week": "3",
            "program_duration": "8",
            "training_place": "home",
            "goal": "weight_loss",
        },
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["bmr"] == 1805
    assert data["calories"] == 2207.48
    assert data["proteins"] == 160
    assert "training_plan" in data
    assert "nutrition_plan" in data


def test_register_login_and_calculator_save_result(client):
    register_response = register(client)
    login_response = login(client)

    assert register_response.status_code == 200
    assert login_response.status_code == 200

    response = client.post(
        "/calculator",
        data={
            "full_name": "Student Test",
            "age": "25",
            "height": "180",
            "weight": "80",
            "target_weight": "75",
            "gender": "male",
            "activity_level": "light",
            "training_level": "beginner",
            "workouts_per_week": "3",
            "program_duration": "8",
            "training_place": "home",
            "goal": "weight_loss",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Индивидуальный план".encode("utf-8") in response.data

    conn = app_db.get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM fitness_results fr
        JOIN users u ON u.user_id = fr.user_id
        WHERE u.email = ?;
        """,
        ("student@example.com",)
    )
    result_count = cur.fetchone()[0]
    app_db.close_db_connection(conn)

    assert result_count == 1


def test_history_requires_login(client):
    response = client.get("/history", follow_redirects=True)

    assert response.status_code == 200
    assert "Вход".encode("utf-8") in response.data
