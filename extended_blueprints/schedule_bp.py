from flask import Blueprint, render_template, session
from app import require_auth

schedule_bp = Blueprint("schedule_bp", __name__)

@schedule_bp.route("/schedule")
@require_auth
def schedule_page():
    return render_template("schedule.html", username=session.get("username"))
