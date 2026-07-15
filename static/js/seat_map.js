// --- SEAT MAP VIEWER INTERACTIVE ENGINE ---

let seatData = {};
let sectionList = [];

async function initSeatMap() {
    try {
        const response = await fetch("/extended/api/seat-map/data");
        const data = await response.json();
        if (!response.ok) return;

        seatData = data.seats;
        sectionList = data.sections;

        // Render KPI details
        document.getElementById("seat-capacity").textContent = data.kpis.capacity.toLocaleString();
        document.getElementById("seat-booked").textContent = data.kpis.booked.toLocaleString();
        document.getElementById("seat-avail").textContent = data.kpis.available.toLocaleString();
        document.getElementById("seat-occupancy-pct").textContent = `${data.kpis.occupancy_pct}% Occupancy`;

        // Render select dropdown options
        const select = document.getElementById("section-select");
        if (select) {
            select.innerHTML = sectionList.map(s => `
                <option value="${s.id}">${s.name} (${s.total} seats)</option>
            `).join("");
            
            // Load first stand by default
            if (sectionList.length > 0) {
                loadStandGrid(sectionList[0].id);
            }
        }
    } catch (e) {
        console.error("Error loading seating metrics", e);
    }
}

function loadStandGrid(sectionId) {
    const canvas = document.getElementById("seating-canvas");
    const section = sectionList.find(s => s.id === sectionId);
    
    if (!canvas || !section || !seatData[sectionId]) return;

    // Apply grid template layout columns matching section specs
    canvas.style.gridTemplateColumns = `repeat(${section.seats_per_row}, minmax(15px, 1fr))`;
    
    canvas.innerHTML = seatData[sectionId].map(seat => {
        let typeClass = "seat-available";
        let label = "";
        
        if (seat.booked) typeClass = "seat-booked";
        else if (seat.vip) typeClass = "seat-vip";
        else if (seat.accessible) {
            typeClass = "seat-accessible";
            label = "♿";
        }

        return `
            <div class="seat-dot ${typeClass}" 
                 title="Seat ${seat.seat_no}" 
                 onclick="inspectSeat('${sectionId}', '${seat.seat_no}')">
                 ${label}
            </div>
        `;
    }).join("");
}

function inspectSeat(sectionId, seatNo) {
    const details = document.getElementById("seat-details-card");
    if (!details || !seatData[sectionId]) return;

    const seat = seatData[sectionId].find(s => s.seat_no === seatNo);
    if (!seat) return;

    const section = sectionList.find(s => s.id === sectionId);

    let statusText = seat.booked ? "<span style='color:var(--danger); font-weight:700;'>Booked</span>" : "<span style='color:var(--success); font-weight:700;'>Available</span>";
    let tierText = seat.vip ? "VIP Premium Lounge ($150)" : (seat.accessible ? "Accessible Companion Block ($30)" : "General Admission Stand ($45)");

    details.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:0.5rem; font-size:0.95rem;">
            <div>🎫 Seat Number: <strong>${seat.seat_no}</strong></div>
            <div>🏢 Stand: <strong>${section.name}</strong></div>
            <div>📶 Row Position: <strong>Row ${seat.row}</strong></div>
            <div>🟢 Status: <strong>${statusText}</strong></div>
            <div>💳 Ticket Tier: <strong>${tierText}</strong></div>
        </div>
    `;
}

document.addEventListener("DOMContentLoaded", initSeatMap);
