# ArenaFlow: FIFA World Cup 2026 Smart Stadium Portal

**ArenaFlow** (originally StadiumIQ) is an advanced, production-grade Web Portal designed to elevate the **FIFA World Cup 2026** matchday operations and fan experience. Combining live telemetry streams, interactive geolocation systems, regional accessibility, and Generative AI, ArenaFlow serves as a comprehensive dashboard for fans, venue volunteers, and operations managers at MetLife Stadium.

---

##  Key Extension Modules

1. ** AI Stadium Super Assistant**:
   A Gemini-grounded chat concierge answering queries on parking lot slots, restrooms, concessions, emergency exits, and transit routes. Incorporates a dynamic fallback loop supporting `gemini-2.5-flash`, `gemini-2.0-flash`, and `gemini-1.5-flash`.
2. **Stadium Seat Viewer**:
   An interactive grid map of sections tracking VIP, wheelchair-accessible, occupied, and vacant seats with real-time capacity percentage counters.
3. ** Match Schedule Module**:
   A live countdown timer showing the time remaining until kickoff, alongside team formations, gates opening notices, and a 7-day tournament schedule.
4. ** Interactive Stadium Map**:
   A multi-layered Leaflet (dark mode) & Google Maps engine mapping first-aid zones, ATMs, water stands, food courts, and entrances.
5. ** Google Directions Navigator**:
   A shortest-path routing tool directing users from their seat blocks to target amenities.
6. ** Indian Language Pack (13 Languages)**:
   A regional accessibility switch supporting English, Hindi, Kannada, Tamil, Telugu, Malayalam, Marathi, Gujarati, Punjabi, Bengali, Urdu (with RTL layouts), Odia, and Konkani.
7. **Voice Assistant (STT & TTS)**:
   Speech-to-text recording inputs and text-to-speech audio voice narration, integrated directly into the chat console.
8. ** Weather Forecasting Panel**:
   A real-time matchday weather widget listing temperatures, wind speeds, humidity, and active sun/rain warnings.
9. **Smart Parking**:
   A transit lot manager displaying available spots and routing users directly from their parking lots to the nearest gate entrances.
10. ** AI Tourist Assistant**:
    An AI tour recommender suggesting nearby metro stations, official FIFA Fan Zones, hotel options, hospitals, and airports with directions.

---

##  Security & Code Quality Standards

* **XSS Sanitization**: User inputs and chatbot messages are escaped with an HTML sanitizer before rendering markdown, mitigating script injections.
* **Header Hardening**: Enforces strict security headers:
  * `X-Frame-Options: DENY` (prevents clickjacking)
  * `X-Content-Type-Options: nosniff` (prevents MIME sniffing)
  * `X-XSS-Protection: 1; mode=block`
* **Input Constraints**: Restricts prompt inputs to 500 characters to prevent buffer flooding/prompt injection.
* **Translation Caching**: Implements a client-side `localStorage` cache for translated keys. Page transitions and language switches load instantly with **zero redundant API queries**, conserving network resources.

---

##  Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/paiikarthik/promptwars4-Smart-Stadiums.git
   cd promptwars4-Smart-Stadiums
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment Variables**:
   Set your Google Gemini API key:
   * **Windows (PowerShell)**:
     ```powershell
     $env:GEMINI_API_KEY="your-gemini-key"
     ```
   * **macOS/Linux**:
     ```bash
     export GEMINI_API_KEY="your-gemini-key"
     ```
4. **Run Server**:
   ```bash
   python extended_app.py
   ```
   Open **`http://localhost:8080`** in your browser.

---

##  Running Verification Tests

Run the automated integration test suite covering blueprints, chatbot replies, regional languages, and html injections:
```bash
python test_extended.py
```

---
