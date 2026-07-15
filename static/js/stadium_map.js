// --- INTERACTIVE STADIUM MAP EXPLORER ---

const facilitiesData = {
    gates: [
        {"id": "gate-north", "name": "Main North Gate", "lat": 12.9782, "lng": 77.5912, "occupancy": "High (82%)", "queue": "14 mins wait", "walking": "3 mins", "status": "Active"},
        {"id": "gate-south", "name": "South Entrance Gate", "lat": 12.9772, "lng": 77.5925, "occupancy": "Moderate (55%)", "queue": "8 mins wait", "walking": "5 mins", "status": "Active"},
        {"id": "gate-east", "name": "East Admission Gate", "lat": 12.9791, "lng": 77.5921, "occupancy": "Low (20%)", "queue": "2 mins wait", "walking": "8 mins", "status": "Active"}
    ],
    restrooms: [
        {"id": "rr-north", "name": "North Concourse Restrooms", "lat": 12.9785, "lng": 77.5915, "occupancy": "Moderate (60%)", "queue": "4 mins queue", "walking": "2 mins", "status": "Cleaned"},
        {"id": "rr-south", "name": "South Concourse Restrooms", "lat": 12.9775, "lng": 77.5922, "occupancy": "High (90%)", "queue": "9 mins queue", "walking": "4 mins", "status": "Busy"}
    ],
    food: [
        {"id": "food-court", "name": "Main Court Pizza & Drinks", "lat": 12.9780, "lng": 77.5918, "occupancy": "High (85%)", "queue": "12 mins wait", "walking": "3 mins", "status": "Open"},
        {"id": "food-snacks", "name": "South Stand Burger Stop", "lat": 12.9776, "lng": 77.5923, "occupancy": "Low (15%)", "queue": "1 min wait", "walking": "1 min", "status": "Open"}
    ],
    medical: [
        {"id": "med-first", "name": "North First Aid Base", "lat": 12.9784, "lng": 77.5913, "occupancy": "Low (5%)", "queue": "Immediate", "walking": "2 mins", "status": "Standby"}
    ],
    parking: [
        {"id": "park-a", "name": "Parking A (North Lot)", "lat": 12.9789, "lng": 77.5908, "occupancy": "High (80%)", "queue": "20 slots free", "walking": "3 mins", "status": "Open"},
        {"id": "park-b", "name": "Parking B (South Lot)", "lat": 12.9768, "lng": 77.5929, "occupancy": "Moderate (65%)", "queue": "120 slots free", "walking": "5 mins", "status": "Open"}
    ],
    atms: [
        {"id": "atm-vip", "name": "VIP Stand ATM (HDFC)", "lat": 12.9781, "lng": 77.5920, "occupancy": "Low (10%)", "queue": "No line", "walking": "1 min", "status": "Dispensing"}
    ]
};

let activeMarkers = [];
let mapInstance = null;

function initStadiumMap() {
    const canvas = document.getElementById("map-canvas");
    if (!canvas) return;

    // Check if Google Maps script loaded successfully
    if (typeof google !== "undefined" && typeof google.maps !== "undefined") {
        try {
            const mapOptions = {
                center: { lat: 12.9780, lng: 77.5918 },
                zoom: 17,
                mapTypeId: 'roadmap',
                styles: [
                    { elementType: "geometry", stylers: [{ color: "#242f3e" }] },
                    { elementType: "labels.text.stroke", stylers: [{ color: "#242f3e" }] },
                    { elementType: "labels.text.fill", stylers: [{ color: "#746855" }] }
                ]
            };
            mapInstance = new google.maps.Map(canvas, mapOptions);
            
            // Render all pins
            renderGoogleMarkers("all");
            return;
        } catch (e) {
            console.warn("Google Maps init failed, loading Leaflet fallback.", e);
        }
    }

    // Leaflet Dynamic fallback loader
    loadLeafletMapFallback(canvas);
}

function loadLeafletMapFallback(canvas) {
    // Inject Leaflet CSS
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
    document.head.appendChild(link);

    // Inject Leaflet Script
    const script = document.createElement("script");
    script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    script.onload = () => {
        try {
            // Leaflet map center
            mapInstance = L.map(canvas).setView([12.9780, 77.5918], 17);
            
            // Dark map tiles matching glassmorphism dark theme
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; OpenStreetMap'
            }).addTo(mapInstance);

            renderLeafletMarkers("all");
        } catch (err) {
            console.error("Leaflet fallback failed", err);
            canvas.innerHTML = `<p style="padding:4rem; text-align:center; opacity:0.6;">Local fallback map rendering failed.</p>`;
        }
    };
    document.head.appendChild(script);
}

function renderGoogleMarkers(category) {
    // Clear old markers
    activeMarkers.forEach(m => m.setMap(null));
    activeMarkers = [];

    const categories = category === "all" ? Object.keys(facilitiesData) : [category];
    
    categories.forEach(cat => {
        if (!facilitiesData[cat]) return;
        facilitiesData[cat].forEach(f => {
            const marker = new google.maps.Marker({
                position: { lat: f.lat, lng: f.lng },
                map: mapInstance,
                title: f.name
            });
            
            marker.addListener("click", () => {
                displayFacilityDetails(f);
            });
            
            activeMarkers.push(marker);
        });
    });
}

function renderLeafletMarkers(category) {
    // Clear old markers
    activeMarkers.forEach(m => mapInstance.removeLayer(m));
    activeMarkers = [];

    const categories = category === "all" ? Object.keys(facilitiesData) : [category];

    categories.forEach(cat => {
        if (!facilitiesData[cat]) return;
        facilitiesData[cat].forEach(f => {
            const marker = L.marker([f.lat, f.lng]).addTo(mapInstance);
            marker.bindTooltip(f.name);
            
            marker.on("click", () => {
                displayFacilityDetails(f);
            });
            
            activeMarkers.push(marker);
        });
    });
}

function displayFacilityDetails(facility) {
    const details = document.getElementById("facility-details-card");
    if (!details) return;

    details.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:0.35rem; font-size:0.92rem;">
            <h4 style="font-weight:700; color:var(--primary); font-size: 1.05rem;">📍 ${facility.name}</h4>
            <div style="margin-top:0.25rem;">📊 Occupancy density: <strong>${facility.occupancy}</strong></div>
            <div>⏱️ Wait queue length: <strong>${facility.queue}</strong></div>
            <div>🚶 Walking time: <strong>${facility.walking} away</strong></div>
            <div>🟢 Status indicator: <strong style="color:var(--success);">${facility.status}</strong></div>
        </div>
    `;
}

function filterMapMarkers(category) {
    if (!mapInstance) return;
    
    // Check if map is Google or Leaflet
    if (typeof google !== "undefined" && typeof google.maps !== "undefined" && mapInstance instanceof google.maps.Map) {
        renderGoogleMarkers(category);
    } else {
        renderLeafletMarkers(category);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // Wait slightly to ensure styles are parsed
    setTimeout(initStadiumMap, 500);
});
