import time
import logging
from typing import Any, Dict, List
from firebase_helper import StadiumDB

logger = logging.getLogger("SOSService")

# Try to import Google GenAI exceptions if available
try:
    import google.api_core.exceptions
except ImportError:
    pass


class SOSService:
    """Service class managing fan emergency SOS alerts.

    Attributes:
        db (StadiumDB): Stadium database client.
    """

    def __init__(self, db: StadiumDB) -> None:
        """Initializes SOSService with database dependency.

        Args:
            db (StadiumDB): Stadium database client helper.
        """
        self.db: StadiumDB = db

    def send_sos(self, seat: str, zone_id: str) -> Dict[str, Any]:
        """Creates a new emergency SOS alert in the database and triggers a global danger alert.

        Args:
            seat (str): Seat name identifier where the alert was triggered.
            zone_id (str): Stadium zone identifier.

        Returns:
            Dict[str, Any]: Saved SOS alert structure.
        """
        sos = {
            "id": f"sos-{time.time()}",
            "seat": str(seat).strip(),
            "zone_id": zone_id,
            "timestamp": time.time(),
            "status": "Pending",  # Pending, Accepted, Resolved
        }

        if self.db.use_firebase:
            try:
                self.db.db.collection("sos_alerts").document(sos["id"]).set(
                    sos
                )
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[SOSService] Firebase write error: {e}")
        else:
            with self.db.lock:
                data = self.db._read_local_db()
                if "sos_alerts" not in data:
                    data["sos_alerts"] = []
                data["sos_alerts"].append(sos)
                self.db._write_local_db(data)

        # Also log an automatic danger alert in the global alerts center
        self.db.add_alert(
            f"Emergency SOS triggered: Seat {seat} in Zone {zone_id}.",
            "danger",
            auto=True,
        )
        return sos

    def get_sos_alerts(self) -> List[Dict[str, Any]]:
        """Fetches all active emergency alerts sorted chronologically (newest first).

        Returns:
            List[Dict[str, Any]]: Array of SOS alerts.
        """
        if self.db.use_firebase:
            try:
                docs = self.db.db.collection("sos_alerts").stream()
                alerts = [doc.to_dict() for doc in docs]
                return sorted(
                    alerts, key=lambda x: x["timestamp"], reverse=True
                )
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[SOSService] Firebase read error: {e}")
                return []
        else:
            with self.db.lock:
                data = self.db._read_local_db()
                alerts_local: List[Dict[str, Any]] = data.get("sos_alerts", [])
                return sorted(
                    alerts_local, key=lambda x: x["timestamp"], reverse=True
                )

    def update_sos_status(self, sos_id: str, status: str) -> bool:
        """Updates status (Pending, Accepted, Resolved) of an active emergency alert.

        Args:
            sos_id (str): Targeted SOS alert identifier.
            status (str): New status string.

        Returns:
            bool: True if status updated successfully, False otherwise.
        """
        if status not in ["Pending", "Accepted", "Resolved"]:
            return False

        if self.db.use_firebase:
            try:
                ref = self.db.db.collection("sos_alerts").document(sos_id)
                if ref.get().exists:
                    ref.update({"status": status})
                    return True
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[SOSService] Firebase update error: {e}")
                return False
        else:
            with self.db.lock:
                data = self.db._read_local_db()
                sos_list: List[Dict[str, Any]] = data.get("sos_alerts", [])
                found = False
                for s in sos_list:
                    if s["id"] == sos_id:
                        s["status"] = status
                        found = True
                        break
                if found:
                    self.db._write_local_db(data)
                    return True
        return False
