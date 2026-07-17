import random
from typing import Any, Dict, List
from firebase_helper import StadiumDB


class PredictionService:
    """Service class responsible for calculating predictive crowd levels.

    Attributes:
        db (StadiumDB): The database helper interface.
    """

    def __init__(self, db: StadiumDB) -> None:
        """Initializes PredictionService with database interface dependency.

        Args:
            db (StadiumDB): Stadium database client.
        """
        self.db: StadiumDB = db

    def _predict_zone_level(self, current_level: int, total_staff: int, duration_minutes: int) -> int:
        """Calculates predicted crowd level for a single zone based on duration and staff.

        Args:
            current_level (int): Active crowd level percent.
            total_staff (int): Dispatched safety units.
            duration_minutes (int): Predictive offset (5, 10, or 30).

        Returns:
            int: Predicted crowd level percent (5 to 99).
        """
        if duration_minutes == 5:
            drift = random.randint(-2, 3)
            reduction = total_staff * 4
        elif duration_minutes == 10:
            drift = random.randint(-3, 4)
            reduction = total_staff * 10
        else:
            drift = random.randint(-5, 5)
            reduction = total_staff * 25

        return max(5, min(99, int(current_level + drift - reduction)))

    def _get_status(self, level: int) -> str:
        """Translates crowd level percentage into qualitative status tags.

        Args:
            level (int): Crowd density percentage.

        Returns:
            str: Status description (Clear, Moderate, Congested).
        """
        if level < 50:
            return "Clear"
        elif level < 75:
            return "Moderate"
        return "Congested"

    def get_predictions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Calculates crowd density predictions for 5, 10, and 30 minutes.

        Returns:
            Dict[str, List[Dict[str, Any]]]: Predictive timelines mapped to lists of zone metrics.
        """
        state: Dict[str, Any] = self.db.get_simulation_state()
        if not state:
            return {}

        zones: List[Dict[str, Any]] = state.get("zones", [])
        dispatches: Dict[str, Any] = state.get("staff", {}).copy()

        predictions: Dict[str, List[Dict[str, Any]]] = {"5_min": [], "10_min": [], "30_min": []}

        for zone in zones:
            zone_id: str = zone["id"]
            current_level: int = zone["crowdLevel"]

            sec_deployed: int = len(
                [
                    d
                    for d in dispatches.get("security", {}).get("deployed", [])
                    if d.get("zone_id") == zone_id
                ]
            )
            med_deployed: int = len(
                [
                    d
                    for d in dispatches.get("medical", {}).get("deployed", [])
                    if d.get("zone_id") == zone_id
                ]
            )
            total_staff: int = sec_deployed + med_deployed

            for duration in [5, 10, 30]:
                pred: int = self._predict_zone_level(current_level, total_staff, duration)
                predictions[f"{duration}_min"].append(
                    {
                        "zone_id": zone_id,
                        "name": zone["name"],
                        "predictedLevel": pred,
                        "status": self._get_status(pred),
                    }
                )

        return predictions
