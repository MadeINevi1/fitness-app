from app import app, csrf
from app.views import (
    index_view,
    register_view,
    login_view,
    logout_view,
    home_view,
    calculator_view,
    history_view,
    history_detail_view,
    methodology_view,
    api_calculate_view,
    progress_latest_view,
    progress_view,
    delete_progress_record_view,
    delete_history_result_view
)


@app.route("/")
def index():
    return index_view()


@app.route("/register", methods=["GET", "POST"])
def register():
    return register_view()


@app.route("/login", methods=["GET", "POST"])
def login():
    return login_view()


@app.route("/logout")
def logout():
    return logout_view()


@app.route("/home")
def home():
    return home_view()


@app.route("/calculator", methods=["GET", "POST"])
def calculator():
    return calculator_view()


@app.route("/history")
def history():
    return history_view()


@app.route("/history/<int:result_id>")
def history_detail(result_id):
    return history_detail_view(result_id)


@app.route("/history/delete/<int:result_id>", methods=["POST"])
def delete_history_result(result_id):
    return delete_history_result_view(result_id)


@app.route("/methodology")
def methodology():
    return methodology_view()


@app.route("/progress")
def progress_latest():
    return progress_latest_view()


@app.route("/progress/<int:profile_id>", methods=["GET", "POST"])
def progress(profile_id):
    return progress_view(profile_id)


@app.route("/progress/<int:profile_id>/delete/<int:progress_id>", methods=["POST"])
def delete_progress_record(profile_id, progress_id):
    return delete_progress_record_view(profile_id, progress_id)


@app.route("/api/calculate", methods=["POST"])
@csrf.exempt
def api_calculate():
    return api_calculate_view()