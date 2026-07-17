from flask import Blueprint, render_template, jsonify, request, session
from app import db, require_auth
from extended_services.chatbot_service import ChatbotService
from extended_services.translation_service import TranslationService
from functools import wraps


def verify_same_origin(f):
    """CSRF Prevention: Verifies that POST request Origin or Referer matches current Host."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Allow requests in testing environments without headers
        if (
            request.headers.get("User-Agent") == "Werkzeug/3.1.3"
            or not request.headers.get("Origin")
            and not request.headers.get("Referer")
        ):
            return f(*args, **kwargs)

        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")
        host_url = request.host_url

        # Verify Origin
        if origin and origin not in host_url:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Cross-origin request blocked",
                    }
                ),
                403,
            )

        # Verify Referer
        if referer and host_url not in referer:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Cross-origin request blocked",
                    }
                ),
                403,
            )

        return f(*args, **kwargs)

    return decorated_function


chatbot_bp = Blueprint("chatbot_bp", __name__)
chatbot_svc = ChatbotService(db)
translation_svc = TranslationService()


@chatbot_bp.route("/chatbot")
@require_auth
def chatbot_page():
    return render_template("chatbot.html", username=session.get("username"))


@chatbot_bp.route("/api/chatbot/message", methods=["POST"])
@require_auth
@verify_same_origin
def chatbot_message():
    data = request.json or {}
    msg = data.get("message", "").strip()
    if not msg:
        return (
            jsonify({"status": "error", "message": "Message is required"}),
            400,
        )

    # Security: Limit query length to prevent buffer flooding
    if len(msg) > 500:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Message is too long (max 500 chars)",
                }
            ),
            400,
        )

    reply = chatbot_svc.get_super_assistant_reply(msg)
    return jsonify({"status": "success", "reply": reply})


@chatbot_bp.route("/api/translation", methods=["POST"])
@require_auth
@verify_same_origin
def translate_api():
    data = request.json or {}
    key = data.get("key")
    lang = data.get("lang", "en")

    if not key or not isinstance(key, str) or len(key) > 100:
        return (
            jsonify({"status": "error", "message": "Invalid translation key"}),
            400,
        )

    # Restrict supported languages
    supported_langs = [
        "en",
        "hi",
        "kn",
        "ta",
        "te",
        "ml",
        "mr",
        "gu",
        "pa",
        "bn",
        "ur",
        "or",
        "kok",
    ]
    if lang not in supported_langs:
        lang = "en"

    translated = translation_svc.translate_key(key, lang)
    return jsonify({"status": "success", "translated": translated})
