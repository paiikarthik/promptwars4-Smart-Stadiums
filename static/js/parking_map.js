// --- SMART PARKING MAP ROUTING ---

let parkingMapInstance = null;
let parkingMarkers = [];

const parkingLots = {
    "park-a": {"name": "Parking A (North Lot)", "lat": 12.9789, "lng": 77.5908, "slots": "80 free", "gate": [12.9782, 77.5912]},
    "park-b": {"name": "Parking B (South Lot)", "lat": 12.9768, "lng": 77.5929, "slots": "120 free", "gate": [12.9772, 77.5925]},
    "park-c": {"name": "Parking C (VIP Lot)", "lat": 12.9781, "lng": 77.5920, "slots": "10 free", "gate": [12.9782, 77.5912]}
};

function initParkingMap() {
    const canvas = document.getElementById("parking-map-canvas");
    if (!canvas) return;

    if (typeof google !== "undefined" && typeof google.maps !== "undefined") {
        try {
            parkingMapInstance = new google.maps.Map(canvas, {
                center: { lat: 12.9780, lng: 77.5918 },
                zoom: 17,
                mapTypeId: 'roadmap'
            });
            return;
        } catch (e) {
            console.warn("Google Parking Map failed, loading Leaflet fallback.", e);
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
            parkingMapInstance = L.map(canvas).setView([12.9780, 77.5918], 17);
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; OpenStreetMap'
            }).addTo(parkingMapInstance);

            // Add markers
            Object.keys(parkingLots).forEach(key => {
                const lot = parkingLots[key];
                const marker = L.marker([lot.lat, lot.lng]).addTo(parkingMapInstance);
                marker.bindTooltip(lot.name);
                parkingMarkers.push(marker);
            });
        } catch (err) {
            console.error("Leaflet parking fallback failed", err);
        }
    };
    document.head.appendChild(script);
}

function focusParkingLot(lotId) {
    const lot = parkingLots[lotId];
    if (!parkingMapInstance || !lot) return;

    // If Leaflet map
    if (typeof L !== "undefined" && parkingMapInstance instanceof L.Map) {
        // Center on lot
        parkingMapInstance.setView([lot.lat, lot.lng], 18);
        
        // Remove old routes
        parkingMapInstance.eachLayer(layer => {
            if (layer instanceof L.Polyline) {
                parkingMapInstance.removeLayer(layer);
            }
        });

        // Draw walking polyline to gate
        L.polyline([[lot.lat, lot.lng], lot.gate], {color: '#10b981', weight: 5, dashArray: '5, 10'}).addTo(parkingMapInstance);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    setTimeout(initParkingMap, 500);
});
