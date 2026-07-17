import random


class PredictionService:
    def __init__(self, db):
        self.db = db

    def get_predictions(self):
        """Calculates crowd density predictions for 5, 10, and 30 minutes.
        Does not modify the active telemetry state.
        """
        state = self.db.get_simulation_state()
        if not state:
            return {}

        zones = state.get("zones", [])
        dispatches = state.get("staff", {}).copy()

        predictions = {"5_min": [], "10_min": [], "30_min": []}

        # Calculate predictions for each zone
        for zone in zones:
            zone_id = zone["id"]
            current_level = zone["crowdLevel"]

            # Check if staff is deployed to this zone
            sec_deployed = len(
                [
                    d
                    for d in dispatches.get("security", {}).get("deployed", [])
                    if d.get("zone_id") == zone_id
                ]
            )
            med_deployed = len(
                [
                    d
                    for d in dispatches.get("medical", {}).get("deployed", [])
                    if d.get("zone_id") == zone_id
                ]
            )
            total_staff = sec_deployed + med_deployed

            # Prediction factors:
            # - If no staff, crowd tends to drift slightly higher or stay high if busy
            # - If staff deployed, crowd level is predicted to decline over time

            # 5 Minute Prediction
            drift_5 = random.randint(-2, 3)
            reduction_5 = total_staff * 4  # 4% reduction per staff in 5 min
            pred_5 = max(
                5, min(99, int(current_level + drift_5 - reduction_5))
            )

            # 10 Minute Prediction
            drift_10 = random.randint(-3, 4)
            reduction_10 = total_staff * 10  # 10% reduction in 10 min
            pred_10 = max(
                5, min(99, int(current_level + drift_10 - reduction_10))
            )

            # 30 Minute Prediction
            drift_30 = random.randint(-5, 5)
            reduction_30 = (
                total_staff * 25
            )  # 25% reduction in 30 min (fully resolved)
            pred_30 = max(
                5, min(99, int(current_level + drift_30 - reduction_30))
            )

            predictions["5_min"].append(
                {
                    "zone_id": zone_id,
                    "name": zone["name"],
                    "predictedLevel": pred_5,
                    "status": self._get_status(pred_5),
                }
            )

            predictions["10_min"].append(
                {
                    "zone_id": zone_id,
                    "name": zone["name"],
                    "predictedLevel": pred_10,
                    "status": self._get_status(pred_10),
                }
            )

            predictions["30_min"].append(
                {
                    "zone_id": zone_id,
                    "name": zone["name"],
                    "predictedLevel": pred_30,
                    "status": self._get_status(pred_30),
                }
            )

        return predictions

    def _get_status(self, level):
        if level < 50:
            return "Clear"
        if level < 80:
            return "Moderate"
        return "Congested"
