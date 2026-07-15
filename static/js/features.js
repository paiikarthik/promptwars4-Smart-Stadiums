// --- FLOATING SOS BUTTON AND SYSTEM CONTROLLER ---

function toggleSOSModal(show) {
    const modal = document.getElementById("sos-modal");
    if (modal) {
        modal.style.display = show ? "flex" : "none";
    }
}

async function handleSOSSubmit(event) {
    event.preventDefault();
    const seatInput = document.getElementById("sos-seat");
    const zoneSelect = document.getElementById("sos-zone");
    
    if (!seatInput || !zoneSelect) return;

    const payload = {
        seat: seatInput.value,
        zone_id: zoneSelect.value
    };

    try {
        const response = await fetch("/api/sos/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        
        if (response.ok) {
            toggleSOSModal(false);
            seatInput.value = "";
            alert("🚨 EMERGENCY SOS BROADCASTED! Medical/Security staff have been notified and dispatched to your seat.");
        } else {
            alert(data.message || "Failed to trigger SOS.");
        }
    } catch (e) {
        alert("SOS connection failed. Please seek nearest staff member.");
    }
}

// --- ADMIN SOS MANAGER ---

async function loadAdminSOSList() {
    const container = document.getElementById("admin-sos-list");
    if (!container) return;

    try {
        const response = await fetch("/api/sos/list");
        const data = await response.json();
        if (!response.ok) return;

        if (data.alerts.length === 0) {
            container.innerHTML = `<li class="info-item" style="color:var(--text-muted);">No active emergency dispatches.</li>`;
            return;
        }

        container.innerHTML = data.alerts.map(s => {
            let statusStyle = "color: var(--danger); font-weight:700;";
            if (s.status === "Accepted") statusStyle = "color: var(--warning); font-weight:700;";
            if (s.status === "Resolved") statusStyle = "color: var(--success); font-weight:700;";

            let buttonsHtml = "";
            if (s.status === "Pending") {
                buttonsHtml = `
                    <button class="btn-dispatch security" onclick="updateSOSStatus('${s.id}', 'Accepted')">Accept</button>
                    <button class="btn-dispatch medical" onclick="updateSOSStatus('${s.id}', 'Resolved')">Resolve</button>
                `;
            } else if (s.status === "Accepted") {
                buttonsHtml = `
                    <button class="btn-dispatch medical" onclick="updateSOSStatus('${s.id}', 'Resolved')">Resolve</button>
                `;
            }

            return `
                <li class="info-item" style="flex-wrap: wrap; gap: 0.5rem;">
                    <div style="flex: 1; min-width: 150px;">
                        <div>⚠️ Emergency: <strong>Seat ${s.seat}</strong> in <strong>Zone ${s.zone_id}</strong></div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.15rem;">
                            Triggered: ${timeAgo(s.timestamp)} ago
                        </div>
                    </div>
                    <div style="display:flex; align-items:center; gap: 1rem;">
                        <span style="${statusStyle}">${s.status}</span>
                        <div class="staff-actions">
                            ${buttonsHtml}
                        </div>
                    </div>
                </li>
            `;
        }).join("");
    } catch (e) {
        console.error("SOS list error", e);
    }
}

async function updateSOSStatus(sosId, status) {
    try {
        const response = await fetch("/api/sos/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: sosId, status: status })
        });
        if (response.ok) {
            loadAdminSOSList();
        }
    } catch (e) {
        console.error("SOS update error", e);
    }
}

// Helper: time ago text formatting
function timeAgo(timestamp) {
    const diff = Math.floor(time.time() - timestamp);
    if (diff < 60) return `${diff}s`;
    return `${Math.floor(diff/60)}m`;
}

// --- FAN FEEDBACK RATING CONTROLLER ---

let currentFeedbackRatings = {
    navigation: 5,
    food: 5,
    restrooms: 5,
    security: 5,
    ai_assistant: 5
};

function selectStarRating(category, rating) {
    currentFeedbackRatings[category] = rating;
    
    // Update star visual highlights
    for (let i = 1; i <= 5; i++) {
        const star = document.getElementById(`star-${category}-${i}`);
        if (star) {
            if (i <= rating) {
                star.style.color = "var(--warning)";
                star.textContent = "★";
            } else {
                star.style.color = "var(--text-muted)";
                star.textContent = "☆";
            }
        }
    }
}

async function handleFeedbackSubmit(event) {
    event.preventDefault();
    const commentInput = document.getElementById("feedback-comments");
    if (!commentInput) return;

    const payload = {
        scores: currentFeedbackRatings,
        comments: commentInput.value
    };

    try {
        const response = await fetch("/api/feedback/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            commentInput.value = "";
            alert("Thank you for your feedback! It helps improve ArenaFlow operations.");
            loadFeedbackSummary();
        } else {
            alert("Failed to submit feedback.");
        }
    } catch (e) {
        alert("Error sending feedback.");
    }
}

