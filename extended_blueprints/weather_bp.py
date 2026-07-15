from flask import Blueprint, render_template, jsonify, session
from app import require_auth
from extended_services.weather_service import WeatherService

weather_bp = Blueprint("weather_bp", __name__)
weather_svc = WeatherService()

@weather_bp.route("/weather")
@require_auth
def weather_page():
    return render_template("weather.html", username=session.get("username"))

@weather_bp.route("/api/weather/data")
@require_auth
def get_weather_data_api():
    w = weather_svc.get_weather_data()
    return jsonify({"status": "success", "weather": w})
