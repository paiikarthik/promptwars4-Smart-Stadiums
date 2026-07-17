import time


class SOSService:
    def __init__(self, db):
        self.db = db

    def send_sos(self, seat, zone_id):
        """Creates a new emergency SOS alert in the database."""
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
            except Exception as e:
                print(f"[SOSService] Firebase write error: {e}")
        else:
            with self.db.lock:
                data = self.db._read_local_db()
                if "sos_alerts" not in data:
                    data["sos_alerts"] = []
                data["sos_alerts"].append(sos)
                self.db._write_local_db(data)

        # Also log an automatic danger alert in the global alerts center
        # to alert other admins/attendees
        self.db.add_alert(
            f"Emergency SOS triggered: Seat {seat} in Zone {zone_id}.",
            "danger",
            auto=True,
        )
        return sos

    def get_sos_alerts(self):
        """Fetches all active emergency alerts."""
        if self.db.use_firebase:
            try:
                docs = self.db.db.collection("sos_alerts").stream()
                alerts = [doc.to_dict() for doc in docs]
                return sorted(
                    alerts, key=lambda x: x["timestamp"], reverse=True
                )
            except Exception as e:
                print(f"[SOSService] Firebase read error: {e}")
                return []
        else:
            with self.db.lock:
                data = self.db._read_local_db()
                alerts = data.get("sos_alerts", [])
                return sorted(
                    alerts, key=lambda x: x["timestamp"], reverse=True
                )

    def update_sos_status(self, sos_id, status):
        """Updates status of an emergency alert."""
        if status not in ["Pending", "Accepted", "Resolved"]:
            return False

        if self.db.use_firebase:
            try:
                ref = self.db.db.collection("sos_alerts").document(sos_id)
                if ref.get().exists:
                    ref.update({"status": status})
                    return True
            except Exception as e:
                print(f"[SOSService] Firebase update error: {e}")
                return False
        else:
            with self.db.lock:
                data = self.db._read_local_db()
                sos_list = data.get("sos_alerts", [])
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
