import random
import time

class AnalyticsService:
    def __init__(self, db):
        self.db = db

    def get_analytics(self):
        """Compiles analytics metrics using a mixture of active DB logs 
        (alerts, dispatches) and realistic historical series simulation.
        """
        state = self.db.get_simulation_state()
        alerts = self.db.get_alerts()
        dispatches = self.db.get_dispatches()

        # Count dispatches
        security_dispatches = len([d for d in dispatches if d.get("staff_type") == "security"])
        medical_dispatches = len([d for d in dispatches if d.get("staff_type") == "medical"])
        total_dispatches = len(dispatches)

        # Count alerts
        manual_alerts = len([a for a in alerts if not a.get("auto")])
        auto_alerts = len([a for a in alerts if a.get("auto")])
        total_alerts = len(alerts)

        # Simulate 2 hours of historical crowd trends (12 data points in 10-min intervals)
        current_occupancy = state.get("occupancy", 52000)
        capacity = state.get("capacity", 70000)
        
        crowd_history = []
        base_occupancy = current_occupancy - 12000
        for i in range(12):
            # Progression of crowd filling the stadium
            factor = (i + 1) / 12
            occupancy_val = int(base_occupancy + (current_occupancy - base_occupancy) * factor + random.randint(-1000, 1000))
            occupancy_val = max(1000, min(capacity, occupancy_val))
            crowd_history.append({
                "time": f"{(i*10)} mins ago" if i > 0 else "Just Now",
                "occupancy": occupancy_val
            })
            
        # Reverse to show chronological order
        crowd_history.reverse()

        # Calculate peak and average wait times from active gates
        gates = state.get("gates", [])
        gate_times = [g["waitTimeMinutes"] for g in gates] if gates else [5, 10, 15]
        peak_wait = max(gate_times)
        avg_wait = sum(gate_times) / len(gate_times)

        # Compute AI usage and fan ratings statistics (simulated counts based on system load)
        ai_chat_queries = 24 + len(dispatches) * 3 + random.randint(1, 10)
        fan_page_views = 152 + len(dispatches) * 12 + random.randint(5, 30)

        return {
            "summary": {
                "peakWaitTime": peak_wait,
                "avgWaitTime": round(avg_wait, 1),
                "totalDispatches": total_dispatches,
                "securityDispatches": security_dispatches,
                "medicalDispatches": medical_dispatches,
                "totalAlerts": total_alerts,
                "manualAlerts": manual_alerts,
                "autoAlerts": auto_alerts,
                "aiChatQueries": ai_chat_queries,
                "fanActivity": fan_page_views
            },
            "crowdTrends": crowd_history,
            "gateMetrics": [
                {"name": g["name"], "waitTime": g["waitTimeMinutes"]} for g in gates
            ]
        }
