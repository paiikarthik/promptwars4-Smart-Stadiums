import os
import time
import json
import random
import queue
import threading
from functools import wraps
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, Response
from werkzeug.security import generate_password_hash, check_password_hash

# Import our database wrapper
from firebase_helper import StadiumDB

# Import Google GenAI SDK
try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

app = Flask(__name__)
# Secure key for sessions
app.secret_key = os.environ.get("SECRET_KEY", "stadiumiq-secure-session-key-2026")

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
        print("[AI] Google GenAI client initialized successfully.")
    except Exception as e:
        print(f"[AI] GenAI initialization failed: {e}")

# --- ROLE-BASED ACCESS CONTROL DECORATORS ---

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"status": "error", "message": "Unauthorized"}), 401
            return redirect(url_for("portal"))
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"status": "error", "message": "Unauthorized"}), 401
            return redirect(url_for("portal"))
        if session.get("role") != "admin":
            if request.path.startswith("/api/"):
                return jsonify({"status": "error", "message": "Forbidden. Admin access required."}), 403
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function

# --- STATE DRIFT SIMULATION ENGINE ---

def drift_simulation():
    """Background thread function that drifts the state every 5 seconds."""
    global current_state
    
    print("[Simulation] Background thread started.")
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
            state["occupancy"] = max(5000, min(capacity, occupancy + random.randint(-400, +600)))
            
            # 2. Drift Gate wait times (-2 to +2 minutes)
            for gate in state.get("gates", []):
                drift = random.randint(-2, 2)
                gate["waitTimeMinutes"] = max(1, min(45, gate["waitTimeMinutes"] + drift))
                
            # 3. Drift Zone crowd levels (-3% to +3%)
            for zone in state.get("zones", []):
                drift = random.randint(-3, 3)
                zone["crowdLevel"] = max(5, min(99, zone["crowdLevel"] + drift))
                
            # 4. Drift Amenities wait times (-2 to +2 minutes)
            for am in state.get("amenities", []):
                drift = random.randint(-2, 2)
                am["waitTimeMinutes"] = max(0, min(30, am["waitTimeMinutes"] + drift))
                
            # 5. Automated Alerts Cleanup (20% chance each drift)
            alerts = db.get_alerts()
            if random.random() < 0.2:
                # Remove automated warnings
                db.clear_auto_alerts()
                alerts = [a for a in alerts if not a.get("auto")]
                
            # 6. Automatic Medical/Security Overcrowd Alert (if Food Court >90%)
            food_zone = next((z for z in state.get("zones", []) if z["id"] == "zone-food"), None)
            if food_zone and food_zone["crowdLevel"] > 90:
                if not any("Food Court" in a["message"] for a in alerts):
                    new_alert = db.add_alert(
                        "Critical overcrowding in Food Court. Medical staff on standby.",
                        "danger",
                        auto=True
                    )
                    
            # Save the drifted state to the database
            db.save_simulation_state(state)
            current_state = state
            
        # Notify all active SSE stream connections
        with sse_lock:
            # Refresh alerts from DB to send along with the state
            fresh_alerts = db.get_alerts()
            payload = {
                "telemetry": current_state,
                "alerts": fresh_alerts
            }
            # Remove closed/broken queues
            for listener in list(sse_listeners):
                try:
                    listener.put_nowait(payload)
                except queue.Full:
                    # Queue is full, consumer likely disconnected
                    pass

# Start background thread
simulation_thread = threading.Thread(target=drift_simulation, daemon=True)
simulation_thread.start()

# --- WEB PAGE ROUTES ---

@app.route("/")
def portal():
    """Renders the login/registration gateway."""
    if "username" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))
    return render_template("portal.html")

@app.route("/dashboard")
@require_auth
def dashboard():
    """Renders the attendee fan dashboard."""
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    return render_template("index.html", username=session.get("username"))

@app.route("/admin")
@require_admin
def admin_dashboard():
    """Renders the Command Center dashboard."""
    return render_template("admin.html", username=session.get("username"))

