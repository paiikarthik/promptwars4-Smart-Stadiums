from flask import Blueprint, render_template, session
from app import require_auth

navigation_bp = Blueprint("navigation_bp", __name__)


@navigation_bp.route("/navigation")
@require_auth
def navigation_page():
    return render_template("navigation.html", username=session.get("username"))
