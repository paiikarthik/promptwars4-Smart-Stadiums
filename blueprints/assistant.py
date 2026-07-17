import time
import os
from typing import Dict, Any, Union, Tuple
from flask import Blueprint, jsonify, request, Response

from app import (
    require_auth,
    current_state_lock,
    db,
    gemini_client,
    logger
)

assistant_bp = Blueprint("assistant", __name__)


def local_concierge_fallback(query: str, telemetry: Dict[str, Any]) -> str:
    """Fallback logic for Stadium Concierge if Gemini API key is missing.

    Evaluates keyword matches on gate status, food stalls, restrooms, and density.
    """
    query = query.lower()

    # Simple PII warning check
    if (
        "ssn" in query
        or "password" in query
        or "aadhaar" in query
        or "credit card" in query
    ):
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
            others_str = ", ".join(
                [
                    f"**{g['name']}** ({g['waitTimeMinutes']} mins)"
                    for g in sorted_gates[1:]
                ]
            )
            return (
                f"🏟️ **Fastest Entry Point**: I recommend using **{fastest['name']}** which has a wait time of only **{fastest['waitTimeMinutes']} minutes**.\n\n"
                f"Other entrances: {others_str}.\n\n"
                f"Do you need directions to this gate?"
            )
        return "I can't access gate wait times right now. Generally, the North and West Gates have shorter lines."

    # 2. Food / Drink questions
    if (
        "food" in query
        or "drink" in query
        or "pizza" in query
        or "beer" in query
        or "eat" in query
        or "restaurant" in query
    ):
        food_items = [am for am in amenities if am["type"] == "food"]
        if food_items:
            sorted_food = sorted(
                food_items, key=lambda x: x["waitTimeMinutes"]
            )
            best = sorted_food[0]
            others_str = ", ".join(
                [
                    f"**{f['name']}** ({f['waitTimeMinutes']} mins)"
                    for f in sorted_food[1:]
                ]
            )
            return (
                f"🍕 **Food & Drink Recommendation**: The **{best['name']}** currently has the shortest line, with a wait time of **{best['waitTimeMinutes']} minutes**.\n\n"
                f"Other stands: {others_str}.\n\n"
                f"Would you like me to find the nearest restroom on your way there?"
            )
        return "The Food Court is currently busy. Pizza Stand and Drinks Tent are available on the East and South Concourses."

    # 3. Washroom / Restroom questions
    if (
        "restroom" in query
        or "washroom" in query
        or "toilet" in query
        or "loo" in query
    ):
        restrooms = [am for am in amenities if am["type"] == "restroom"]
        if restrooms:
            sorted_restrooms = sorted(
                restrooms, key=lambda x: x["waitTimeMinutes"]
            )
            best = sorted_restrooms[0]
            return (
                f"🚻 **Nearest Restroom**: The **{best['name']}** is your best option with a wait time of only **{best['waitTimeMinutes']} minutes**.\n\n"
                f"The other option (**{sorted_restrooms[1]['name']}**) currently has a **{sorted_restrooms[1]['waitTimeMinutes']} minute** wait.\n\n"
                f"Do you need to know if it has accessible stalls?"
            )
        return "Washrooms are located near the North Concourse and the Main Entrance. The Main washroom usually moves fastest."

    # 4. Crowd / Concourse density questions
    if (
        "crowd" in query
        or "concourse" in query
        or "busy" in query
        or "congested" in query
    ):
        congested = [z for z in zones if z["crowdLevel"] > 75]
        clear = [z for z in zones if z["crowdLevel"] < 45]

        reply = "📊 **Stadium Density Report**:\n"
        if congested:
            reply += (
                "- **High Congestion Zones (Avoid)**: "
                + ", ".join(
                    [
                        f"**{z['name']}** ({z['crowdLevel']}% full)"
                        for z in congested
                    ]
                )
                + "\n"
            )
        if clear:
            reply += (
                "- **Clear Zones**: "
                + ", ".join(
                    [
                        f"**{z['name']}** ({z['crowdLevel']}% full)"
                        for z in clear
                    ]
                )
                + "\n"
            )

        reply += "\nI suggest routing your movement through Clear Zones to avoid bottlenecks. Can I help plan an alternative route?"
        return reply

    return (
        "Hi there! I am your **AI Stadium Concierge** 🤖.\n\n"
        "I can help you navigate the stadium in real-time based on live crowds and telemetry. Try asking:\n"
        "- *Which gate is fastest to enter?*\n"
        "- *Where can I grab food with the shortest queue?*\n"
        "- *What washroom should I use right now?*\n"
        "- *Which areas of the stadium are overcrowded?*"
    )


@assistant_bp.route("/api/assistant/chat", methods=["POST"])
@require_auth
def assistant_chat() -> Union[Response, Tuple[Response, int]]:
    """Grounded AI Chat Concierge Endpoint.

    Checks user inputs, queries the Gemini model grounding with live telemetry data,
    and returns a structured Markdown response.
    """
    data = request.json or {}
    user_query: str = str(data.get("message", "")).strip()

    if not user_query:
        return (
            jsonify({"status": "error", "message": "Message cannot be empty"}),
            400,
        )

    if len(user_query) > 500:
        return (
            jsonify({"status": "error", "message": "Message exceeds maximum allowed length of 500 characters"}),
            400,
        )

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
    You are ArenaFlow's Grounded AI Stadium Concierge 🤖, helping attendees navigate the physical venue.
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
                model="gemini-1.5-flash", contents=system_context
            )
            response_text = response.text
            is_ai = True
        except Exception as e:
            logger.error(
                f"[AI] Gemini model generation failed: {e}. Falling back to rule-based."
            )

    if not is_ai:
        # Fallback to local rule-based engine
        response_text = local_concierge_fallback(user_query, state)
        if os.environ.get("GEMINI_API_KEY"):
            response_text += "\n\n*(Using local rule-based assistant fallback due to Gemini error)*"
        else:
            response_text += "\n\n*(Using local rule-based assistant - set GEMINI_API_KEY environment variable for full AI capabilities)*"

    return jsonify(
        {
            "status": "success",
            "message": response_text,
            "model": "Gemini-1.5-Flash" if is_ai else "Rule-based Engine",
            "timestamp": time.time(),
        }
    )
