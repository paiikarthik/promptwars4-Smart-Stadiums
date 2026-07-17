// Global fetch interceptor to automatically inject CSRF tokens for mutating requests
(function() {
    const originalFetch = window.fetch;
    window.fetch = async function(resource, options = {}) {
        const method = (options.method || 'GET').toUpperCase();
        if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            if (csrfToken) {
                options.headers = options.headers || {};
                if (options.headers instanceof Headers) {
                    options.headers.set('X-CSRFToken', csrfToken);
                } else if (Array.isArray(options.headers)) {
                    const hasCsrf = options.headers.some(([k]) => k.toLowerCase() === 'x-csrf-token');
                    if (!hasCsrf) {
                        options.headers.push(['X-CSRFToken', csrfToken]);
                    }
                } else {
                    options.headers['X-CSRFToken'] = csrfToken;
                }
            }
        }
        return originalFetch(resource, options);
    };
})();

// --- SYSTEM GATEWAY: SIGN IN & REGISTER TOGGLES ---

function showForm(mode) {
    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");
    const loginBtn = document.getElementById("btn-show-login");
    const registerBtn = document.getElementById("btn-show-register");
    const errDiv = document.getElementById("form-error");
    const succDiv = document.getElementById("form-success");

    // Hide error/success banners
    if (errDiv) errDiv.style.display = "none";
    if (succDiv) succDiv.style.display = "none";

    if (mode === "login") {
        loginForm.style.display = "block";
        registerForm.style.display = "none";
        loginBtn.classList.add("active");
        registerBtn.classList.remove("active");
    } else {
        loginForm.style.display = "none";
        registerForm.style.display = "block";
        loginBtn.classList.remove("active");
        registerBtn.classList.add("active");
    }
}

// --- AUTHENTICATION ACTIONS ---

async function handleAuth(event, mode) {
    event.preventDefault();
    const errDiv = document.getElementById("form-error");
    const succDiv = document.getElementById("form-success");

    errDiv.style.display = "none";
    succDiv.style.display = "none";

    let payload = {};
    let url = "";

    if (mode === "login") {
        payload = {
            username: document.getElementById("login-username").value,
            password: document.getElementById("login-password").value
        };
        url = "/api/auth/login";
    } else {
        const radios = document.getElementsByName("role");
        let selectedRole = "attendee";
        for (let r of radios) {
            if (r.checked) {
                selectedRole = r.value;
                break;
            }
        }
        payload = {
            username: document.getElementById("reg-username").value,
            password: document.getElementById("reg-password").value,
            role: selectedRole
        };
        url = "/api/auth/register";
    }

    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            if (mode === "login") {
                succDiv.textContent = "Access granted! Redirecting...";
                succDiv.style.display = "block";
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 800);
            } else {
                succDiv.textContent = "Registration successful! You can now Sign In.";
                succDiv.style.display = "block";
                showForm("login");
                // Pre-fill registered username
                document.getElementById("login-username").value = payload.username;
            }
        } else {
            errDiv.textContent = data.message || "An error occurred. Please try again.";
            errDiv.style.display = "block";
        }
    } catch (e) {
        errDiv.textContent = "Server connection lost. Check backend logs.";
        errDiv.style.display = "block";
    }
}

async function handleLogout() {
    try {
        const response = await fetch("/api/auth/logout", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        });
        if (response.ok) {
            const data = await response.json();
            window.location.href = data.redirect || "/";
        } else {
            window.location.href = "/";
        }
    } catch (e) {
        console.error("Logout failed", e);
        window.location.href = "/";
    }
}

// --- TELEMETRY COLOR BADGES HELPER ---

function getWaitBadgeClass(minutes) {
    if (minutes < 10) return "badge-clear";
    if (minutes < 20) return "badge-warning";
    return "badge-danger";
}

function getCrowdBadgeClass(percentage) {
    if (percentage < 50) return "badge-clear";
    if (percentage < 80) return "badge-warning";
    return "badge-danger";
}

// --- ATTENDEE REAL-TIME DATA STREAM ---

