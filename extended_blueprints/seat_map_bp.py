from typing import Any, Dict, List
from flask import Blueprint, render_template, jsonify, session, Response
from app import require_auth

seat_map_bp = Blueprint("seat_map_bp", __name__)


def _generate_section_seats(sec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generates seat occupancy attributes and metadata lists for a specific section.

    Args:
        sec (Dict[str, Any]): Seating section configurations.

    Returns:
        List[Dict[str, Any]]: Array of individual seat maps.
    """
    sec_seats: List[Dict[str, Any]] = []
    is_vip: bool = sec["id"] == "sec-vip"
    is_accessible: bool = sec["id"] == "sec-d"

    for r in range(1, sec["rows"] + 1):
        for s in range(1, sec["seats_per_row"] + 1):
            # Deterministic pseudo-random booking pattern
            booked_hash = (r * 7 + s * 13) % 10
            booked = booked_hash < 8  # 80% occupancy

            sec_seats.append(
                {
                    "seat_no": f"{sec['id'].split('-')[1].upper()}-{r}-{s}",
                    "row": r,
                    "seat": s,
                    "booked": booked,
                    "vip": is_vip,
                    "accessible": is_accessible,
                }
            )
    return sec_seats


@seat_map_bp.route("/seat-map")
@require_auth
def seat_map_page() -> str:
    """Renders the stadium seating selection/view layout page.

    Returns:
        str: Rendered HTML template.
    """
    return render_template("seat_map.html", username=session.get("username"))


@seat_map_bp.route("/api/seat-map/data")
@require_auth
def seat_map_data() -> Response:
    """Generates stadium seating sections configuration dataset.

    Returns:
        Response: Flask JSON response with capacity and occupancy mapping.
    """
    # 6 sections representing major stadium blocks
    sections: List[Dict[str, Any]] = [
        {
            "id": "sec-a",
            "name": "North Stand A",
            "total": 100,
            "rows": 5,
            "seats_per_row": 20,
        },
        {
            "id": "sec-b",
            "name": "East Stand B",
            "total": 150,
            "rows": 6,
            "seats_per_row": 25,
        },
        {
            "id": "sec-vip",
            "name": "VIP Platinum",
            "total": 50,
            "rows": 5,
            "seats_per_row": 10,
        },
        {
            "id": "sec-d",
            "name": "South Stand D (Accessible)",
            "total": 80,
            "rows": 4,
            "seats_per_row": 20,
        },
        {
            "id": "sec-e",
            "name": "West Stand E",
            "total": 120,
            "rows": 6,
            "seats_per_row": 20,
        },
        {
            "id": "sec-f",
            "name": "Concourse Upper F",
            "total": 200,
            "rows": 8,
            "seats_per_row": 25,
        },
    ]

    seats_by_section: Dict[str, List[Dict[str, Any]]] = {}
    for sec in sections:
        seats_by_section[sec["id"]] = _generate_section_seats(sec)

    return jsonify(
        {
            "status": "success",
            "sections": sections,
            "seats": seats_by_section,
            "kpis": {
                "capacity": 70000,
                "booked": 56210,
                "available": 13790,
                "occupancy_pct": 80.3,
            },
        }
    )
