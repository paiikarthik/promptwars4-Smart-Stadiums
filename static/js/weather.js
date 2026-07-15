// --- WEATHER EXPLORER COMPONENT ---

async function loadWeatherPageMetrics() {
    try {
        const response = await fetch("/extended/api/weather/data");
        const data = await response.json();
        if (!response.ok) return;

        const w = data.weather;
        document.getElementById("weather-val-temp").textContent = `${w.temperature}°C`;
        document.getElementById("weather-val-desc").textContent = w.description;
        document.getElementById("weather-val-rain").textContent = `${w.rain_chance}%`;
        document.getElementById("weather-val-humid").textContent = `${w.humidity}%`;
        document.getElementById("weather-val-wind").textContent = `${w.wind_speed_kph} kph`;
        document.getElementById("weather-val-advisory").textContent = w.advisory;
    } catch (e) {
        console.error("Error loading weather details", e);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadWeatherPageMetrics();
    // Auto-update every 15 seconds
    setInterval(loadWeatherPageMetrics, 15000);
});
