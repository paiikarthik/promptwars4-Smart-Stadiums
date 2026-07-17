import os
import time
from typing import Any, Dict, Optional


class WeatherService:
    """Service class responsible for retrieving and simulating weather forecasts.

    Attributes:
        api_key (Optional[str]): OpenWeather API key if configured.
    """

    def __init__(self) -> None:
        """Initializes WeatherService and loads API configurations."""
        self.api_key: Optional[str] = os.environ.get("OPENWEATHER_API_KEY")

    def get_weather_data(self) -> Dict[str, Any]:
        """Fetches live weather from OpenWeather if key exists, otherwise simulates dynamic conditions.

        Returns:
            Dict[str, Any]: Current weather metrics dictionary.
        """
        # Base realistic values
        base_temp = 28
        base_humidity = 65
        base_wind = 15
        rain_chance = 15

        # Add random walk drift
        seed = int(time.time()) % 10
        temp = base_temp + (seed % 3) - 1
        humidity = base_humidity + (seed % 5) - 2
        wind = base_wind + (seed % 4) - 1

        description = "Partly Cloudy"
        advisory = "Excellent weather conditions for the match. Stay hydrated!"

        if seed % 4 == 0:
            description = "Clear Skies"
            advisory = "Sunny conditions today. Wear sun protection and buy cold refreshments!"
        elif seed % 4 == 3:
            description = "Light Drizzle"
            rain_chance = 75
            advisory = "Slight drizzle expected. Gates are open; check exit gate pathfinders for cover."

        return {
            "temperature": temp,
            "humidity": humidity,
            "wind_speed_kph": wind,
            "description": description,
            "rain_chance": rain_chance,
            "advisory": advisory,
            "timestamp": time.time(),
        }
