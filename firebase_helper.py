import os
import json
import time
import threading
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("StadiumDB")

# Firebase SDK imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    import google.api_core.exceptions

    HAS_FIREBASE = True
except ImportError:
    HAS_FIREBASE = False


class StadiumDB:
    """Helper class managing connection to Firebase Firestore or local JSON database fallback.

    Attributes:
        use_firebase (bool): True if connected to Firebase, False otherwise.
        db (Optional[firestore.client]): Firestore database client session if connected.
        lock (threading.Lock): Mutex lock protecting local file operations.
        local_db_path (str): Relative system path to the local database file.
    """

    def __init__(self) -> None:
        """Initializes StadiumDB by checking credentials and selecting database engine."""
        self.use_firebase: bool = False
        self.db: Optional[Any] = None
        self.lock: threading.Lock = threading.Lock()
        self.local_db_path: str = "local_db.json"

        # Check if Firebase is available and configured
        if HAS_FIREBASE:
            # Look for service account credentials
            cred_path: str = os.environ.get(
                "FIREBASE_CREDENTIALS", "serviceAccountKey.json"
            )
            if os.path.exists(cred_path):
                try:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    self.db = firestore.client()
                    self.use_firebase = True
                    logger.info(
                        "[StadiumDB] Initialized successfully using Firebase Firestore."
                    )
                except (
                    ValueError,
                    google.api_core.exceptions.GoogleAPIError,
                ) as e:
                    logger.error(
                        f"[StadiumDB] Firebase initialization failed: {e}. Falling back to Local DB."
                    )
            else:
                logger.info(
                    "[StadiumDB] No serviceAccountKey.json found. Falling back to Local DB."
                )
        else:
            logger.info(
                "[StadiumDB] firebase-admin package not found. Falling back to Local DB."
            )

        if not self.use_firebase:
            self._init_local_db()

    def _get_default_db_data(self) -> Dict[str, Any]:
        """Generates default schema dictionary structure for fresh database initialization.

        Returns:
            Dict[str, Any]: Standard stadium portal schema.
        """
        return {
            "users": {},
            "simulation_state": {
                "occupancy": 52000,
                "capacity": 70000,
                "gates": [
                    {
                        "id": "gate-n",
                        "name": "North Gate",
                        "waitTimeMinutes": 12,
                    },
                    {
                        "id": "gate-s",
                        "name": "South Gate",
                        "waitTimeMinutes": 8,
                    },
                    {
                        "id": "gate-e",
                        "name": "East Gate",
                        "waitTimeMinutes": 22,
                    },
                    {
                        "id": "gate-w",
                        "name": "West Gate",
                        "waitTimeMinutes": 4,
                    },
                ],
                "zones": [
                    {
                        "id": "zone-nc",
                        "name": "North Concourse",
                        "crowdLevel": 45,
                    },
                    {
                        "id": "zone-sc",
                        "name": "South Concourse",
                        "crowdLevel": 62,
                    },
                    {
                        "id": "zone-food",
                        "name": "Food Court A",
                        "crowdLevel": 85,
                    },
                    {
                        "id": "zone-merch",
                        "name": "Merch Stand",
                        "crowdLevel": 78,
                    },
                    {"id": "zone-vip", "name": "VIP Lounge", "crowdLevel": 35},
                    {
                        "id": "zone-main",
                        "name": "Main Entrance",
                        "crowdLevel": 55,
                    },
                ],
                "amenities": [
                    {
                        "id": "am-rest-main",
                        "name": "Main Washroom",
                        "type": "restroom",
                        "waitTimeMinutes": 2,
                    },
                    {
                        "id": "am-rest-north",
                        "name": "North Washroom",
                        "type": "restroom",
                        "waitTimeMinutes": 8,
                    },
                    {
                        "id": "am-food-pizza",
                        "name": "Pizza Stand",
                        "type": "food",
                        "waitTimeMinutes": 15,
                    },
                    {
                        "id": "am-food-drinks",
                        "name": "Drinks Tent",
                        "type": "food",
                        "waitTimeMinutes": 5,
                    },
                ],
                "staff": {
                    "security": {"available": 10, "deployed": []},
                    "medical": {"available": 5, "deployed": []},
                },
            },
            "alerts": [],
            "dispatches": [],
        }

    def _init_local_db(self) -> None:
        """Initializes local JSON database with default structures if it doesn't exist."""
        with self.lock:
            if not os.path.exists(self.local_db_path):
                default_data = self._get_default_db_data()
                self._write_local_db(default_data)
                logger.info(
                    "[StadiumDB] Initialized fresh Local JSON database."
                )
            else:
                logger.info("[StadiumDB] Found existing Local JSON database.")

    def _read_local_db(self) -> Dict[str, Any]:
        """Reads local JSON DB file. Assumes lock is held.

        Returns:
            Dict[str, Any]: Loaded JSON structure or default structure on failure.
        """
        try:
            with open(self.local_db_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
                return data
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"[StadiumDB] Error reading local DB: {e}")
            return {
                "users": {},
                "simulation_state": {},
                "alerts": [],
                "dispatches": [],
            }

    def _write_local_db(self, data: Dict[str, Any]) -> None:
        """Writes to local JSON DB file. Assumes lock is held.

        Args:
            data (Dict[str, Any]): Data structure to write.
        """
        try:
            with open(self.local_db_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except OSError as e:
            logger.error(f"[StadiumDB] Error writing local DB: {e}")

    # --- USER AUTHENTICATION METHODS ---

    def register_user(
        self, username: str, password_hash: str, role: str
    ) -> bool:
        """Registers a new user profile.

        Args:
            username (str): Target unique username.
            password_hash (str): Securely hashed user password.
            role (str): Security role (admin or attendee).

        Returns:
            bool: True if registration succeeded, False if user exists or operation failed.
        """
        if self.use_firebase:
            try:
                user_ref = self.db.collection("users").document(username)
                if user_ref.get().exists:
                    return False
                user_ref.set(
                    {
                        "username": username,
                        "password_hash": password_hash,
                        "role": role,
                        "created_at": time.time(),
                    }
                )
                return True
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[StadiumDB] Firebase register error: {e}")
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
                    "created_at": time.time(),
                }
                self._write_local_db(data)
                return True

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Gets user profile by username.

        Args:
            username (str): Target username.

        Returns:
            Optional[Dict[str, Any]]: Profile dict or None if not found or database fails.
        """
        if self.use_firebase:
            try:
                user_ref = self.db.collection("users").document(username).get()
                if user_ref.exists:
                    user_dict: Dict[str, Any] = user_ref.to_dict()
                    return user_dict
                return None
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[StadiumDB] Firebase get_user error: {e}")
                return None
        else:
            with self.lock:
                data = self._read_local_db()
                val: Optional[Dict[str, Any]] = data["users"].get(username)
                return val

    # --- SIMULATION STATE METHODS ---

    def save_simulation_state(self, state: Dict[str, Any]) -> None:
        """Saves current simulation telemetry state.

        Args:
            state (Dict[str, Any]): Telemetry dictionary payload.
        """
        if self.use_firebase:
            try:
                self.db.collection("simulation_state").document("current").set(
                    state
                )
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[StadiumDB] Firebase save_state error: {e}")
        else:
            with self.lock:
                data = self._read_local_db()
                data["simulation_state"] = state
                self._write_local_db(data)

    def get_simulation_state(self) -> Dict[str, Any]:
        """Fetches current simulation telemetry state.

        Returns:
            Dict[str, Any]: Current telemetry state mapping.
        """
        if self.use_firebase:
            try:
                doc = (
                    self.db.collection("simulation_state")
                    .document("current")
                    .get()
                )
                if doc.exists:
                    state_dict: Dict[str, Any] = doc.to_dict()
                    return state_dict
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[StadiumDB] Firebase get_state error: {e}")

        # Local fallback if Firebase fails or is disabled
        with self.lock:
            data = self._read_local_db()
            fallback_state: Dict[str, Any] = data.get("simulation_state", {})
            return fallback_state

    # --- ALERTS & BROADCASTS METHODS ---

    def add_alert(
        self, message: str, alert_type: str = "info", auto: bool = False
    ) -> Dict[str, Any]:
        """Adds a warning/alert notification.

        Args:
            message (str): Visual message description.
            alert_type (str): Severity class (info, warning, danger, success).
            auto (bool): True if system-generated automatically, False if admin broadcast.

        Returns:
            Dict[str, Any]: Created alert metadata.
        """
        alert = {
            "id": f"{'auto' if auto else 'manual'}-{time.time()}",
            "message": message,
            "type": alert_type,
            "auto": auto,
            "timestamp": time.time(),
        }
        if self.use_firebase:
            try:
                self.db.collection("alerts").document(alert["id"]).set(alert)
                return alert
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[StadiumDB] Firebase add_alert error: {e}")

        # Local JSON write
        with self.lock:
            data = self._read_local_db()
            data["alerts"].append(alert)
            self._write_local_db(data)
            return alert

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Gets all active alerts sorted chronologically (newest first).

        Returns:
            List[Dict[str, Any]]: Alerts array list.
        """
        if self.use_firebase:
            try:
                docs = (
                    self.db.collection("alerts")
                    .order_by(
                        "timestamp", direction=firestore.Query.DESCENDING
                    )
                    .stream()
                )
                return [doc.to_dict() for doc in docs]
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[StadiumDB] Firebase get_alerts error: {e}")

        with self.lock:
            data = self._read_local_db()
            return sorted(
                data.get("alerts", []),
                key=lambda x: x["timestamp"],
                reverse=True,
            )

    def clear_auto_alerts(self) -> None:
        """Removes automated simulation-generated alerts from database."""
        if self.use_firebase:
            try:
                docs = (
                    self.db.collection("alerts")
                    .where("auto", "==", True)
                    .stream()
                )
                for doc in docs:
                    doc.reference.delete()
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(
                    f"[StadiumDB] Firebase clear_auto_alerts error: {e}"
                )
        else:
            with self.lock:
                data = self._read_local_db()
                data["alerts"] = [
                    a for a in data.get("alerts", []) if not a.get("auto")
                ]
                self._write_local_db(data)

    # --- DISPATCH LOGS METHODS ---

    def log_dispatch(self, staff_type: str, zone_id: str) -> Dict[str, Any]:
        """Logs a staff unit dispatch.

        Args:
            staff_type (str): Type of dispatched staff (security/medical).
            zone_id (str): Targeted zone.

        Returns:
            Dict[str, Any]: Logged dispatch dictionary.
        """
        dispatch = {
            "id": f"dispatch-{time.time()}",
            "staff_type": staff_type,
            "zone_id": zone_id,
            "timestamp": time.time(),
        }
        if self.use_firebase:
            try:
                self.db.collection("dispatches").document(dispatch["id"]).set(
                    dispatch
                )
                return dispatch
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[StadiumDB] Firebase log_dispatch error: {e}")

        with self.lock:
            data = self._read_local_db()
            data["dispatches"].append(dispatch)
            self._write_local_db(data)
            return dispatch

    def get_dispatches(self) -> List[Dict[str, Any]]:
        """Gets all dispatch logs sorted chronologically (newest first).

        Returns:
            List[Dict[str, Any]]: List of dispatches.
        """
        if self.use_firebase:
            try:
                docs = (
                    self.db.collection("dispatches")
                    .order_by(
                        "timestamp", direction=firestore.Query.DESCENDING
                    )
                    .stream()
                )
                return [doc.to_dict() for doc in docs]
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[StadiumDB] Firebase get_dispatches error: {e}")

        with self.lock:
            data = self._read_local_db()
            return sorted(
                data.get("dispatches", []),
                key=lambda x: x["timestamp"],
                reverse=True,
            )