function initDashboardStream() {
    console.log("[SSE] Initializing real-time dashboard stream...");
    const eventSource = new EventSource("/api/stream");

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        const telemetry = data.telemetry;
        const alerts = data.alerts;

        if (!telemetry) return;

        // 1. Update overall capacity KPIs
        document.getElementById("kpi-occupancy").textContent = telemetry.occupancy.toLocaleString();
        document.getElementById("kpi-capacity-total").textContent = `Capacity: ${telemetry.capacity.toLocaleString()}`;

        // 2. Identify and update Fastest Gate
        let fastestGate = null;
        if (telemetry.gates && telemetry.gates.length > 0) {
            telemetry.gates.forEach(gate => {
                if (!fastestGate || gate.waitTimeMinutes < fastestGate.waitTimeMinutes) {
                    fastestGate = gate;
                }
            });
            document.getElementById("kpi-fastest-gate").textContent = fastestGate.name;
            document.getElementById("kpi-fastest-gate-time").textContent = `Wait time: ${fastestGate.waitTimeMinutes} mins`;
            document.getElementById("action-gate").textContent = `${fastestGate.name} (${fastestGate.waitTimeMinutes}m)`;
        }

        // 3. Identify and update Congested Concourse
        let congestedZone = null;
        if (telemetry.zones && telemetry.zones.length > 0) {
            telemetry.zones.forEach(zone => {
                if (!congestedZone || zone.crowdLevel > congestedZone.crowdLevel) {
                    congestedZone = zone;
                }
            });
            document.getElementById("kpi-congested-zone").textContent = congestedZone.name;
            document.getElementById("kpi-congested-level").textContent = `Density: ${congestedZone.crowdLevel}%`;
        }

        // 4. Update Smart Pathfinder Washroom/Food short values
        if (telemetry.amenities) {
            const restrooms = telemetry.amenities.filter(a => a.type === "restroom");
            const foodStands = telemetry.amenities.filter(a => a.type === "food");

            if (restrooms.length > 0) {
                const fastestRest = restrooms.reduce((prev, curr) => prev.waitTimeMinutes < curr.waitTimeMinutes ? prev : curr);
                document.getElementById("action-restroom").textContent = `${fastestRest.name} (${fastestRest.waitTimeMinutes}m)`;
            }
            if (foodStands.length > 0) {
                const fastestFood = foodStands.reduce((prev, curr) => prev.waitTimeMinutes < curr.waitTimeMinutes ? prev : curr);
                document.getElementById("action-food").textContent = `${fastestFood.name} (${fastestFood.waitTimeMinutes}m)`;
            }
        }

        // 5. Render Gates list
        const gateList = document.getElementById("list-gates");
        if (gateList && telemetry.gates) {
            gateList.innerHTML = telemetry.gates.map(gate => `
                <li class="info-item">
                    <span class="item-name">${gate.name}</span>
                    <span class="item-value ${getWaitBadgeClass(gate.waitTimeMinutes)}">${gate.waitTimeMinutes} mins</span>
                </li>
            `).join("");
        }

        // 6. Render Concourse Zones list
        const zoneList = document.getElementById("list-zones");
        if (zoneList && telemetry.zones) {
            zoneList.innerHTML = telemetry.zones.map(zone => `
                <li class="info-item">
                    <span class="item-name">${zone.name}</span>
                    <span class="item-value ${getCrowdBadgeClass(zone.crowdLevel)}">${zone.crowdLevel}% full</span>
                </li>
            `).join("");
        }

        // 7. Render Restrooms and Food lists
        const restroomList = document.getElementById("list-restrooms");
        const foodList = document.getElementById("list-food");
        if (telemetry.amenities) {
            if (restroomList) {
                const restrooms = telemetry.amenities.filter(a => a.type === "restroom");
                restroomList.innerHTML = restrooms.map(r => `
                    <li class="info-item">
                        <span class="item-name">${r.name}</span>
                        <span class="item-value ${getWaitBadgeClass(r.waitTimeMinutes)}">${r.waitTimeMinutes} mins</span>
                    </li>
                `).join("");
            }
            if (foodList) {
                const foodStands = telemetry.amenities.filter(a => a.type === "food");
                foodList.innerHTML = foodStands.map(f => `
                    <li class="info-item">
                        <span class="item-name">${f.name}</span>
                        <span class="item-value ${getWaitBadgeClass(f.waitTimeMinutes)}">${f.waitTimeMinutes} mins</span>
                    </li>
                `).join("");
            }
        }

        // 8. Handle Notification Broadcast banner
        const alertBanner = document.getElementById("live-alert");
        if (alertBanner) {
            if (alerts && alerts.length > 0) {
                const latestAlert = alerts[0]; // Newest alert
                document.getElementById("alert-message").textContent = latestAlert.message;
                
                // Set alert title & color theme
                const alertTitle = document.getElementById("alert-title");
                const alertIcon = document.getElementById("alert-icon");
                alertTitle.textContent = latestAlert.auto ? "🤖 Automatic Safety Warning" : "📢 Command Center Broadcast";
                
                // Format banner style matching type
                alertBanner.className = "notification-banner"; // reset
                if (latestAlert.type === "danger") {
                    alertBanner.style.borderLeftColor = "var(--danger)";
                    alertBanner.style.background = "linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(13, 15, 26, 0.9) 100%)";
                    alertBanner.style.borderColor = "rgba(239, 68, 68, 0.4)";
                    alertIcon.textContent = "🚨";
                } else if (latestAlert.type === "warning") {
                    alertBanner.style.borderLeftColor = "var(--warning)";
                    alertBanner.style.background = "linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(13, 15, 26, 0.9) 100%)";
                    alertBanner.style.borderColor = "rgba(245, 158, 11, 0.4)";
                    alertIcon.textContent = "⚠️";
                } else if (latestAlert.type === "success") {
                    alertBanner.style.borderLeftColor = "var(--success)";
                    alertBanner.style.background = "linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(13, 15, 26, 0.9) 100%)";
                    alertBanner.style.borderColor = "rgba(16, 185, 129, 0.4)";
                    alertIcon.textContent = "✅";
                } else {
                    alertBanner.style.borderLeftColor = "var(--info)";
                    alertBanner.style.background = "linear-gradient(135deg, rgba(14, 165, 233, 0.15) 0%, rgba(13, 15, 26, 0.9) 100%)";
                    alertBanner.style.borderColor = "rgba(14, 165, 233, 0.4)";
                    alertIcon.textContent = "📢";
                }
                
                alertBanner.style.display = "flex";
            } else {
                alertBanner.style.display = "none";
            }
        }
    };

    eventSource.onerror = function() {
        console.warn("[SSE] Connection interrupted. Re-connecting...");
    };
}