# --- AUTHENTICATION API ENDPOINTS ---

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "attendee")
    
    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password are required"}), 400
        
    if role not in ["attendee", "admin"]:
        role = "attendee"
        
    password_hash = generate_password_hash(password)
    success = db.register_user(username, password_hash, role)
    if success:
        return jsonify({"status": "success", "message": "User registered successfully"})
    return jsonify({"status": "error", "message": "Username already exists"}), 400

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password are required"}), 400
        
    user = db.get_user(username)
    if user and check_password_hash(user["password_hash"], password):
        session["username"] = user["username"]
        session["role"] = user["role"]
        return jsonify({
            "status": "success", 
            "username": user["username"], 
            "role": user["role"],
            "redirect": url_for("admin_dashboard") if user["role"] == "admin" else url_for("dashboard")
        })
    return jsonify({"status": "error", "message": "Invalid username or password"}), 401

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "success", "message": "Logged out successfully", "redirect": url_for("portal")})

# --- TELEMETRY API ENDPOINTS ---

@app.route("/api/telemetry", methods=["GET"])
@require_auth
def get_telemetry():
    """Gets current telemetry state and alerts."""
    state = db.get_simulation_state()
    alerts = db.get_alerts()
    return jsonify({
        "status": "success",
        "telemetry": state,
        "alerts": alerts
    })

# --- ADMIN API ENDPOINTS ---

@app.route("/api/admin/broadcast", methods=["POST"])
@require_admin
def admin_broadcast():
    data = request.json or {}
    message = data.get("message", "").strip()
    alert_type = data.get("type", "info")
    
    if not message:
        return jsonify({"status": "error", "message": "Broadcast message cannot be empty"}), 400
        
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

@app.route("/api/admin/dispatch", methods=["POST"])
@require_admin
def admin_dispatch():
    data = request.json or {}
    staff_type = data.get("type", "security") # security or medical
    zone_id = data.get("zone_id")
    
    if staff_type not in ["security", "medical"] or not zone_id:
        return jsonify({"status": "error", "message": "Invalid dispatch details"}), 400
        
    with current_state_lock:
        state = db.get_simulation_state()
        if state["staff"][staff_type]["available"] > 0:
            state["staff"][staff_type]["available"] -= 1
            state["staff"][staff_type]["deployed"].append({
                "zone_id": zone_id,
                "timestamp": time.time()
            })
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
                        
            return jsonify({"status": "success", "message": f"{staff_type.capitalize()} unit dispatched successfully."})
            
    return jsonify({"status": "error", "message": f"No available {staff_type} units."}), 400

# --- SERVER-SENT EVENTS (SSE) STREAMING ---

@app.route("/api/stream")
@require_auth
def event_stream():
    """Streams live simulation state and alerts to clients in real-time."""
    def event_generator():
        q = queue.Queue(maxsize=10)
        with sse_lock:
            sse_listeners.append(q)
            
        # Push initial data immediately
        initial_alerts = db.get_alerts()
        with current_state_lock:
            initial_payload = {"telemetry": current_state, "alerts": initial_alerts}
        yield f"data: {json.dumps(initial_payload)}\n\n"
        
        try:
            while True:
                # Wait for next simulation/alert update
                data = q.get()
                yield f"data: {json.dumps(data)}\n\n"
        except GeneratorExit:
            # Client disconnected
            with sse_lock:
                if q in sse_listeners:
                    sse_listeners.remove(q)
                    
    return Response(event_generator(), mimetype="text/event-stream")

# --- AI CONCIERGE CHATBOT ENDPOINT ---

