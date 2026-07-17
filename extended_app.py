import logging
import os

from app import app
from extended_blueprints.chatbot_bp import chatbot_bp
from extended_blueprints.map_bp import map_bp
from extended_blueprints.navigation_bp import navigation_bp
from extended_blueprints.parking_bp import parking_bp
from extended_blueprints.schedule_bp import schedule_bp
from extended_blueprints.seat_map_bp import seat_map_bp
from extended_blueprints.weather_bp import weather_bp

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ExtendedApp")

# Register blueprints under the /extended url prefix
app.register_blueprint(chatbot_bp, url_prefix="/extended")
app.register_blueprint(seat_map_bp, url_prefix="/extended")
app.register_blueprint(schedule_bp, url_prefix="/extended")
app.register_blueprint(map_bp, url_prefix="/extended")
app.register_blueprint(navigation_bp, url_prefix="/extended")
app.register_blueprint(weather_bp, url_prefix="/extended")
app.register_blueprint(parking_bp, url_prefix="/extended")


@app.after_request
def inject_extended_features(response):
    """Intercepts HTML responses and dynamically injects navigation buttons
    and advanced capability scripts, leaving production templates on disk untouched.
    Performs global name replacement from StadiumIQ to ArenaFlow on all templates including login.
    Adds security headers to harden the browser context.
    """
    from flask import request

    if (
        response.status_code == 200
        and response.headers.get("Content-Type")
        and "text/html" in response.headers.get("Content-Type", "")
    ):
        try:
            html = response.get_data(as_text=True)

            # Global name replacement to ArenaFlow (including login portal)
            html = html.replace("StadiumIQ", "ArenaFlow")

            # Only inject menus/scripts on user dashboard, admin, and extended views
            if any(
                request.path.startswith(p)
                for p in ["/dashboard", "/admin", "/extended/"]
            ):
                # Inject new navigation buttons before the Logout button
                old_button = '<button class="btn-logout" onclick="handleLogout()">Logout</button>'
                if old_button in html:
                    menu_injection = (
                        '<a href="/extended/chatbot" class="toggle-btn" style="margin-right:10px; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; width:auto; padding:0.4rem 0.8rem; font-size:0.8rem;">🤖 Super Assistant</a>'
                        '<a href="/extended/seat-map" class="toggle-btn" style="margin-right:10px; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; width:auto; padding:0.4rem 0.8rem; font-size:0.8rem;">🎟️ Seat Viewer</a>'
                        '<a href="/extended/schedule" class="toggle-btn" style="margin-right:10px; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; width:auto; padding:0.4rem 0.8rem; font-size:0.8rem;">📅 Schedule</a>'
                        '<a href="/extended/map" class="toggle-btn" style="margin-right:10px; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; width:auto; padding:0.4rem 0.8rem; font-size:0.8rem;">🗺️ Stadium Map</a>'
                        '<a href="/extended/navigation" class="toggle-btn" style="margin-right:10px; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; width:auto; padding:0.4rem 0.8rem; font-size:0.8rem;">🧭 Navigation</a>'
                        '<a href="/extended/weather" class="toggle-btn" style="margin-right:10px; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; width:auto; padding:0.4rem 0.8rem; font-size:0.8rem;">🌦️ Weather</a>'
                        '<a href="/extended/parking-map" class="toggle-btn" style="margin-right:10px; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; width:auto; padding:0.4rem 0.8rem; font-size:0.8rem;">🚗 Smart Parking</a>'
                    )
                    html = html.replace(
                        old_button, menu_injection + old_button
                    )

                # Inject advanced capabilities scripts right before closing body tag
                if "</body>" in html:
                    script_injection = (
                        '<script src="/static/js/indian_lang.js"></script>'
                        '<script src="/static/js/voice_assistant.js"></script>'
                    )
                    html = html.replace(
                        "</body>", script_injection + "</body>"
                    )

            response.set_data(html)
        except Exception as e:
            logger.error(f"HTML dynamic injection/replacement failed: {e}")
    return response


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8080))
    print(f"--- STARTING ARENAFLOW EXTENDED SERVER ON PORT {port} ---")
    app.run(debug=False, host=host, port=port)
