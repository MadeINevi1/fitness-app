CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    full_name VARCHAR(100),
    age INTEGER,
    height NUMERIC(5,2),
    weight NUMERIC(5,2),
    gender VARCHAR(20),
    activity_level VARCHAR(50),
    training_level VARCHAR(50),
    workouts_per_week INTEGER,
    training_place VARCHAR(50),
    goal VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS fitness_results (
    result_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    calories NUMERIC(8,2),
    proteins NUMERIC(8,2),
    fats NUMERIC(8,2),
    carbs NUMERIC(8,2),
    training_plan TEXT,
    nutrition_plan TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);