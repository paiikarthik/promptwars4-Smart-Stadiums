from flask import Blueprint, render_template, jsonify, session
from app import require_auth

seat_map_bp = Blueprint("seat_map_bp", __name__)

@seat_map_bp.route("/seat-map")
@require_auth
def seat_map_page():
    return render_template("seat_map.html", username=session.get("username"))

@seat_map_bp.route("/api/seat-map/data")
@require_auth
def seat_map_data():
    """Generates stadium seating sections configuration including:
    - VIP seats
    - Accessible (wheelchair) seats
    - Booked & Available seats
    """
    # 6 sections representing major stadium blocks
    sections = [
        {"id": "sec-a", "name": "North Stand A", "total": 100, "rows": 5, "seats_per_row": 20},
        {"id": "sec-b", "name": "East Stand B", "total": 150, "rows": 6, "seats_per_row": 25},
        {"id": "sec-vip", "name": "VIP Platinum", "total": 50, "rows": 5, "seats_per_row": 10},
        {"id": "sec-d", "name": "South Stand D (Accessible)", "total": 80, "rows": 4, "seats_per_row": 20},
        {"id": "sec-e", "name": "West Stand E", "total": 120, "rows": 6, "seats_per_row": 20},
        {"id": "sec-f", "name": "Concourse Upper F", "total": 200, "rows": 8, "seats_per_row": 25}
    ]
    
    # Generate seat list for each section with booked / VIP / accessible attributes
    seats_by_section = {}
    for sec in sections:
        sec_seats = []
        is_vip = sec["id"] == "sec-vip"
        is_accessible = sec["id"] == "sec-d"
        
        for r in range(1, sec["rows"] + 1):
            for s in range(1, sec["seats_per_row"] + 1):
                # Deterministic pseudo-random booking pattern
                booked_hash = (r * 7 + s * 13) % 10
                booked = booked_hash < 8 # 80% occupancy
                
                sec_seats.append({
                    "seat_no": f"{sec['id'].split('-')[1].upper()}-{r}-{s}",
                    "row": r,
                    "seat": s,
                    "booked": booked,
                    "vip": is_vip,
                    "accessible": is_accessible
                })
        seats_by_section[sec["id"]] = sec_seats

    return jsonify({
        "status": "success",
        "sections": sections,
        "seats": seats_by_section,
        "kpis": {
            "capacity": 70000,
            "booked": 56210,
            "available": 13790,
            "occupancy_pct": 80.3
        }
    })
