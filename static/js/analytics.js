// --- OPERATIONS ANALYTICS ENGINE (Chart.js Config) ---

let crowdChartInstance = null;
let gatesChartInstance = null;

async function loadAnalyticsCharts() {
    try {
        const response = await fetch("/api/analytics/data");
        const data = await response.json();
        if (!response.ok) return;

        const metrics = data.metrics;
        
        // 1. Render Summary stats
        document.getElementById("stat-peak-wait").textContent = `${metrics.summary.peakWaitTime}m`;
        document.getElementById("stat-avg-wait").textContent = `${metrics.summary.avgWaitTime}m`;
        document.getElementById("stat-dispatches").textContent = metrics.summary.totalDispatches;
        document.getElementById("stat-alerts").textContent = metrics.summary.totalAlerts;
        document.getElementById("stat-ai-queries").textContent = metrics.summary.aiChatQueries;
        document.getElementById("stat-fan-views").textContent = metrics.summary.fanActivity;

        // 2. Setup Crowd occupancy trends chart (Line Chart)
        const crowdCtx = document.getElementById("crowdChart");
        if (crowdCtx) {
            const labels = metrics.crowdTrends.map(t => t.time);
            const values = metrics.crowdTrends.map(t => t.occupancy);
            
            if (crowdChartInstance) crowdChartInstance.destroy();
            crowdChartInstance = new Chart(crowdCtx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Stadium Occupancy',
                        data: values,
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.15)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: { color: '#94a3b8' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#94a3b8' }
                        }
                    }
                }
            });
        }

        // 3. Setup Gate wait times chart (Bar Chart)
        const gatesCtx = document.getElementById("gatesChart");
        if (gatesCtx) {
            const labels = metrics.gateMetrics.map(g => g.name);
            const values = metrics.gateMetrics.map(g => g.waitTime);
            
            if (gatesChartInstance) gatesChartInstance.destroy();
            gatesChartInstance = new Chart(gatesCtx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Wait Time (Minutes)',
                        data: values,
                        backgroundColor: values.map(v => v > 20 ? '#ef4444' : (v > 10 ? '#f59e0b' : '#10b981')),
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: { color: '#94a3b8' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#94a3b8' }
                        }
                    }
                }
            });
        }
    } catch (e) {
        console.error("Error loading charts", e);
    }
}

// --- CROWD PREDICTION GRID ---

let currentPredictionTab = "5_min";

async function selectPredictionTab(tabId) {
    currentPredictionTab = tabId;
    
    // Toggle active state on tabs
    document.querySelectorAll(".pred-tab-btn").forEach(btn => {
        if (btn.id === `pred-tab-${tabId}`) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    await loadPredictions();
}

async function loadPredictions() {
    const listContainer = document.getElementById("predictions-list");
    if (!listContainer) return;

    try {
        const response = await fetch("/api/predictions");
        const data = await response.json();
        if (!response.ok) return;

        const zonePredictions = data.predictions[currentPredictionTab] || [];
        
        listContainer.innerHTML = zonePredictions.map(p => {
            let badgeClass = "badge-clear";
            if (p.status === "Moderate") badgeClass = "badge-warning";
            if (p.status === "Congested") badgeClass = "badge-danger";

            return `
                <div class="glass-card" style="padding: 1rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 700; font-size: 0.95rem;">${p.name}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.15rem;">
                            Current telemetry is factored
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <span style="font-size: 1.1rem; font-weight: 800; font-feature-settings: 'tnum';">${p.predictedLevel}%</span>
                        <span class="item-value ${badgeClass}" style="padding: 0.2rem 0.6rem; font-size: 0.75rem; border-radius: 50px;">
                            ${p.status}
                        </span>
                    </div>
                </div>
            `;
        }).join("");
    } catch (e) {
        console.error("Error loading predictions", e);
    }
}

// --- PARKING MANAGEMENT DISPLAY ---

async function loadParkingData() {
    const container = document.getElementById("parking-container");
    if (!container) return;

    try {
        const response = await fetch("/api/parking");
        const data = await response.json();
        if (!response.ok) return;

        container.innerHTML = data.parking.map(p => {
            const occupancyPct = Math.round((p.occupied / p.total_slots) * 100);
            let barColor = "var(--success)";
            if (occupancyPct > 70) barColor = "var(--warning)";
            if (occupancyPct > 90) barColor = "var(--danger)";

            return `
                <div class="glass-card" style="padding: 1.5rem; display: flex; flex-direction: column; gap: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="font-weight:700; font-size: 1.1rem;">🚗 ${p.name}</h3>
                        <span style="font-size: 0.8rem; padding: 0.25rem 0.75rem; border-radius: 50px; background: rgba(255,255,255,0.05); font-weight:600;">
                            🚶 ${p.walking_time_mins} min walk
                        </span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.25rem;">
                        <span>Available Slots: <strong>${p.total_slots - p.occupied}</strong> / ${p.total_slots}</span>
                        <span>${occupancyPct}% full</span>
                    </div>
                    
                    <!-- Progress Bar -->
                    <div style="width: 100%; height: 8px; background: rgba(0,0,0,0.3); border-radius: 50px; overflow: hidden; border: 1px solid var(--glass-border);">
                        <div style="width: ${occupancyPct}%; height: 100%; background: ${barColor}; border-radius: 50px; transition: var(--transition-smooth);"></div>
                    </div>
                </div>
            `;
        }).join("");
    } catch (e) {
        console.error("Error loading parking", e);
    }
}

// --- AI OPERATIONS COPILOT CHAT ---

async function handleCopilotSubmit(event) {
    event.preventDefault();
    const chatInput = document.getElementById("copilot-input");
    const chatBox = document.getElementById("copilot-messages");
    if (!chatInput || !chatBox) return;

    const message = chatInput.value.trim();
    if (!message) return;

    chatInput.value = "";

    // Render user message
    const userDiv = document.createElement("div");
    userDiv.className = "chat-msg user";
    userDiv.textContent = message;
    chatBox.appendChild(userDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    // Show loading
    const typingDiv = document.createElement("div");
    typingDiv.className = "chat-msg bot";
    typingDiv.innerHTML = "<span style='opacity: 0.6;'>Copilot is analyzing logs and alerts...</span>";
    chatBox.appendChild(typingDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const response = await fetch("/api/copilot/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message })
        });
        const data = await response.json();
        
        typingDiv.remove();

        const botDiv = document.createElement("div");
        botDiv.className = "chat-msg bot";
        
        // Convert Markdown bold tags to HTML
        let formatted = data.message
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*\s(.*?)\n/g, '<li>$1</li>')
            .replace(/\n\n/g, '<p></p>');
            
        if (formatted.includes('<li>')) {
            formatted = formatted.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
        }

        botDiv.innerHTML = formatted;
        chatBox.appendChild(botDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    } catch (e) {
        typingDiv.remove();
        const errDiv = document.createElement("div");
        errDiv.className = "chat-msg bot";
        errDiv.textContent = "❌ Connection failed. Copilot could not reach the server.";
        chatBox.appendChild(errDiv);
    }
}

function copilotQuickQuery(text) {
    const input = document.getElementById("copilot-input");
    if (input) {
        input.value = text;
        handleCopilotSubmit(new Event('submit'));
    }
}
