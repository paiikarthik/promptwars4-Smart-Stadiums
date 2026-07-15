from flask import Blueprint, render_template, session
from app import require_auth

parking_bp = Blueprint("parking_bp", __name__)

@parking_bp.route("/parking-map")
@require_auth
def parking_map_page():
    return render_template("parking_map.html", username=session.get("username"))
