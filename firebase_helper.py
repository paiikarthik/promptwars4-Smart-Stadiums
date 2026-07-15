import os
import json
import time
import threading

# Firebase SDK imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    HAS_FIREBASE = True
except ImportError:
    HAS_FIREBASE = False

class StadiumDB:
    def __init__(self):
        self.use_firebase = False
        self.db = None
        self.lock = threading.Lock()
        self.local_db_path = "local_db.json"
        
        # Check if Firebase is available and configured
        if HAS_FIREBASE:
            # Look for service account credentials
            cred_path = os.environ.get("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
            if os.path.exists(cred_path):
                try:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    self.db = firestore.client()
                    self.use_firebase = True
                    print("[StadiumDB] Initialized successfully using Firebase Firestore.")
                except Exception as e:
                    print(f"[StadiumDB] Firebase initialization failed: {e}. Falling back to Local DB.")
            else:
                print("[StadiumDB] No serviceAccountKey.json found. Falling back to Local DB.")
        else:
            print("[StadiumDB] firebase-admin package not found. Falling back to Local DB.")

        if not self.use_firebase:
            self._init_local_db()

    def _init_local_db(self):
        """Initializes local JSON database with default structures if it doesn't exist."""
        with self.lock:
            if not os.path.exists(self.local_db_path):
                default_data = {
                    "users": {},
                    "simulation_state": {
                        "occupancy": 52000,
                        "capacity": 70000,
                        "gates": [
                            {"id": "gate-n", "name": "North Gate", "waitTimeMinutes": 12},
                            {"id": "gate-s", "name": "South Gate", "waitTimeMinutes": 8},
                            {"id": "gate-e", "name": "East Gate", "waitTimeMinutes": 22},
                            {"id": "gate-w", "name": "West Gate", "waitTimeMinutes": 4},
                        ],
                        "zones": [
                            {"id": "zone-nc", "name": "North Concourse", "crowdLevel": 45},
                            {"id": "zone-sc", "name": "South Concourse", "crowdLevel": 62},
                            {"id": "zone-food", "name": "Food Court A", "crowdLevel": 85},
                            {"id": "zone-merch", "name": "Merch Stand", "crowdLevel": 78},
                            {"id": "zone-vip", "name": "VIP Lounge", "crowdLevel": 35},
                            {"id": "zone-main", "name": "Main Entrance", "crowdLevel": 55},
                        ],
                        "amenities": [
                            {"id": "am-rest-main", "name": "Main Washroom", "type": "restroom", "waitTimeMinutes": 2},
                            {"id": "am-rest-north", "name": "North Washroom", "type": "restroom", "waitTimeMinutes": 8},
                            {"id": "am-food-pizza", "name": "Pizza Stand", "type": "food", "waitTimeMinutes": 15},
                            {"id": "am-food-drinks", "name": "Drinks Tent", "type": "food", "waitTimeMinutes": 5},
                        ],
                        "staff": {
                            "security": {"available": 10, "deployed": []},
                            "medical": {"available": 5, "deployed": []}
                        }
                    },
                    "alerts": [],
                    "dispatches": []
                }
                self._write_local_db(default_data)
                print("[StadiumDB] Initialized fresh Local JSON database.")
            else:
                print("[StadiumDB] Found existing Local JSON database.")

    def _read_local_db(self):
        """Reads local JSON DB file. Assumes lock is held."""
        try:
            with open(self.local_db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[StadiumDB] Error reading local DB: {e}")
            return {"users": {}, "simulation_state": {}, "alerts": [], "dispatches": []}

    def _write_local_db(self, data):
        """Writes to local JSON DB file. Assumes lock is held."""
        try:
            with open(self.local_db_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[StadiumDB] Error writing local DB: {e}")

    # --- USER AUTHENTICATION METHODS ---
    
    def register_user(self, username, password_hash, role):
        """Registers a user. Returns True if successful, False if user exists."""
        if self.use_firebase:
            try:
                user_ref = self.db.collection("users").document(username)
                if user_ref.get().exists:
                    return False
                user_ref.set({
                    "username": username,
                    "password_hash": password_hash,
                    "role": role,
                    "created_at": time.time()
                })
                return True
            except Exception as e:
                print(f"[StadiumDB] Firebase register error: {e}")
                return False
        else:
            with self.lock:
                data = self._read_local_db()
                if username in data["users"]:
                    return False
                data["users"][username] = {
                    "username": username,
                    "password_hash": password_hash,
                    "role": role,
                    "created_at": time.time()
                }
                self._write_local_db(data)
                return True

    def get_user(self, username):
        """Gets user profile by username."""
        if self.use_firebase:
            try:
                user_ref = self.db.collection("users").document(username).get()
                if user_ref.exists:
                    return user_ref.to_dict()
                return None
            except Exception as e:
                print(f"[StadiumDB] Firebase get_user error: {e}")
                return None
        else:
            with self.lock:
                data = self._read_local_db()
                return data["users"].get(username)

    # --- SIMULATION STATE METHODS ---

    def save_simulation_state(self, state):
        """Saves current simulation telemetry state."""
        if self.use_firebase:
            try:
                self.db.collection("simulation_state").document("current").set(state)
            except Exception as e:
                print(f"[StadiumDB] Firebase save_state error: {e}")
        else:
            with self.lock:
                data = self._read_local_db()
                data["simulation_state"] = state
                self._write_local_db(data)

    def get_simulation_state(self):
        """Fetches current simulation telemetry state."""
        if self.use_firebase:
            try:
                doc = self.db.collection("simulation_state").document("current").get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                print(f"[StadiumDB] Firebase get_state error: {e}")
        
        # Local fallback if Firebase fails or is disabled
        with self.lock:
            data = self._read_local_db()
            return data.get("simulation_state", {})

    # --- ALERTS & BROADCASTS METHODS ---

    def add_alert(self, message, alert_type="info", auto=False):
        """Adds a warning/alert notification."""
        alert = {
            "id": f"{'auto' if auto else 'manual'}-{time.time()}",
            "message": message,
            "type": alert_type,
            "auto": auto,
            "timestamp": time.time()
        }
        if self.use_firebase:
            try:
                self.db.collection("alerts").document(alert["id"]).set(alert)
                return alert
            except Exception as e:
                print(f"[StadiumDB] Firebase add_alert error: {e}")
        
        # Local JSON write
        with self.lock:
            data = self._read_local_db()
            data["alerts"].append(alert)
            self._write_local_db(data)
            return alert

    def get_alerts(self):
        """Gets all active alerts."""
        if self.use_firebase:
            try:
                docs = self.db.collection("alerts").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
                return [doc.to_dict() for doc in docs]
            except Exception as e:
                print(f"[StadiumDB] Firebase get_alerts error: {e}")
        
        with self.lock:
            data = self._read_local_db()
            # Sort newest first
            return sorted(data.get("alerts", []), key=lambda x: x["timestamp"], reverse=True)

    def clear_auto_alerts(self):
        """Removes automated alerts (cleanup triggered by simulation)."""
        if self.use_firebase:
            try:
                # Query and delete in Firebase
                docs = self.db.collection("alerts").where("auto", "==", True).stream()
                for doc in docs:
                    doc.reference.delete()
            except Exception as e:
                print(f"[StadiumDB] Firebase clear_auto_alerts error: {e}")
        else:
            with self.lock:
                data = self._read_local_db()
                data["alerts"] = [a for a in data.get("alerts", []) if not a.get("auto")]
                self._write_local_db(data)

    # --- DISPATCH LOGS METHODS ---

    def log_dispatch(self, staff_type, zone_id):
        """Logs a staff unit dispatch."""
        dispatch = {
            "id": f"dispatch-{time.time()}",
            "staff_type": staff_type,
            "zone_id": zone_id,
            "timestamp": time.time()
        }
        if self.use_firebase:
            try:
                self.db.collection("dispatches").document(dispatch["id"]).set(dispatch)
                return dispatch
            except Exception as e:
                print(f"[StadiumDB] Firebase log_dispatch error: {e}")
        
        with self.lock:
            data = self._read_local_db()
            data["dispatches"].append(dispatch)
            self._write_local_db(data)
            return dispatch

    def get_dispatches(self):
        """Gets all dispatch logs."""
        if self.use_firebase:
            try:
                docs = self.db.collection("dispatches").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
                return [doc.to_dict() for doc in docs]
            except Exception as e:
                print(f"[StadiumDB] Firebase get_dispatches error: {e}")
        
        with self.lock:
            data = self._read_local_db()
            return sorted(data.get("dispatches", []), key=lambda x: x["timestamp"], reverse=True)
