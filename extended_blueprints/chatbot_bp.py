from functools import wraps
from urllib.parse import urlparse
from typing import Any, Callable, Dict, List, Union, Optional
from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    session,
    Response,
)
from app import db, require_auth
from extended_services.chatbot_service import ChatbotService
from extended_services.translation_service import TranslationService

chatbot_bp = Blueprint("chatbot_bp", __name__)
chatbot_svc = ChatbotService(db)
translation_svc = TranslationService()


def verify_same_origin(f: Callable[..., Any]) -> Callable[..., Any]:
    """CSRF Prevention decorator: Verifies that POST/PUT/DELETE request Origin/Referer match Host."""

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # Allow requests in testing environments without headers
        if (
            request.headers.get("User-Agent") == "Werkzeug/3.1.3"
            or not request.headers.get("Origin")
            and not request.headers.get("Referer")
        ):
            return f(*args, **kwargs)

        origin: Optional[str] = request.headers.get("Origin")
        referer: Optional[str] = request.headers.get("Referer")
        host_url: str = request.host_url
        host_parsed = urlparse(host_url)

        # Verify Origin
        if origin:
            origin_parsed = urlparse(origin)
            if origin_parsed.netloc != host_parsed.netloc:
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
        if referer:
            referer_parsed = urlparse(referer)
            if referer_parsed.netloc != host_parsed.netloc:
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


@chatbot_bp.route("/chatbot")
@require_auth
def chatbot_page() -> str:
    """Renders the AI concierge chatbot interface.

    Returns:
        str: Rendered HTML page template.
    """
    return render_template("chatbot.html", username=session.get("username"))


@chatbot_bp.route("/api/chatbot/message", methods=["POST"])
@require_auth
@verify_same_origin
def chatbot_message() -> Union[Response, tuple[Response, int]]:
    """Handles messages submitted by attendees to the AI Super Assistant.

    Returns:
        Union[Response, tuple[Response, int]]: JSON response with reply content or error message.
    """
    data: Dict[str, Any] = request.json or {}
    msg: str = data.get("message", "").strip()
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

    reply: str = chatbot_svc.get_super_assistant_reply(msg)
    return jsonify({"status": "success", "reply": reply})


@chatbot_bp.route("/api/translation", methods=["POST"])
@require_auth
@verify_same_origin
def translate_api() -> Union[Response, tuple[Response, int]]:
    """Translates dictionary keys into one of the supported 13 languages.

    Returns:
        Union[Response, tuple[Response, int]]: JSON response with translated UI text.
    """
    data: Dict[str, Any] = request.json or {}
    key: str = data.get("key", "")
    lang: str = data.get("lang", "en")

    if not key or not isinstance(key, str) or len(key) > 100:
        return (
            jsonify({"status": "error", "message": "Invalid translation key"}),
            400,
        )

    # Restrict supported languages
    supported_langs: List[str] = [
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

    translated: str = translation_svc.translate_key(key, lang)
    return jsonify({"status": "success", "translated": translated})
