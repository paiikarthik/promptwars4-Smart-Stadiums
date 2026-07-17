import unittest
import json
import os
import sys

# Ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Use test database environment config
os.environ["TESTING"] = "true"

from extended_app import app  # noqa: E402
from app import db


class ExtendedAppTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

        # Initialize clean test database
        if not db.use_firebase:
            self.original_db_path = db.local_db_path
            db.local_db_path = "test_local_db.json"
            if os.path.exists(db.local_db_path):
                os.remove(db.local_db_path)
            db._init_local_db()

    def tearDown(self):
        if not db.use_firebase:
            if os.path.exists(db.local_db_path):
                os.remove(db.local_db_path)
            db.local_db_path = self.original_db_path

    def login_user(self, username, role="attendee"):
        from werkzeug.security import generate_password_hash

        db.register_user(username, generate_password_hash("password"), role)
        self.client.post(
            "/api/auth/login",
            data=json.dumps({"username": username, "password": "password"}),
            content_type="application/json",
        )

    def test_dynamic_html_injection(self):
        """Tests that loading the dashboard dynamically injects the extension links and scripts."""
        self.login_user("test_fan")
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)

        html = response.get_data(as_text=True)
        # Check injected menu buttons
        self.assertIn("🤖 Super Assistant", html)
        self.assertIn("🎟️ Seat Viewer", html)
        self.assertIn("📅 Schedule", html)
        self.assertIn("🗺️ Stadium Map", html)

        # Check injected scripts
        self.assertIn("/static/js/indian_lang.js", html)
        self.assertIn("/static/js/voice_assistant.js", html)

    def test_chatbot_super_assistant(self):
        """Tests the chatbot Super Assistant API endpoints and responses."""
        self.login_user("test_fan")

        # Rendering
        response = self.client.get("/extended/chatbot")
        self.assertEqual(response.status_code, 200)

        # Posting message (schedule query)
        response = self.client.post(
            "/extended/api/chatbot/message",
            data=json.dumps({"message": "What is today's match schedule?"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertTrue(
            "usa" in data["reply"].lower()
            or "england" in data["reply"].lower()
            or "fifa" in data["reply"].lower()
        )

        # Posting message (sustainability query)
        response = self.client.post(
            "/extended/api/chatbot/message",
            data=json.dumps(
                {"message": "Tell me about green sustainability features"}
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertTrue(
            "sustainability" in data["reply"].lower()
            or "carbon" in data["reply"].lower()
            or "eco" in data["reply"].lower()
        )

    def test_seat_map_api(self):
        """Tests seating grid and stand metrics."""
        self.login_user("test_fan")

        response = self.client.get("/extended/seat-map")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/extended/api/seat-map/data")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("sections", data)
        self.assertIn("sec-vip", data["seats"])

    def test_schedule_and_map_rendering(self):
        """Tests match schedule, interactive map, and navigation routes load successfully."""
        self.login_user("test_fan")

        response = self.client.get("/extended/schedule")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/extended/map")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/extended/navigation")
        self.assertEqual(response.status_code, 200)

    def test_weather_and_parking_endpoints(self):
        """Tests weather metrics and smart parking loads successfully."""
        self.login_user("test_fan")

        # Weather Page & API
        response = self.client.get("/extended/weather")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/extended/api/weather/data")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("temperature", data["weather"])

        # Parking map
        response = self.client.get("/extended/parking-map")
        self.assertEqual(response.status_code, 200)

    def test_regional_translations(self):
        """Tests the Indian Language Pack regional translations mapping."""
        self.login_user("test_fan")

        # Translate to Kannada
        response = self.client.post(
            "/extended/api/translation",
            data=json.dumps({"key": "lbl_match", "lang": "kn"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertEqual(
            data["translated"], "ಇಂದಿನ ಪಂದ್ಯ"
        )  # Check exact match

        # Translate to Hindi
        response = self.client.post(
            "/extended/api/translation",
            data=json.dumps({"key": "lbl_match", "lang": "hi"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["translated"], "आज का मैच")

    def test_csrf_protection_blocking(self):
        """Tests that CSRF checks block POST requests with mismatching Origin/Referer when not in test mode."""
        app.config["TESTING"] = False
        try:
            response = self.client.post(
                "/api/auth/register",
                data=json.dumps(
                    {"username": "csrf_test", "password": "password123"}
                ),
                content_type="application/json",
                headers={
                    "Origin": "http://malicious-attacker.com",
                    "Referer": "http://malicious-attacker.com/exploit",
                },
            )
            self.assertEqual(response.status_code, 403)
            self.assertIn(
                "blocked", json.loads(response.data)["message"].lower()
            )
        finally:
            app.config["TESTING"] = True

    def test_server_side_input_sanitization(self):
        """Tests that HTML script tags are safely stripped from user inputs."""
        # 1. Test registering with script tag in username (alphanumeric check will block it)
        reg_payload = {
            "username": "<script>alert('XSS')</script>xssuser",
            "password": "password123",
            "role": "attendee",
        }
        response = self.client.post(
            "/api/auth/register",
            data=json.dumps(reg_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        # 2. Test sanitize_html logic directly
        from app import sanitize_html

        dirty_input = "Row <script>alert('hack')</script> 12"
        clean_output = sanitize_html(dirty_input)
        self.assertNotIn("<script>", clean_output)
        self.assertNotIn("</script>", clean_output)
        self.assertEqual(clean_output, "Row  12")


if __name__ == "__main__":
    unittest.main()
