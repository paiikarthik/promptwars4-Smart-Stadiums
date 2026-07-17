from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, limiter, USERNAME_PATTERN, sanitize_html

auth_bp = Blueprint("auth", __name__)


def normalize_username(raw_username: str) -> str:
    return sanitize_html(raw_username or "").strip()


def is_valid_username(username: str) -> bool:
    return bool(USERNAME_PATTERN.match(username))


@auth_bp.route("/")
@auth_bp.route("/portal")
def portal():
    """Renders the login/registration gateway."""
    if "username" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        return redirect(url_for("core.dashboard"))
    return render_template("portal.html")


@auth_bp.route("/api/auth/register", methods=["POST"])
@limiter.limit("3 per minute")
def register():
    data = request.json or {}
    raw_username = data.get("username", "")
    username = normalize_username(raw_username)
    password = data.get("password", "")
    role = "attendee"

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
def login():
    data = request.json or {}
    username = (data.get("username", "") or "").strip()
    password = data.get("password", "")

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
def logout():
    session.clear()
    return jsonify(
        {
            "status": "success",
            "message": "Logged out successfully",
            "redirect": url_for("auth.portal"),
        }
    )
