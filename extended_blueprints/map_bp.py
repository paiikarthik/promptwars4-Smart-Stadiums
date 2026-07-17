from flask import Blueprint, render_template, session
from app import require_auth

map_bp = Blueprint("map_bp", __name__)


@map_bp.route("/map")
@require_auth
def map_page() -> str:
    """Renders the interactive 3D/2D stadium navigation map page.

    Returns:
        str: Rendered HTML template.
    """
    return render_template(
        "stadium_map.html", username=session.get("username")
    )
