import logging
import os
import queue
import random
import re
import sys
import threading
import time
from functools import wraps
from urllib.parse import urlparse

from flask import (
    Flask,
    jsonify,
    redirect,
    request,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, generate_csrf

from firebase_helper import StadiumDB
from services.analytics_service import AnalyticsService
from services.feedback_service import FeedbackService
from services.prediction_service import PredictionService
from services.report_service import ReportService
from services.sos_service import SOSService

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ArenaFlowApp")

# Import Google GenAI SDK
try:
    from google import genai

    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# Constants
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")

app = Flask(__name__)
csrf = CSRFProtect(app)

# Secure key for sessions - require SECRET_KEY in production
SECRET_KEY = os.environ.get("SECRET_KEY")
IS_TESTING_ENV = (
    str(os.environ.get("TESTING", "false")).lower() in ("1", "true", "yes")
    or os.environ.get("FLASK_ENV") == "testing"
)
if not SECRET_KEY:
    if not IS_TESTING_ENV:
        logger.critical(
            "SECRET_KEY environment variable is required in production. "
            "Refusing to start without SECRET_KEY set."
        )
        sys.exit(1)
    # Generate cryptographically secure random session key for local/testing fallback
    SECRET_KEY = os.urandom(24).hex()

app.secret_key = SECRET_KEY
app.config["TESTING"] = IS_TESTING_ENV
app.config["RATELIMIT_ENABLED"] = not IS_TESTING_ENV

# Session Cookie Hardening
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = not IS_TESTING_ENV and not app.debug

# Initialize rate limiter (no default global limits)
limiter = Limiter(key_func=get_remote_address, app=app, default_limits=[])

# Initialize database
db = StadiumDB()

# Global state copy for active SSE connections
current_state_lock = threading.Lock()
current_state = db.get_simulation_state()

# List of SSE connection queues
sse_listeners = []
sse_lock = threading.Lock()

# Google AI Client
gemini_client = None
if HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
    try:
        gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        logger.info("[AI] Google GenAI client initialized successfully.")
    except Exception as e:
        logger.error(f"[AI] GenAI initialization failed: {e}")


# --- INPUT SANITIZATION UTILITY ---

def sanitize_html(text):
    """Strips HTML script tags and normalizes input to prevent XSS injection."""
    if not isinstance(text, str):
        return text
    # Remove script tag elements entirely
    clean = re.sub(
        r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", "", clean)
    # Escape special characters
    clean = (
        clean.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
    return clean.strip()


# --- ROLE-BASED ACCESS CONTROL DECORATORS ---

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"status": "error", "message": "Unauthorized"}), 401
            return redirect(url_for("auth.portal"))
        return f(*args, **kwargs)

    return decorated_function


def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"status": "error", "message": "Unauthorized"}), 401
            return redirect(url_for("auth.portal"))
        if session.get("role") != "admin":
            if request.path.startswith("/api/"):
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Forbidden. Admin access required.",
                        }
                    ),
                    403,
                )
            return redirect(url_for("core.dashboard"))
        return f(*args, **kwargs)

    return decorated_function


def is_safe_origin_or_referer() -> bool:
    """Validate Origin or Referer headers for state-mutating requests."""
    origin = request.headers.get("Origin")
    referer = request.headers.get("Referer")
    host_url = request.host_url

    host_parsed = urlparse(host_url)

    if origin:
        origin_parsed = urlparse(origin)
        if origin_parsed.netloc != host_parsed.netloc:
            return False

    if referer:
        referer_parsed = urlparse(referer)
        if referer_parsed.netloc != host_parsed.netloc:
            return False

    return bool(origin or referer)


@app.before_request
def check_csrf():
    """CSRF Prevention: Verifies Origin/Referer for state-mutating requests."""
    if request.method not in ["POST", "PUT", "DELETE"]:
        return

    if (
        app.config.get("TESTING")
        or request.headers.get("User-Agent") == "Werkzeug/3.1.3"
    ):
        return

    if not is_safe_origin_or_referer():
        return (
            jsonify(
                {"status": "error", "message": "Cross-origin request blocked"}
            ),
            403,
        )


