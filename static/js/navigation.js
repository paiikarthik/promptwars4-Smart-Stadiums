// --- ASSISTIVE DIRECTIONS FINDING NAVIGATION ---

let directionsMap = null;

function initNavigationMap() {
    const canvas = document.getElementById("navigation-canvas");
    if (!canvas) return;

    if (typeof google !== "undefined" && typeof google.maps !== "undefined") {
        try {
            directionsMap = new google.maps.Map(canvas, {
                center: { lat: 12.9780, lng: 77.5918 },
                zoom: 17,
                mapTypeId: 'roadmap'
            });
            return;
        } catch (e) {
            console.warn("Directions Map failed, loading Leaflet fallback.", e);
        }
    }

    // Leaflet fallback
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
    document.head.appendChild(link);

    const script = document.createElement("script");
    script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    script.onload = () => {
        try {
            directionsMap = L.map(canvas).setView([12.9780, 77.5918], 17);
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; OpenStreetMap'
            }).addTo(directionsMap);
        } catch (err) {
            console.error("Leaflet nav fallback failed", err);
        }
    };
    document.head.appendChild(script);
}

function escapeHTML(str) {
    if (!str) return "";
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

function calculateDirections(event) {
    event.preventDefault();
    const startValRaw = document.getElementById("nav-start").value.trim();
    const startVal = escapeHTML(startValRaw);
    const endSelect = document.getElementById("nav-end");
    const endText = escapeHTML(endSelect.options[endSelect.selectedIndex].text);
    const endVal = endSelect.value;

    const stepsContainer = document.getElementById("navigation-steps");
    if (!stepsContainer) return;

    stepsContainer.innerHTML = `<li class="info-item">Plotting navigation route...</li>`;

    // Mock directions steps fallback (works immediately without credential blocks)
    setTimeout(() => {
        const directions = {
            "restroom-north": [
                `Exit your seat row at Block ${startVal.split(' ')[1] || 'current Stand'}.`,
                "Turn right and head towards the North Concourse corridor.",
                "Pass the Pizza Stand on your left.",
                "Restrooms are located directly opposite Block A (approx 45m walk)."
            ],
            "restroom-south": [
                `Exit your seat row at Block ${startVal.split(' ')[1] || 'current Stand'}.`,
                "Walk down the steps to the lower South concourse aisle.",
                "Follow signs for Restrooms past medical stand B.",
                "Restrooms are on your right next to the Burger Shop (approx 80m walk)."
            ],
            "medical-nc": [
                `Exit your seat row at Block ${startVal.split(' ')[1] || 'current Stand'}.`,
                "Proceed to the North Concourse exit lobby.",
                "The First Aid medical center is situated next to Entrance Gate North."
            ],
            "food-court": [
                "Walk towards the central food stand concourse corridor.",
                "Main Pizza Stand and Beverage bar are located between Stands A and B."
            ],
            "exit-west": [
                "Locate the exit routing signs in your stand row.",
                "Proceed down the West exit ramps.",
                "Gate West is active and clear. Proceed through the ticket scan gate."
            ],
            "exit-north": [
                "Follow main overhead green exit indicators.",
                "Take the elevator or stairs to ground level.",
                "Walk past Parking Lot A to Gate North main egress exit."
            ]
        };

        const steps = directions[endVal] || [
            "Exit your seating row.",
            `Head towards the nearest concourse signs for ${endText}.`,
            "Ask nearby staff members if you experience navigation difficulties."
        ];

        stepsContainer.innerHTML = steps.map((step, idx) => `
            <li class="info-item" style="display:flex; gap:0.75rem; align-items:flex-start;">
                <span style="background:var(--primary); color:white; font-size:0.75rem; padding:0.15rem 0.4rem; border-radius:50%; font-weight:700;">${idx + 1}</span>
                <span style="font-size:0.88rem; line-height:1.4;">${step}</span>
            </li>
        `).join("");
        
        // Draw mock path on Leaflet map if map exists
        if (directionsMap && typeof L !== "undefined" && directionsMap instanceof L.Map) {
            // Draw a line across the stadium representation
            const startLatLong = [12.9780 + (Math.random() * 0.001 - 0.0005), 77.5918 + (Math.random() * 0.001 - 0.0005)];
            const endLatLong = [12.9780, 77.5918];
            
            // Clear old lines
            directionsMap.eachLayer(layer => {
                if (layer instanceof L.Polyline) {
                    directionsMap.removeLayer(layer);
                }
            });

            const polyline = L.polyline([startLatLong, endLatLong], {color: '#6366f1', weight: 5}).addTo(directionsMap);
            directionsMap.fitBounds(polyline.getBounds());
        }
    }, 800);
}

document.addEventListener("DOMContentLoaded", () => {
    setTimeout(initNavigationMap, 500);
});
