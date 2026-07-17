import random
from typing import Any, Dict, List
from firebase_helper import StadiumDB


class AnalyticsService:
    """Service class responsible for compiling operations analytics metrics.

    Attributes:
        db (StadiumDB): The stadium database helper object.
    """

    def __init__(self, db: StadiumDB) -> None:
        """Initializes AnalyticsService with database interface dependency.

        Args:
            db (StadiumDB): Stadium database client.
        """
        self.db: StadiumDB = db

    def _compute_crowd_trends(self, current_occupancy: int, capacity: int) -> List[Dict[str, Any]]:
        """Simulates 2 hours of historical crowd trends in 10-minute intervals.

        Args:
            current_occupancy (int): Current count of stadium visitors.
            capacity (int): Stadium maximum capacity.

        Returns:
            List[Dict[str, Any]]: Array of trend data points.
        """
        crowd_history: List[Dict[str, Any]] = []
        base_occupancy: int = current_occupancy - 12000
        for i in range(12):
            factor: float = (i + 1) / 12
            occupancy_val: int = int(
                base_occupancy
                + (current_occupancy - base_occupancy) * factor
                + random.randint(-1000, 1000)
            )
            occupancy_val = max(1000, min(capacity, occupancy_val))
            crowd_history.append(
                {
                    "time": f"{(i * 10)} mins ago" if i > 0 else "Just Now",
                    "occupancy": occupancy_val,
                }
            )
        crowd_history.reverse()
        return crowd_history

    def _compute_summary(
        self,
        gates: List[Dict[str, Any]],
        dispatches: List[Dict[str, Any]],
        alerts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculates peak metrics, staff dispatches, and alerts.

        Args:
            gates (List[Dict[str, Any]]): List of entrance gate configurations.
            dispatches (List[Dict[str, Any]]): List of logged dispatches.
            alerts (List[Dict[str, Any]]): List of alerts.

        Returns:
            Dict[str, Any]: Compiled summary metrics.
        """
        security_dispatches: int = len(
            [d for d in dispatches if d.get("staff_type") == "security"]
        )
        medical_dispatches: int = len(
            [d for d in dispatches if d.get("staff_type") == "medical"]
        )
        manual_alerts: int = len([a for a in alerts if not a.get("auto")])
        auto_alerts: int = len([a for a in alerts if a.get("auto")])

        gate_times: List[int] = (
            [g["waitTimeMinutes"] for g in gates] if gates else [5, 10, 15]
        )
        peak_wait: int = max(gate_times)
        avg_wait: float = sum(gate_times) / len(gate_times)

        ai_chat_queries: int = 24 + len(dispatches) * 3 + random.randint(1, 10)
        fan_page_views: int = 152 + len(dispatches) * 12 + random.randint(5, 30)

        return {
            "peakWaitTime": peak_wait,
            "avgWaitTime": round(avg_wait, 1),
            "totalDispatches": len(dispatches),
            "securityDispatches": security_dispatches,
            "medicalDispatches": medical_dispatches,
            "totalAlerts": len(alerts),
            "manualAlerts": manual_alerts,
            "autoAlerts": auto_alerts,
            "aiChatQueries": ai_chat_queries,
            "fanActivity": fan_page_views,
        }

    def get_analytics(self) -> Dict[str, Any]:
        """Compiles analytics metrics using active DB logs and realistic simulations.

        Returns:
            Dict[str, Any]: Analytics dataset.
        """
        state: Dict[str, Any] = self.db.get_simulation_state()
        alerts: List[Dict[str, Any]] = self.db.get_alerts()
        dispatches: List[Dict[str, Any]] = self.db.get_dispatches()

        current_occupancy: int = state.get("occupancy", 52000)
        capacity: int = state.get("capacity", 70000)
        gates: List[Dict[str, Any]] = state.get("gates", [])

        crowd_history = self._compute_crowd_trends(current_occupancy, capacity)
        summary = self._compute_summary(gates, dispatches, alerts)

        return {
            "summary": summary,
            "crowdTrends": crowd_history,
            "gateMetrics": [
                {"name": g["name"], "waitTime": g["waitTimeMinutes"]}
                for g in gates
            ],
        }
