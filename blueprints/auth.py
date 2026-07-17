from typing import Union, Tuple
from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    Response,
)
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, limiter, USERNAME_PATTERN, sanitize_html

auth_bp = Blueprint("auth", __name__)


def normalize_username(raw_username: str) -> str:
    """Sanitizes and strips the user-supplied username."""
    return sanitize_html(raw_username or "").strip()


def is_valid_username(username: str) -> bool:
    """Verifies that the username strictly matches the alphanumeric regex pattern."""
    return bool(USERNAME_PATTERN.match(username))


@auth_bp.route("/")
@auth_bp.route("/portal")
def portal() -> Union[str, Response]:
    """Renders the login/registration gateway.

    If already authenticated, redirects the user to their appropriate dashboard.
    """
    if "username" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        return redirect(url_for("core.dashboard"))
    return render_template("portal.html")


@auth_bp.route("/api/auth/register", methods=["POST"])
@limiter.limit("3 per minute")
def register() -> Union[Response, Tuple[Response, int]]:
    """Registers a new user account inside the database fallback / Firestore.

    Validates that the username meets complexity format standards.
    """
    data = request.json or {}
    raw_username: str = str(data.get("username", ""))
    username: str = normalize_username(raw_username)
    password: str = str(data.get("password", ""))
    role: str = "attendee"

    if not username or not password:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Username and password are required",
                }
            ),
            400,
        )

    if raw_username != username or not is_valid_username(username):
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Username must be alphanumeric or contain only _ or -",
                }
            ),
            400,
        )

    password_hash = generate_password_hash(password)
    success = db.register_user(username, password_hash, role)
    if success:
        return jsonify(
            {"status": "success", "message": "User registered successfully"}
        )
    return (
        jsonify({"status": "error", "message": "Username already exists"}),
        400,
    )


@auth_bp.route("/api/auth/login", methods=["POST"])
@limiter.limit("6 per minute")
def login() -> Union[Response, Tuple[Response, int]]:
    """Logs the user into their session using password hash checks."""
    data = request.json or {}
    username: str = str(data.get("username", "") or "").strip()
    password: str = str(data.get("password", ""))

    if not username or not password:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Username and password are required",
                }
            ),
            400,
        )

    if not USERNAME_PATTERN.match(username):
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Invalid username format",
                }
            ),
            400,
        )

    user = db.get_user(username)
    if user and check_password_hash(user["password_hash"], password):
        session["username"] = user["username"]
        session["role"] = user["role"]
        return jsonify(
            {
                "status": "success",
                "username": user["username"],
                "role": user["role"],
                "redirect": (
                    url_for("admin.admin_dashboard")
                    if user["role"] == "admin"
                    else url_for("core.dashboard")
                ),
            }
        )
    return (
        jsonify(
            {"status": "error", "message": "Invalid username or password"}
        ),
        401,
    )


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout() -> Response:
    """Logs out the current session and returns redirect URL."""
    session.clear()
    return jsonify(
        {
            "status": "success",
            "message": "Logged out successfully",
            "redirect": url_for("auth.portal"),
        }
    )