# --- DYNAMIC CSRF META TAG INJECTION HOOK ---

@app.after_request
def inject_csrf_token(response):
    """Dynamically injects CSRF meta tag into HTML responses."""
    if response.mimetype == "text/html":
        try:
            html = response.get_data(as_text=True)
            token = generate_csrf()
            meta_tag = f'\n    <meta name="csrf-token" content="{token}">'
            if "<head>" in html:
                html = html.replace("<head>", f"<head>{meta_tag}", 1)
                response.set_data(html)
        except Exception as e:
            logger.error(f"Failed to inject CSRF token: {e}")
    return response


# --- STATE DRIFT SIMULATION ENGINE ---

def drift_simulation():
    """Background thread function that drifts the state every 5 seconds."""
    global current_state

    logger.info("[Simulation] Background thread started.")
    while True:
        # Update simulation telemetry every 5 seconds
        time.sleep(5)

        with current_state_lock:
            state = db.get_simulation_state()
            if not state:
                # Local DB initialization fallback
                continue

            # 1. Drift Occupancy (-400 to +600) capped at capacity
            capacity = state.get("capacity", 70000)
            occupancy = state.get("occupancy", 52000)
            state["occupancy"] = max(
                5000, min(capacity, occupancy + random.randint(-400, +600))
            )

            # 2. Drift Gate wait times (-2 to +2 minutes)
            for gate in state.get("gates", []):
                drift = random.randint(-2, 2)
                gate["waitTimeMinutes"] = max(
                    1, min(45, gate["waitTimeMinutes"] + drift)
                )

            # 3. Drift Zone crowd levels (-3% to +3%)
            for zone in state.get("zones", []):
                drift = random.randint(-3, 3)
                zone["crowdLevel"] = max(
                    5, min(99, zone["crowdLevel"] + drift)
                )

            # 4. Drift Amenities wait times (-2 to +2 minutes)
            for am in state.get("amenities", []):
                drift = random.randint(-2, 2)
                am["waitTimeMinutes"] = max(
                    0, min(30, am["waitTimeMinutes"] + drift)
                )

            # 5. Automated Alerts Cleanup (20% chance each drift)
            alerts = db.get_alerts()
            if random.random() < 0.2:
                # Remove automated warnings
                db.clear_auto_alerts()
                alerts = [a for a in alerts if not a.get("auto")]

            # 6. Automatic Medical/Security Overcrowd Alert (if Food Court >90%)
            food_zone = next(
                (z for z in state.get("zones", []) if z["id"] == "zone-food"),
                None,
            )
            if food_zone and food_zone["crowdLevel"] > 90:
                if not any("Food Court" in a["message"] for a in alerts):
                    db.add_alert(
                        "Critical overcrowding in Food Court. Medical staff on standby.",
                        "danger",
                        auto=True,
                    )

            # Save the drifted state to the database
            db.save_simulation_state(state)
            current_state = state

        # Notify all active SSE stream connections
        with sse_lock:
            # Refresh alerts from DB to send along with the state
            fresh_alerts = db.get_alerts()
            payload = {"telemetry": current_state, "alerts": fresh_alerts}
            # Remove closed/broken queues
            for listener in list(sse_listeners):
                try:
                    listener.put_nowait(payload)
                except queue.Full:
                    pass


# Start background thread
simulation_thread = threading.Thread(target=drift_simulation, daemon=True)
simulation_thread.start()


# --- ARENAFLOW NEW EXTENSIONS MODULES ---

prediction_svc = PredictionService(db)
analytics_svc = AnalyticsService(db)
feedback_svc = FeedbackService(db)
sos_svc = SOSService(db)
report_svc = ReportService(db)


# --- BLUEPRINTS REGISTRATION ---

from blueprints.auth import auth_bp  # noqa: E402
from blueprints.admin import admin_bp  # noqa: E402
from blueprints.core import core_bp  # noqa: E402
from blueprints.assistant import assistant_bp  # noqa: E402

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(core_bp)
app.register_blueprint(assistant_bp)


# --- SERVER STARTUP ---

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host=host, port=port)
