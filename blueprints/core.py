import json
import queue
import time
import google.api_core.exceptions
from typing import Union, Tuple, Dict, Any
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

from app import (
    db,
    require_auth,
    current_state,
    current_state_lock,
    sse_lock,
    sse_listeners,
    prediction_svc,
    feedback_svc,
    sos_svc,
    sanitize_html,
    logger,
)

core_bp = Blueprint("core", __name__)


@core_bp.route("/dashboard")
@require_auth
def dashboard() -> Union[str, Response]:
    """Renders the attendee fan dashboard or redirects admins to the command center."""
    if session.get("role") == "admin":
        return redirect(url_for("admin.admin_dashboard"))
    return render_template("index.html", username=session.get("username"))


@core_bp.route("/api/telemetry", methods=["GET"])
@require_auth
def get_telemetry() -> Response:
    """Gets the current real-time stadium metrics and warning alerts."""
    state: Dict[str, Any] = db.get_simulation_state()
    alerts = db.get_alerts()
    return jsonify({"status": "success", "telemetry": state, "alerts": alerts})


@core_bp.route("/api/stream")
@require_auth
def event_stream() -> Response:
    """Streams live stadium simulation telemetry to active frontend listeners via SSE."""

    def event_generator():
        q = queue.Queue(maxsize=10)
        with sse_lock:
            sse_listeners.append(q)

        # Push initial data immediately
        initial_alerts = db.get_alerts()
        with current_state_lock:
            initial_payload = {
                "telemetry": current_state,
                "alerts": initial_alerts,
            }
        yield f"data: {json.dumps(initial_payload)}\n\n"

        try:
            while True:
                # Wait for state changes in simulation drift or dispatch triggers
                data = q.get()
                yield f"data: {json.dumps(data)}\n\n"
        except GeneratorExit:
            with sse_lock:
                if q in sse_listeners:
                    sse_listeners.remove(q)

    return Response(event_generator(), mimetype="text/event-stream")


@core_bp.route("/api/predictions")
@require_auth
def get_predictions() -> Response:
    """Returns predictive wait-times and gate crowds using historical drift telemetry."""
    predictions = prediction_svc.get_predictions()
    return jsonify({"status": "success", "predictions": predictions})


@core_bp.route("/feedback")
@require_auth
def feedback_page() -> str:
    """Renders the attendee feedback form page."""
    return render_template("feedback.html", username=session.get("username"))


@core_bp.route("/api/feedback/submit", methods=["POST"])
@require_auth
def submit_feedback() -> Union[Response, Tuple[Response, int]]:
    """Handles fan feedback submissions.

    Validates that scores exist, are integer values between 1 and 5, and the comments are within bounds.
    """
    data = request.json or {}
    scores = data.get("scores", {})
    comments: str = sanitize_html(data.get("comments", "") or "").strip()

    if not isinstance(scores, dict):
        return (
            jsonify(
                {"status": "error", "message": "Scores must be a JSON object"}
            ),
            400,
        )

    valid_categories = [
        "navigation",
        "food",
        "restrooms",
        "security",
        "ai_assistant",
    ]
    for category, val in scores.items():
        if category not in valid_categories:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Invalid score category: {category}",
                    }
                ),
                400,
            )
        try:
            val_int = int(val)
            if not (1 <= val_int <= 5):
                raise ValueError()
            scores[category] = val_int
        except (ValueError, TypeError):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Score for {category} must be an integer between 1 and 5",
                    }
                ),
                400,
            )

    if len(comments) > 1000:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Comments cannot exceed 1000 characters",
                }
            ),
            400,
        )

    feedback = feedback_svc.submit_feedback(scores, comments)
    return jsonify({"status": "success", "feedback": feedback})


@core_bp.route("/api/sos/send", methods=["POST"])
@require_auth
def send_sos() -> Union[Response, Tuple[Response, int]]:
    """Receives and logs a fan SOS panic alert."""
    data = request.json or {}
    seat: str = sanitize_html(data.get("seat", "") or "").strip()
    zone_id: str = sanitize_html(data.get("zone_id", "") or "").strip()

    if not seat or not zone_id:
        return (
            jsonify(
                {"status": "error", "message": "Seat and Zone ID are required"}
            ),
            400,
        )

    if len(seat) > 50 or len(zone_id) > 50:
        return (
            jsonify(
                {"status": "error", "message": "Seat or Zone ID too long"}
            ),
            400,
        )

    sos = sos_svc.send_sos(seat, zone_id)

    # Broadcast to SSE listeners immediately
    with sse_lock:
        fresh_alerts = db.get_alerts()
        payload = {"telemetry": current_state, "alerts": fresh_alerts}
        for listener in list(sse_listeners):
            try:
                listener.put_nowait(payload)
            except queue.Full:
                pass

    return jsonify({"status": "success", "sos": sos})


@core_bp.route("/lost-found")
@require_auth
def lost_found_page() -> str:
    """Renders the Lost & Found visual search page."""
    return render_template("lost_found.html", username=session.get("username"))