// --- ADMIN COMMAND CENTER DATA STREAM ---

function initAdminStream() {
    console.log("[SSE] Initializing Command Center stream...");
    const eventSource = new EventSource("/api/stream");

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        const telemetry = data.telemetry;

        if (!telemetry) return;

        // 1. Update overall capacity KPIs
        document.getElementById("kpi-occupancy").textContent = telemetry.occupancy.toLocaleString();
        document.getElementById("kpi-capacity-total").textContent = `Capacity: ${telemetry.capacity.toLocaleString()}`;

        // 2. Update staff availability badges
        document.getElementById("admin-security-avail").textContent = telemetry.staff.security.available;
        document.getElementById("admin-medical-avail").textContent = telemetry.staff.medical.available;

        // 3. Render Zone Management & Dispatch list
        const zoneList = document.getElementById("admin-zone-list");
        if (zoneList && telemetry.zones) {
            zoneList.innerHTML = telemetry.zones.map(zone => {
                // Count deployed staff in this zone
                const secDeployed = telemetry.staff.security.deployed.filter(d => d.zone_id === zone.id).length;
                const medDeployed = telemetry.staff.medical.deployed.filter(d => d.zone_id === zone.id).length;
                
                let staffStatus = "";
                if (secDeployed > 0) staffStatus += `🛡️ ${secDeployed} Security `;
                if (medDeployed > 0) staffStatus += `🩺 ${medDeployed} Medical`;

                return `
                    <li class="info-item" style="flex-wrap: wrap; gap: 0.5rem;">
                        <div style="flex: 1; min-width: 150px;">
                            <span class="item-name" style="font-weight:700;">${zone.name}</span>
                            <div style="font-size:0.75rem; color:var(--text-muted); margin-top: 0.15rem;">
                                ${staffStatus || "No deployed units"}
                            </div>
                        </div>
                        <span class="item-value ${getCrowdBadgeClass(zone.crowdLevel)}" style="margin-right: 1rem;">
                            Density: ${zone.crowdLevel}%
                        </span>
                        <div class="staff-actions">
                            <button class="btn-dispatch security" onclick="dispatchStaff('security', '${zone.id}')" ${telemetry.staff.security.available === 0 ? "disabled" : ""}>
                                Deploy Sec.
                            </button>
                            <button class="btn-dispatch medical" onclick="dispatchStaff('medical', '${zone.id}')" ${telemetry.staff.medical.available === 0 ? "disabled" : ""}>
                                Deploy Med.
                            </button>
                        </div>
                    </li>
                `;
            }).join("");
        }
    };

    eventSource.onerror = function() {
        console.warn("[SSE] Admin stream connection interrupted.");
    };
}