async function loadFeedbackSummary() {
    const summaryContainer = document.getElementById("feedback-summary-container");
    if (!summaryContainer) return;

    summaryContainer.innerHTML = `<p style="opacity: 0.6;">Generating Operations Analyst summary...</p>`;

    try {
        const response = await fetch("/api/feedback/summary");
        const data = await response.json();
        if (response.ok) {
            // Replace markdown
            let formatted = data.summary
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*\s(.*?)\n/g, '<li>$1</li>')
                .replace(/\n\n/g, '<p></p>');
            if (formatted.includes('<li>')) {
                formatted = formatted.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
            }
            summaryContainer.innerHTML = formatted;
        } else {
            summaryContainer.innerHTML = `<p>Feedback metrics summary unavailable.</p>`;
        }
    } catch (e) {
        summaryContainer.innerHTML = `<p>Error loading analytics summary.</p>`;
    }
}

// --- LOST & FOUND REGISTRY ---

async function handleLostFoundSubmit(event) {
    event.preventDefault();
    const typeSelect = document.getElementById("lf-type");
    const descInput = document.getElementById("lf-desc");
    const locInput = document.getElementById("lf-loc");
    const contactInput = document.getElementById("lf-contact");

    if (!typeSelect || !descInput || !locInput || !contactInput) return;

    const payload = {
        item_type: typeSelect.value,
        description: descInput.value,
        location: locInput.value,
        contact: contactInput.value
    };

    try {
        const response = await fetch("/api/lost-found/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            descInput.value = "";
            locInput.value = "";
            contactInput.value = "";
            alert("Claim submitted successfully!");
            loadLostFoundList();
        } else {
            alert("Submission failed.");
        }
    } catch (e) {
        alert("Lost & Found database unavailable.");
    }
}

async function loadLostFoundList(searchQuery = "") {
    const container = document.getElementById("lost-found-results");
    if (!container) return;

    container.innerHTML = `<li class="info-item">Searching registry...</li>`;

    try {
        const response = await fetch(`/api/lost-found/search?q=${encodeURIComponent(searchQuery)}`);
        const data = await response.json();
        if (!response.ok) return;

        const items = data.items;
        if (items.length === 0) {
            container.innerHTML = `<li class="info-item" style="color:var(--text-muted);">No matching claims found.</li>`;
            return;
        }

        const isAdmin = document.getElementById("is-admin-view")?.value === "true";

        container.innerHTML = items.map(item => {
            let statusStyle = "color: var(--danger); font-weight:700;";
            if (item.status === "Claimed") statusStyle = "color: var(--success); font-weight:700;";

            let btnHtml = "";
            if (isAdmin && item.status === "Found") {
                btnHtml = `<button class="btn-dispatch security" onclick="claimLostFoundItem('${item.id}')">Mark Claimed</button>`;
            }

            return `
                <li class="info-item" style="flex-wrap: wrap; gap: 0.5rem; justify-content: space-between;">
                    <div style="flex: 1; min-width: 200px;">
                        <h4 style="font-weight: 700; font-size: 1rem;">📦 ${item.item_type}</h4>
                        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.15rem;">
                            ${item.description}
                        </p>
                        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
                            📍 Lost near: ${item.location} | Contact: ${item.contact}
                        </div>
                    </div>
                    <div style="display:flex; align-items:center; gap: 1rem;">
                        <span style="${statusStyle}">${item.status}</span>
                        ${btnHtml}
                    </div>
                </li>
            `;
        }).join("");
    } catch (e) {
        container.innerHTML = `<li class="info-item">Registry search failed.</li>`;
    }
}

async function claimLostFoundItem(itemId) {
    try {
        const response = await fetch("/api/lost-found/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: itemId, status: "Claimed" })
        });
        if (response.ok) {
            loadLostFoundList();
        }
    } catch (e) {
        console.error("Lost & Found status update failed", e);
    }
}

function handleRegistrySearch() {
    const input = document.getElementById("lf-search");
    if (input) {
        loadLostFoundList(input.value);
    }
}

// --- WEATHER ADVISORY WIDGET ---

async function loadWeatherWidget() {
    const tempEl = document.getElementById("weather-temp");
    const rainEl = document.getElementById("weather-rain");
    const windEl = document.getElementById("weather-wind");
    const advisoryEl = document.getElementById("weather-advisory");

    if (!tempEl) return;

    try {
        const response = await fetch("/api/weather");
        const data = await response.json();
        if (response.ok) {
            const w = data.weather;
            tempEl.textContent = `${w.temperature}°C`;
            rainEl.textContent = `🌧️ Rain: ${w.rain_chance}%`;
            windEl.textContent = `💨 Wind: ${w.wind_speed_kph} kph`;
            advisoryEl.textContent = w.advisory;
        }
    } catch (e) {
        console.error("Weather load failed", e);
    }
}