def _save_lost_found_item(item: Dict[str, Any]) -> None:
    """Helper to save a lost and found item to Firebase or local DB.

    Args:
        item (Dict[str, Any]): The item dictionary to save.
    """
    if db.use_firebase:
        try:
            db.db.collection("lost_found").document(item["id"]).set(item)
        except google.api_core.exceptions.GoogleAPIError as e:
            logger.error(f"[LostFound] Firebase error: {e}")
    else:
        with db.lock:
            local_data = db._read_local_db()
            if "lost_found" not in local_data:
                local_data["lost_found"] = []
            local_data["lost_found"].append(item)
            db._write_local_db(local_data)


@core_bp.route("/api/lost-found/submit", methods=["POST"])
@require_auth
def submit_lost_found() -> Union[Response, Tuple[Response, int]]:
    """Registers a newly reported lost/found item.

    Validates field constraints to prevent buffer overflow.
    """
    data = request.json or {}
    item_type: str = sanitize_html(data.get("item_type", "") or "").strip()
    description: str = sanitize_html(data.get("description", "") or "").strip()
    location: str = sanitize_html(data.get("location", "") or "").strip()
    contact: str = sanitize_html(data.get("contact", "") or "").strip()

    if not item_type or not description or not location or not contact:
        return (
            jsonify({"status": "error", "message": "All fields are required"}),
            400,
        )

    if (
        len(item_type) > 100
        or len(description) > 500
        or len(location) > 200
        or len(contact) > 100
    ):
        return (
            jsonify(
                {"status": "error", "message": "Input length bounds exceeded"}
            ),
            400,
        )

    item = {
        "id": f"lf-{time.time()}",
        "item_type": item_type,
        "description": description,
        "location": location,
        "contact": contact,
        "status": "Found",
        "timestamp": time.time(),
    }

    _save_lost_found_item(item)
    return jsonify({"status": "success", "item": item})


@core_bp.route("/api/lost-found/search")
@require_auth
def search_lost_found() -> Union[Response, Tuple[Response, int]]:
    """Searches the Lost & Found database matching item descriptions."""
    query: str = request.args.get("q", "").strip().lower()

    if len(query) > 100:
        return (
            jsonify({"status": "error", "message": "Search query too long"}),
            400,
        )

    items = []
    if db.use_firebase:
        try:
            docs = db.db.collection("lost_found").stream()
            items = [doc.to_dict() for doc in docs]
        except google.api_core.exceptions.GoogleAPIError as e:
            logger.error(f"[LostFound] Firebase read error: {e}")
    else:
        with db.lock:
            local_data = db._read_local_db()
            items = local_data.get("lost_found", [])

    if query:
        items = [
            i
            for i in items
            if query in i["item_type"].lower()
            or query in i["description"].lower()
            or query in i["location"].lower()
        ]

    items = sorted(items, key=lambda x: x["timestamp"], reverse=True)
    return jsonify({"status": "success", "items": items})


@core_bp.route("/parking")
@require_auth
def parking_page() -> str:
    """Renders the parking availability hub page."""
    return render_template("parking.html", username=session.get("username"))


@core_bp.route("/api/parking")
@require_auth
def get_parking() -> Response:
    """Returns real-time occupancy updates for all stadium parking gates."""
    seed = int(time.time()) % 10
    parking_data = [
        {
            "id": "park-a",
            "name": "Parking A (North Gate)",
            "total_slots": 500,
            "occupied": 420 + seed,
            "walking_time_mins": 3,
        },
        {
            "id": "park-b",
            "name": "Parking B (South Gate)",
            "total_slots": 800,
            "occupied": 680 - seed,
            "walking_time_mins": 5,
        },
        {
            "id": "park-c",
            "name": "Parking C (VIP / East)",
            "total_slots": 300,
            "occupied": 290 + (seed % 3),
            "walking_time_mins": 8,
        },
    ]
    return jsonify({"status": "success", "parking": parking_data})


@core_bp.route("/notifications")
@require_auth
def notifications_page() -> str:
    """Renders the fan safety alerts and dispatches log page."""
    return render_template(
        "notifications.html", username=session.get("username")
    )


@core_bp.route("/api/notifications/history")
@require_auth
def get_notifications_history() -> Response:
    """Returns log logs of all dispatches and alerts."""
    history = []

    dispatches = db.get_dispatches()
    for d in dispatches:
        history.append(
            {
                "message": f"Dispatched {d['staff_type'].capitalize()} unit to Zone {d['zone_id']}",
                "type": d["staff_type"],
                "timestamp": d["timestamp"],
            }
        )

    alerts = db.get_alerts()
    for a in alerts:
        history.append(
            {
                "message": a["message"],
                "type": a["type"],
                "timestamp": a["timestamp"],
            }
        )

    history = sorted(history, key=lambda x: x["timestamp"], reverse=True)
    return jsonify({"status": "success", "history": history})


@core_bp.route("/api/weather")
@require_auth
def get_weather() -> Response:
    """Returns current weather condition advisories."""
    weather_data = {
        "temperature": 26,
        "rain_chance": 10,
        "wind_speed_kph": 12,
        "advisory": "Weather is clear & warm. Grab a bottle of water and enjoy the match!",
    }
    seed = (int(time.time()) % 4) - 2
    weather_data["temperature"] += seed
    return jsonify({"status": "success", "weather": weather_data})


@core_bp.route("/api/analytics/data")
@require_auth
def get_analytics_data_core() -> Response:
    """Retrieves operational statistics metrics."""
    from app import analytics_svc

    data = analytics_svc.get_analytics()
    return jsonify({"status": "success", "metrics": data})