// --- ADMIN DISPATCH ACTION ---

async function dispatchStaff(type, zoneId) {
    try {
        const response = await fetch("/api/admin/dispatch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ type: type, zone_id: zoneId })
        });
        const data = await response.json();
        if (!response.ok) {
            alert(data.message || "Dispatch failed.");
        }
    } catch (e) {
        console.error("Dispatch request error", e);
    }
}

// --- ADMIN BROADCAST SUBMIT ---

async function handleBroadcastSubmit(event) {
    event.preventDefault();
    const msgInput = document.getElementById("alert-msg");
    const radios = document.getElementsByName("alert-type");
    let alertType = "info";

    for (let r of radios) {
        if (r.checked) {
            alertType = r.value;
            break;
        }
    }

    const payload = {
        message: msgInput.value,
        type: alertType
    };

    try {
        const response = await fetch("/api/admin/broadcast", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            msgInput.value = "";
            // Optionally check success
        } else {
            const data = await response.json();
            alert(data.message || "Failed to broadcast message.");
        }
    } catch (e) {
        console.error("Broadcast network error", e);
    }
}

// HTML escape function to mitigate XSS
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

function appendChatMessage(sender, text) {
    const chatBox = document.getElementById("chat-messages");
    if (!chatBox) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-msg ${sender}`;
    
    // First escape the message text to prevent script injection (XSS)
    const escapedText = escapeHTML(text);
    
    // Convert markdown paragraphs/bullet lists/bold text to clean HTML
    let formattedText = escapedText
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/###\s(.*?)\n/g, '<h3>$1</h3>')
        .replace(/\n\n/g, '<p></p>')
        .replace(/\*\s(.*?)\n/g, '<li>$1</li>');
        
    // Wrap lists in ul
    if (formattedText.includes('<li>')) {
        // Simple search and wrap list items
        formattedText = formattedText.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
    }

    msgDiv.innerHTML = formattedText;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function showTypingIndicator() {
    const chatBox = document.getElementById("chat-messages");
    if (!chatBox) return null;

    const indDiv = document.createElement("div");
    indDiv.className = "chat-msg bot typing-indicator";
    indDiv.innerHTML = "<span style='opacity:0.6;'>Gemini is analyzing live telemetry...</span>";
    chatBox.appendChild(indDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    return indDiv;
}

async function handleChatSubmit(event) {
    if (event) event.preventDefault();
    const chatInput = document.getElementById("chat-input");
    if (!chatInput) return;

    const message = chatInput.value.trim();
    if (!message) return;

    // Clear input
    chatInput.value = "";

    // Show user message
    appendChatMessage("user", message);

    // Show typing bubble
    const typingIndicator = showTypingIndicator();

    try {
        const response = await fetch("/api/assistant/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message })
        });
        const data = await response.json();

        // Remove typing bubble
        if (typingIndicator) typingIndicator.remove();

        if (response.ok) {
            appendChatMessage("bot", data.message);
        } else {
            appendChatMessage("bot", "⚠️ Sorry, I could not query the telemetry engine at this moment.");
        }
    } catch (e) {
        if (typingIndicator) typingIndicator.remove();
        appendChatMessage("bot", "❌ Server offline. Telemetry is unavailable.");
    }
}

// Smart Pathfinder shortcuts run direct queries
function quickQuery(text) {
    const chatInput = document.getElementById("chat-input");
    if (chatInput) {
        chatInput.value = text;
        handleChatSubmit(null);
    }
}
