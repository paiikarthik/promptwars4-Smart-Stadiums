import json
import logging
import os
from typing import Any, Dict, Optional
from firebase_helper import StadiumDB

logger = logging.getLogger("ChatbotService")

# Try to import Google GenAI SDK
try:
    from google import genai
    import google.api_core.exceptions

    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class ChatbotService:
    """Service class managing the Super Assistant AI chatbot and grounding context mapping.

    Attributes:
        db (StadiumDB): Database client reference helper.
        gemini_client (Optional[genai.Client]): GenAI client session if configured.
    """

    def __init__(self, db: StadiumDB) -> None:
        """Initializes ChatbotService with database and Gemini configurations.

        Args:
            db (StadiumDB): Stadium database client.
        """
        self.db: StadiumDB = db
        self.gemini_client: Optional[genai.Client] = None
        if HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
            try:
                self.gemini_client = genai.Client(
                    api_key=os.environ.get("GEMINI_API_KEY")
                )
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[ChatbotService] Gemini initialization failed: {e}")

    def _get_static_grounding_data(self) -> Dict[str, Any]:
        """Provides static match, transit, tourist landmarks, and sustainability metadata.

        Returns:
            Dict[str, Any]: Static metadata mappings.
        """
        schedule = {
            "today": "Group Stage B - USA vs England (Starts at 19:30)",
            "week": [
                {"day": "Friday", "match": "Group Stage A - Argentina vs France"},
                {"day": "Saturday", "match": "Group Stage C - Mexico vs Spain"},
                {"day": "Sunday", "match": "Group Stage D - Canada vs Morocco"},
            ],
        }
        tourist_info = {
            "nearest_metro": "Stadium Metro Station (Purple Line) - 200m walking distance. Direct transit link.",
            "hotels": "MetLife Plaza Hotel (500m), East Rutherford Inn (1.2km)",
            "restaurants": "World Cup Diner (100m), Fan Zone Grill (200m)",
            "hospitals": "East Rutherford General Hospital (1.5km), Apex Care Center (2.0km)",
            "airport": "Newark Liberty International Airport (EWR) - connected via NJ Transit links.",
        }
        sustainability = {
            "water_stations": "Free eco-friendly water refilling stands are active at North and South Concourses.",
            "recycling_program": "Zero-waste green bins are located at all concession food stands.",
            "carbon_offset": "Attending fans taking the Purple Line Metro offset approximately 2.5kg of CO2.",
        }
        return {
            "schedule": schedule,
            "tourist_info": tourist_info,
            "sustainability": sustainability,
        }

    def get_grounding_context(self) -> Dict[str, Any]:
        """Compiles stadium, schedule, seating, coordinates, and tourist telemetry context.

        Returns:
            Dict[str, Any]: Live grounding context map.
        """
        state: Dict[str, Any] = self.db.get_simulation_state()
        capacity: int = 70000
        booked: int = 56210
        available: int = capacity - booked
        occupancy_pct: float = round((booked / capacity) * 100, 1)

        weather = {
            "temp": "26C",
            "condition": "Sunny",
            "advisory": "Wear caps and drink water!",
        }

        static_data = self._get_static_grounding_data()

        return {
            "stadium_name": "MetLife Stadium (Official FIFA World Cup 2026 Host Venue)",
            "capacity": capacity,
            "booked_seats": booked,
            "available_seats": available,
            "occupancy_percentage": f"{occupancy_pct}%",
            "weather": weather,
            "emergency_exits": "Gates North, South, East, and West are clear.",
            "restroom_locations": "Located behind Blocks A, B, D, F, and VIP lounges.",
            "medical_centers": "Medical stands active at NC and SC.",
            "parking_status": "Parking A: 80% full. Parking B: 65% full. Parking C: 95% full.",
            "merchandise_shop": "FIFA Official Merchandise shop located in Zone Merch Concourse.",
            "schedule": static_data["schedule"],
            "tourist_and_places": static_data["tourist_info"],
            "sustainability_program": static_data["sustainability"],
            "gates": [
                {"name": g["name"], "wait": g["waitTimeMinutes"]}
                for g in state.get("gates", [])
            ],
            "zones_density": [
                {"name": z["name"], "density": z["crowdLevel"]}
                for z in state.get("zones", [])
            ],
        }

    def _get_local_reply(self, message: str, context: Dict[str, Any]) -> str:
        """Helper that executes local rule-based response parsing for the chatbot.

        Args:
            message (str): Incoming user query.
            context (Dict[str, Any]): Telemetry context mappings.

        Returns:
            str: Preformatted Markdown format text answers.
        """
        q: str = message.lower()
        if "match" in q or "schedule" in q or "today" in q:
            return (
                f"🤖 **Assistant**: Today's Match: **{context['schedule']['today']}**.\n\n"
                f"**Upcoming Schedule**:\n"
                f"- Friday: Argentina vs France\n"
                f"- Saturday: Mexico vs Spain\n"
                f"- Sunday: Canada vs Morocco"
            )
        if any(w in q for w in ["sustainability", "eco", "green", "recycle", "carbon"]):
            return (
                f"🤖 **Assistant (FIFA 2026 Sustainability Program)**:\n"
                f"- **Eco Water**: {context['sustainability_program']['water_stations']}\n"
                f"- **Recycling**: {context['sustainability_program']['recycling_program']}\n"
                f"- **Carbon Offset**: {context['sustainability_program']['carbon_offset']}"
            )
        if "seat" in q or "capacity" in q or "book" in q:
            return (
                f"🤖 **Assistant**: Seating Status:\n"
                f"- **Total Capacity**: {context['capacity']}\n"
                f"- **Booked Seats**: {context['booked_seats']} (Occupancy: {context['occupancy_percentage']})\n"
                f"- **Available Seats**: {context['available_seats']}"
            )
        if "exit" in q or "emergency" in q:
            return f"🤖 **Assistant**: **Emergency Exits**: {context['emergency_exits']}"
        if "restroom" in q or "toilet" in q or "washroom" in q:
            return f"🤖 **Assistant**: **Restrooms**: {context['restroom_locations']}"
        if "medical" in q or "hospital" in q or "doctor" in q:
            return f"🤖 **Assistant**: **Medical Support**: {context['medical_centers']}"
        if any(w in q for w in ["metro", "hotel", "airport", "restaurant", "tourist"]):
            return (
                f"🤖 **Assistant (Tourist Hub)**:\n"
                f"- **Metro**: {context['tourist_and_places']['nearest_metro']}\n"
                f"- **Hotels**: {context['tourist_and_places']['hotels']}\n"
                f"- **Restaurants**: {context['tourist_and_places']['restaurants']}\n"
                f"- **Airport**: {context['tourist_and_places']['airport']}"
            )
        if "parking" in q:
            return f"🤖 **Assistant**: **Parking Status**: {context['parking_status']}"
        if "weather" in q:
            return f"🤖 **Assistant**: **Weather**: {context['weather']['condition']}, {context['weather']['temp']}. {context['weather']['advisory']}"

        return "🤖 **Assistant**: Ask me about stadium seating, schedules, parking, emergency exits, restrooms, or tourist spots!"

    def get_super_assistant_reply(self, message: str) -> str:
        """Asks Gemini to answer the user query based on the stadium grounding context.

        Args:
            message (str): Incoming user message prompt.

        Returns:
            str: AI generated response, falling back to local matches on failure.
        """
        context: Dict[str, Any] = self.get_grounding_context()

        system_prompt = f"""
        You are the ArenaFlow Super Assistant 🤖.
        You have direct access to live stadium coordinates, seating maps, schedules, weather, exits, and tourist places:

        {json.dumps(context, indent=2)}

        Answer the user's query precisely and accurately using the context above.
        - If they ask about matches or schedules, quote today's match or the weekly schedule.
        - If they ask about tourist recommendations (hotels, restaurants, metros), provide the exact metro details and hotels listed.
        - If they ask about seats, quote the booked/available stats.
        - Keep answers concise, helpful, and formatted in Markdown.
        """

        if self.gemini_client:
            for m in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                try:
                    response = self.gemini_client.models.generate_content(
                        model=m,
                        contents=system_prompt + f"\nUser Query: {message}",
                    )
                    res_text: str = response.text
                    return res_text
                except google.api_core.exceptions.GoogleAPIError as e:
                    err_msg = str(e)
                    key = os.environ.get("GEMINI_API_KEY")
                    if key and key in err_msg:
                        err_msg = err_msg.replace(key, "[REDACTED]")
                    logger.warning(
                        f"Failed to query Gemini model {m}: {err_msg}"
                    )

        return self._get_local_reply(message, context)
