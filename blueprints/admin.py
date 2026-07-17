import queue
import time
from flask import Blueprint, jsonify, render_template, request, session, Response

from app import (
    db,
    require_admin,
    require_auth,
    current_state,
    current_state_lock,
    sse_lock,
    sse_listeners,
    report_svc,
    sos_svc,
    sanitize_html
)

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@require_admin
def admin_dashboard():
    """Renders the Command Center dashboard."""
    return render_template("admin.html", username=session.get("username"))


@admin_bp.route("/api/admin/broadcast", methods=["POST"])
@require_admin
def admin_broadcast():
    data = request.json or {}
    message = sanitize_html(data.get("message", "").strip())
    alert_type = data.get("type", "info")

    if not message:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Broadcast message cannot be empty",
                }
            ),
            400,
        )

    if alert_type not in ["info", "warning", "danger", "success"]:
        alert_type = "info"

    alert = db.add_alert(message, alert_type, auto=False)

    # Broadcast to SSE streams immediately
    with sse_lock:
        fresh_alerts = db.get_alerts()
        payload = {"telemetry": current_state, "alerts": fresh_alerts}
        for listener in list(sse_listeners):
            try:
                listener.put_nowait(payload)
            except queue.Full:
                pass

    return jsonify({"status": "success", "alert": alert})


@admin_bp.route("/api/admin/dispatch", methods=["POST"])
@require_admin
def admin_dispatch():
    data = request.json or {}
    staff_type = data.get("type", "security")  # security or medical
    zone_id = data.get("zone_id")

    if staff_type not in ["security", "medical"] or not zone_id:
        return (
            jsonify(
                {"status": "error", "message": "Invalid dispatch details"}
            ),
            400,
        )

    with current_state_lock:
        state = db.get_simulation_state()
        if state["staff"][staff_type]["available"] > 0:
            state["staff"][staff_type]["available"] -= 1
            state["staff"][staff_type]["deployed"].append(
                {"zone_id": zone_id, "timestamp": time.time()}
            )
            db.save_simulation_state(state)
            db.log_dispatch(staff_type, zone_id)

            # Immediately notify listeners of staff change
            with sse_lock:
                payload = {"telemetry": state, "alerts": db.get_alerts()}
                for listener in list(sse_listeners):
                    try:
                        listener.put_nowait(payload)
                    except queue.Full:
                        pass

            return jsonify(
                {
                    "status": "success",
                    "message": f"{staff_type.capitalize()} unit dispatched successfully.",
                }
            )

    return (
        jsonify(
            {"status": "error", "message": f"No available {staff_type} units."}
        ),
        400,
    )


# --- REPORT GENERATOR ---

@admin_bp.route("/incident-report")
@require_admin
def incident_report_page():
    return render_template(
        "incident_report.html", username=session.get("username")
    )


@admin_bp.route("/api/reports/incident")
@require_admin
def get_incident_report():
    report_text = report_svc.generate_incident_report_text()
    return jsonify({"status": "success", "report": report_text})


@admin_bp.route("/api/reports/incident/pdf")
@require_admin
def get_incident_report_pdf():
    report_text = report_svc.generate_incident_report_text()
    pdf_bytes = report_svc.export_report_to_pdf(
        report_text, "Operations_Incident_Report"
    )
    if not pdf_bytes:
        return "FPDF is not installed or PDF generation failed.", 500

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": "attachment;filename=operations_incident_report.pdf"
        },
    )


@admin_bp.route("/api/reports/match-summary/pdf")
@require_admin
def get_match_summary_pdf():
    state = db.get_simulation_state()
    summary_text = (
        f"### ARENAFLOW MATCH SUMMARY REPORT\n\n"
        f"**Match Day Metrics**:\n"
        f"- Final Recorded Attendance: {state.get('occupancy', 0)} / {state.get('capacity', 70000)}\n"
        f"- Active Alerts Count: {len(db.get_alerts())}\n"
        f"- Staff Dispatches Logged: {len(db.get_dispatches())}\n\n"
        f"**Security Dispatches**: {len([d for d in db.get_dispatches() if d.get('staff_type') == 'security'])}\n"
        f"**Medical Dispatches**: {len([d for d in db.get_dispatches() if d.get('staff_type') == 'medical'])}\n\n"
        f"**AI Copilot Operational Recommendations**:\n"
        f"- Shift ticketing flows to West Gate during entry rushes.\n"
        f"- Keep two standby medical units on South Concourse to manage food congestion."
    )
    pdf_bytes = report_svc.export_report_to_pdf(
        summary_text, "Operations_Match_Summary"
    )
    if not pdf_bytes:
        return "PDF generation failed.", 500
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": "attachment;filename=match_summary.pdf"
        },
    )


# --- AI OPERATIONS COPILOT ---

@admin_bp.route("/api/copilot/chat", methods=["POST"])
@require_admin
def copilot_chat():
    data = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return (
            jsonify({"status": "error", "message": "Message is required"}),
            400,
        )
    reply = report_svc.run_operations_copilot(message)
    return jsonify({"status": "success", "message": reply})


# --- ANALYTICS ---

@admin_bp.route("/analytics")
@require_admin
def analytics_page():
    return render_template("analytics.html", username=session.get("username"))


# --- SOS UPDATE & LIST ---

@admin_bp.route("/api/sos/list")
@require_admin
def get_sos_list():
    alerts = sos_svc.get_sos_alerts()
    return jsonify({"status": "success", "alerts": alerts})


@admin_bp.route("/api/sos/update", methods=["POST"])
@require_admin
def update_sos():
    data = request.json or {}
    sos_id = data.get("id")
    status = data.get("status")

    if not sos_id or status not in ["Accepted", "Resolved", "Pending"]:
        return (
            jsonify(
                {"status": "error", "message": "Invalid input parameters"}
            ),
            400,
        )

    success = sos_svc.update_sos_status(sos_id, status)
    if success:
        return jsonify({"status": "success", "message": "SOS status updated."})
    return (
        jsonify(
            {"status": "error", "message": "Failed to update SOS status."}
        ),
        400,
    )


# --- LOST & FOUND UPDATE & FEEDBACK SUMMARY ---

@admin_bp.route("/api/lost-found/update", methods=["POST"])
@require_admin
def update_lost_found():
    data = request.json or {}
    item_id = data.get("id")
    status = data.get("status", "Claimed")

    if not item_id or status not in ["Claimed", "Found", "Lost"]:
        return (
            jsonify(
                {"status": "error", "message": "Invalid input parameters"}
            ),
            400,
        )

    if db.use_firebase:
        try:
            ref = db.db.collection("lost_found").document(item_id)
            if ref.get().exists:
                ref.update({"status": status})
                return jsonify({"status": "success"})
        except Exception as e:
            db.logger.error(f"[LostFound] Firebase update error: {e}")
    else:
        with db.lock:
            local_data = db._read_local_db()
            found = False
            for item in local_data.get("lost_found", []):
                if item["id"] == item_id:
                    item["status"] = status
                    found = True
                    break
            if found:
                db._write_local_db(local_data)
                return jsonify({"status": "success"})
    return (
        jsonify({"status": "error", "message": "Failed to update item"}),
        400,
    )


@admin_bp.route("/api/feedback/summary")
@require_auth
def get_feedback_summary():
    """Returns feedback metrics summary."""
    # Importing from app directly to avoid circular dependency
    from app import feedback_svc
    summary = feedback_svc.generate_feedback_summary()
    return jsonify({"status": "success", "summary": summary})
