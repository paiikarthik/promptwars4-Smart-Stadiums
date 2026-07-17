from flask import Blueprint, render_template, session
from app import require_auth

navigation_bp = Blueprint("navigation_bp", __name__)


@navigation_bp.route("/navigation")
@require_auth
def navigation_page() -> str:
    """Renders the step-by-step route planning navigation helper.

    Returns:
        str: Rendered HTML template.
    """
    return render_template("navigation.html", username=session.get("username"))