def local_concierge_fallback(query, telemetry):
    """Fallback logic for Stadium Concierge if Gemini API key is missing."""
    query = query.lower()
    
    # Simple PII warning check
    if "ssn" in query or "password" in query or "aadhaar" in query or "credit card" in query:
        return "⚠️ **Security Warning**: Please do not share any sensitive personal information such as passwords, SSNs, Aadhaar, or credit card details. I do not need this data to assist you."

    # Extract current metrics
    gates = telemetry.get("gates", [])
    zones = telemetry.get("zones", [])
    amenities = telemetry.get("amenities", [])
    
    # 1. Gate questions
    if "gate" in query or "entrance" in query or "enter" in query:
        if gates:
            sorted_gates = sorted(gates, key=lambda x: x["waitTimeMinutes"])
            fastest = sorted_gates[0]
            others_str = ", ".join([f"**{g['name']}** ({g['waitTimeMinutes']} mins)" for g in sorted_gates[1:]])
            return (
                f"🏟️ **Fastest Entry Point**: I recommend using **{fastest['name']}** which has a wait time of only **{fastest['waitTimeMinutes']} minutes**.\n\n"
                f"Other entrances: {others_str}.\n\n"
                f"Do you need directions to this gate?"
            )
        return "I can't access gate wait times right now. Generally, the North and West Gates have shorter lines."

    # 2. Food / Drink questions
    if "food" in query or "drink" in query or "pizza" in query or "beer" in query or "eat" in query or "restaurant" in query:
        food_items = [am for am in amenities if am["type"] == "food"]
        if food_items:
            sorted_food = sorted(food_items, key=lambda x: x["waitTimeMinutes"])
            best = sorted_food[0]
            others_str = ", ".join([f"**{f['name']}** ({f['waitTimeMinutes']} mins)" for f in sorted_food[1:]])
            return (
                f"🍕 **Food & Drink Recommendation**: The **{best['name']}** currently has the shortest line, with a wait time of **{best['waitTimeMinutes']} minutes**.\n\n"
                f"Other stands: {others_str}.\n\n"
                f"Would you like me to find the nearest restroom on your way there?"
            )
        return "The Food Court is currently busy. Pizza Stand and Drinks Tent are available on the East and South Concourses."

    # 3. Washroom / Restroom questions
    if "restroom" in query or "washroom" in query or "toilet" in query or "loo" in query:
        restrooms = [am for am in amenities if am["type"] == "restroom"]
        if restrooms:
            sorted_restrooms = sorted(restrooms, key=lambda x: x["waitTimeMinutes"])
            best = sorted_restrooms[0]
            return (
                f"🚻 **Nearest Restroom**: The **{best['name']}** is your best option with a wait time of only **{best['waitTimeMinutes']} minutes**.\n\n"
                f"The other option (**{sorted_restrooms[1]['name']}**) currently has a **{sorted_restrooms[1]['waitTimeMinutes']} minute** wait.\n\n"
                f"Do you need to know if it has accessible stalls?"
            )
        return "Washrooms are located near the North Concourse and the Main Entrance. The Main washroom usually moves fastest."

    # 4. Crowd / Concourse density questions
    if "crowd" in query or "concourse" in query or "busy" in query or "congested" in query:
        congested = [z for z in zones if z["crowdLevel"] > 75]
        clear = [z for z in zones if z["crowdLevel"] < 45]
        
        reply = "📊 **Stadium Density Report**:\n"
        if congested:
            reply += f"- **High Congestion Zones (Avoid)**: " + ", ".join([f"**{z['name']}** ({z['crowdLevel']}% full)" for z in congested]) + "\n"
        if clear:
            reply += f"- **Clear Zones**: " + ", ".join([f"**{z['name']}** ({z['crowdLevel']}% full)" for z in clear]) + "\n"
            
        reply += "\nI suggest routing your movement through Clear Zones to avoid bottlenecks. Can I help plan an alternative route?"
        return reply

    return (
        f"Hi there! I am your **AI Stadium Concierge** 🤖.\n\n"
        f"I can help you navigate the stadium in real-time based on live crowds and telemetry. Try asking:\n"
        f"- *Which gate is fastest to enter?*\n"
        f"- *Where can I grab food with the shortest queue?*\n"
        f"- *What washroom should I use right now?*\n"
        f"- *Which areas of the stadium are overcrowded?*"
    )

