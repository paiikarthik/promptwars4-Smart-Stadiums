import os
import json
import unittest
from app import app, db
from firebase_helper import StadiumDB

class StadiumIQTest(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        
        # We ensure a clean local test DB if running locally
        if not db.use_firebase:
            self.original_db_path = db.local_db_path
            db.local_db_path = "test_local_db.json"
            if os.path.exists(db.local_db_path):
                os.remove(db.local_db_path)
            db._init_local_db()

    def tearDown(self):
        # Clean up test DB
        if not db.use_firebase:
            if os.path.exists(db.local_db_path):
                os.remove(db.local_db_path)
            db.local_db_path = self.original_db_path

    # --- DATABASE MANAGER TESTS ---

    def test_database_user_registration(self):
        """Test database level registration and check duplicates."""
        # Clean register
        success = db.register_user("testuser", "hashed_pwd", "attendee")
        self.assertTrue(success)
        
        # Duplicate register
        success2 = db.register_user("testuser", "hashed_pwd2", "admin")
        self.assertFalse(success2)
        
        # Fetch user
        user = db.get_user("testuser")
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "attendee")
        self.assertEqual(user["password_hash"], "hashed_pwd")

    def test_simulation_state_save_get(self):
        """Test saving and getting simulation state."""
        state = {
            "occupancy": 12345,
            "capacity": 70000,
            "gates": [{"id": "g1", "name": "Gate 1", "waitTimeMinutes": 5}],
            "zones": [],
            "amenities": [],
            "staff": {"security": {"available": 5, "deployed": []}}
        }
        db.save_simulation_state(state)
        fetched = db.get_simulation_state()
        self.assertEqual(fetched["occupancy"], 12345)
        self.assertEqual(fetched["gates"][0]["waitTimeMinutes"], 5)

    def test_alerts_add_get_clear(self):
        """Test adding, listing, and cleaning alert items."""
        db.clear_auto_alerts()
        
        # Add manual alert
        alert1 = db.add_alert("Manual danger", "danger", auto=False)
        self.assertEqual(alert1["type"], "danger")
        self.assertFalse(alert1["auto"])
        
        # Add auto alert
        alert2 = db.add_alert("Auto check", "warning", auto=True)
        self.assertTrue(alert2["auto"])
        
        # Fetch
        alerts = db.get_alerts()
        self.assertTrue(len(alerts) >= 2)
        
        # Clear auto
        db.clear_auto_alerts()
        alerts_cleared = db.get_alerts()
        self.assertTrue(any(a["id"] == alert1["id"] for a in alerts_cleared))
        self.assertFalse(any(a["id"] == alert2["id"] for a in alerts_cleared))

    # --- FLASK ENDPOINT ROUTE TESTS ---

    def test_portal_route(self):
        """Test accessing portal index returns HTTP 200."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_dashboard_redirects(self):
        """Test that accessing dashboards without authentication redirects to Portal."""
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.headers.get("Location", ""))

    def test_api_unauthorized_auth_check(self):
        """Test that API calls without session return 401."""
        response = self.client.get("/api/telemetry")
        self.assertEqual(response.status_code, 401)

    def test_flask_user_auth_flow(self):
        """Test registering and logging in through Flask APIs."""
        # 1. Register through API
        reg_payload = {
            "username": "apiuser",
            "password": "apipassword",
            "role": "attendee"
        }
        response = self.client.post("/api/auth/register", 
                                    data=json.dumps(reg_payload),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200)
        
        # 2. Login through API
        login_payload = {
            "username": "apiuser",
            "password": "apipassword"
        }
        response = self.client.post("/api/auth/login",
                                    data=json.dumps(login_payload),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["username"], "apiuser")
        self.assertEqual(data["role"], "attendee")
        
        # 3. Access dashboard now that authenticated (session is maintained by client)
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        
        # 4. Telemetry should be accessible
        response = self.client.get("/api/telemetry")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")

    def test_admin_only_privileges(self):
        """Test that attendee cannot access admin endpoints."""
        # Login as attendee
        from werkzeug.security import generate_password_hash
        db.register_user("fan", generate_password_hash("fanpass"), "attendee")
        self.client.post("/api/auth/login",
                         data=json.dumps({"username": "fan", "password": "fanpass"}),
                         content_type="application/json")
        
        # Attempt broadcast
        response = self.client.post("/api/admin/broadcast",
                                    data=json.dumps({"message": "Unauthorized broadcast", "type": "danger"}),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 403)
        
        # Attempt admin page
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 302) # Redirects back to dashboard

if __name__ == "__main__":
    unittest.main()
