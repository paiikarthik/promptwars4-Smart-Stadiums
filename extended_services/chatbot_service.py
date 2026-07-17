import json
import logging
import os

logger = logging.getLogger("ChatbotService")

# Try to import Google GenAI SDK
try:
    from google import genai

    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class ChatbotService:
    def __init__(self, db):
        self.db = db
        self.gemini_client = None
        if HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
            try:
                self.gemini_client = genai.Client(
                    api_key=os.environ.get("GEMINI_API_KEY")
                )
            except Exception:
                pass

    def get_grounding_context(self):
        """Compiles stadium, schedule, seating, coordinates, and tourist telemetry context."""
        state = self.db.get_simulation_state()

        # Seating metrics
        capacity = 70000
        booked = 56210
        available = capacity - booked
        occupancy_pct = round((booked / capacity) * 100, 1)

        # Weather details
        weather = {
            "temp": "26C",
            "condition": "Sunny",
            "advisory": "Wear caps and drink water!",
        }

        # Exits, Volunteers, and Sustainability
        emergency_exits = "Gates North, South, East, and West are clear. FIFA World Cup 2026 Volunteers are stationed at every sector exit in green uniforms."
        restrooms = "Located behind Blocks A, B, D, F, and VIP lounges."
        medical = "Medical stands are active at North Concourse (Zone NC) and South Entrance (Zone SC)."
        parking = "Parking A (North): 80% full. Parking B (South): 65% full. Parking C (VIP): 95% full."
        merchandise = (
            "FIFA Official Merchandise shop located in Zone Merch Concourse."
        )

        # FIFA World Cup 2026 Schedule
        schedule = {
            "today": "Group Stage B - USA vs England (Starts at 19:30)",
            "week": [
                {
                    "day": "Friday",
                    "match": "Group Stage A - Argentina vs France",
                },
                {
                    "day": "Saturday",
                    "match": "Group Stage C - Mexico vs Spain",
                },
                {
                    "day": "Sunday",
                    "match": "Group Stage D - Canada vs Morocco",
                },
            ],
        }

        # FIFA Fan Zones and Transit
        tourist_info = {
            "nearest_metro": "Stadium Metro Station (Purple Line) - 200m walking distance. Direct transit link to the FIFA Fan Fest zone.",
            "hotels": "MetLife Plaza Hotel (500m), East Rutherford Inn (1.2km)",
            "restaurants": "World Cup Diner (100m), Fan Zone Grill (200m)",
            "hospitals": "East Rutherford General Hospital (1.5km), Apex Care Center (2.0km)",
            "airport": "Newark Liberty International Airport (EWR) - connected via NJ Transit train links.",
        }

        # Sustainability Program Metrics
        sustainability = {
            "water_stations": "Free eco-friendly water refilling stands are active at North and South Concourses to eliminate single-use plastic.",
            "recycling_program": "Zero-waste green bins are located at all concession food stands.",
            "carbon_offset": "Attending fans taking the Purple Line Metro offset approximately 2.5kg of CO2 emissions compared to driving.",
        }

        context = {
            "stadium_name": "MetLife Stadium (Official FIFA World Cup 2026 Host Venue)",
            "capacity": capacity,
            "booked_seats": booked,
            "available_seats": available,
            "occupancy_percentage": f"{occupancy_pct}%",
            "weather": weather,
            "emergency_exits": emergency_exits,
            "restroom_locations": restrooms,
            "medical_centers": medical,
            "parking_status": parking,
            "merchandise_shop": merchandise,
            "schedule": schedule,
            "tourist_and_places": tourist_info,
            "sustainability_program": sustainability,
            "gates": [
                {"name": g["name"], "wait": g["waitTimeMinutes"]}
                for g in state.get("gates", [])
            ],
            "zones_density": [
                {"name": z["name"], "density": z["crowdLevel"]}
                for z in state.get("zones", [])
            ],
        }
        return context

    def get_super_assistant_reply(self, message):
        """Asks Gemini to answer the user query based on the stadium grounding context.
        Falls back to local rule-based matching if Gemini is unavailable.
        """
        context = self.get_grounding_context()

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
            # Fallback across supported models (Gemini 2.5, 2.0, and 1.5)
            for m in [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
            ]:
                try:
                    response = self.gemini_client.models.generate_content(
                        model=m,
                        contents=system_prompt + f"\nUser Query: {message}",
                    )
                    return response.text
                except Exception as e:
                    # Security: Redact API Key from error logs to prevent credential leakage
                    err_msg = str(e)
                    key = os.environ.get("GEMINI_API_KEY")
                    if key and key in err_msg:
                        err_msg = err_msg.replace(key, "[REDACTED]")
                    logger.warning(
                        f"Failed to query Gemini model {m}: {err_msg}"
                    )

        # Local rule-based fallback
        q = message.lower()

        if "match" in q or "schedule" in q or "today" in q:
            return (
                f"🤖 **Assistant**: Today's Match: **{context['schedule']['today']}**.\n\n"
                f"**Upcoming Schedule**:\n"
                f"- Friday: Group Stage A - Argentina vs France\n"
                f"- Saturday: Group Stage C - Mexico vs Spain\n"
                f"- Sunday: Group Stage D - Canada vs Morocco"
            )

        if (
            "sustainability" in q
            or "eco" in q
            or "green" in q
            or "recycle" in q
            or "carbon" in q
        ):
            return (
                f"🤖 **Assistant (FIFA 2026 Sustainability Program)**:\n"
                f"- **Eco Water refilling**: {context['sustainability_program']['water_stations']}\n"
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

        if (
            "metro" in q
            or "hotel" in q
            or "airport" in q
            or "restaurant" in q
            or "tourist" in q
        ):
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

        return (
            "🤖 **Assistant**: I can guide you through the stadium seating, schedules, parking, "
            "emergency exits, restrooms, medical dispatches, and nearby tourist metro/hotels. Ask me anything!"
        )