@app.route("/api/assistant/chat", methods=["POST"])
@require_auth
def assistant_chat():
    data = request.json or {}
    user_query = data.get("message", "").strip()
    
    if not user_query:
        return jsonify({"status": "error", "message": "Message cannot be empty"}), 400
        
    # Get current state to ground the prompt
    with current_state_lock:
        state = db.get_simulation_state()
        
    # Build a rich grounding context with current telemetry
    telemetry_summary = f"""
    Current Stadium Telemetry context:
    - Overall Occupancy: {state.get('occupancy')} / {state.get('capacity')}
    - Gates Status:
      * {state.get('gates')[0]['name']}: {state.get('gates')[0]['waitTimeMinutes']} min wait
      * {state.get('gates')[1]['name']}: {state.get('gates')[1]['waitTimeMinutes']} min wait
      * {state.get('gates')[2]['name']}: {state.get('gates')[2]['waitTimeMinutes']} min wait
      * {state.get('gates')[3]['name']}: {state.get('gates')[3]['waitTimeMinutes']} min wait
    - Concourse Zones Density:
      * {state.get('zones')[0]['name']}: {state.get('zones')[0]['crowdLevel']}% full
      * {state.get('zones')[1]['name']}: {state.get('zones')[1]['crowdLevel']}% full
      * {state.get('zones')[2]['name']}: {state.get('zones')[2]['crowdLevel']}% full
      * {state.get('zones')[3]['name']}: {state.get('zones')[3]['crowdLevel']}% full
      * {state.get('zones')[4]['name']}: {state.get('zones')[4]['crowdLevel']}% full
      * {state.get('zones')[5]['name']}: {state.get('zones')[5]['crowdLevel']}% full
    - Amenities wait times:
      * {state.get('amenities')[0]['name']} (restroom): {state.get('amenities')[0]['waitTimeMinutes']} mins
      * {state.get('amenities')[1]['name']} (restroom): {state.get('amenities')[1]['waitTimeMinutes']} mins
      * {state.get('amenities')[2]['name']} (food): {state.get('amenities')[2]['waitTimeMinutes']} mins
      * {state.get('amenities')[3]['name']} (food): {state.get('amenities')[3]['waitTimeMinutes']} mins
    """

    system_context = f"""
    You are StadiumIQ's Grounded AI Stadium Concierge 🤖, helping attendees navigate the physical venue.
    Use the current live telemetry data provided below to answer queries.
    
    {telemetry_summary}
    
    CRITICAL RULES:
    1. NEVER ask for or store sensitive personal information (Aadhaar, SSN, passwords, credit cards). If the user mentions them, warn them clearly.
    2. Provide step-by-step navigation instructions using actual data points (e.g. recommend the gate/washroom/food stall with the MINIMUM wait time).
    3. Keep explanations clear, structured, and easy to read using Markdown (bolding, lists).
    4. Conclude your recommendations with a helpful follow-up question (e.g., "Do you want directions?" or "Should I check food queues near your seat?").
    5. Keep responses concise and focused on crowd/stadium logistics.
    
    User Query: {user_query}
    """
    
    response_text = ""
    is_ai = False
    
    if gemini_client:
        try:
            response = gemini_client.models.generate_content(
                model='gemini-1.5-flash',
                contents=system_context
            )
            response_text = response.text
            is_ai = True
        except Exception as e:
            print(f"[AI] Gemini model generation failed: {e}. Falling back to rule-based.")
            
    if not is_ai:
        # Fallback to local rule-based engine
        response_text = local_concierge_fallback(user_query, state)
        if os.environ.get("GEMINI_API_KEY"):
            response_text += "\n\n*(Using local rule-based assistant fallback due to Gemini error)*"
        else:
            response_text += "\n\n*(Using local rule-based assistant - set GEMINI_API_KEY environment variable for full AI capabilities)*"
            
    return jsonify({
        "status": "success",
        "message": response_text,
        "model": "Gemini-1.5-Flash" if is_ai else "Rule-based Engine",
        "timestamp": time.time()
    })

# --- SERVER STARTUP ---

if __name__ == "__main__":
    # Run server on port 8080.
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host="0.0.0.0", port=port)
