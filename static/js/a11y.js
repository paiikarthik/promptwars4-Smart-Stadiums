// --- ACCESSIBILITY (A11y) MANAGEMENT SYSTEM ---

let isVoiceReadingEnabled = false;

function toggleHighContrast() {
    const isHC = document.body.classList.toggle("high-contrast");
    localStorage.setItem("a11y_high_contrast", isHC ? "true" : "false");
}

function toggleLargeText() {
    const isLT = document.body.classList.toggle("large-text");
    localStorage.setItem("a11y_large_text", isLT ? "true" : "false");
}

function toggleVoiceReading() {
    isVoiceReadingEnabled = !isVoiceReadingEnabled;
    const btn = document.getElementById("btn-voice-read");
    if (btn) {
        btn.classList.toggle("active", isVoiceReadingEnabled);
        btn.textContent = isVoiceReadingEnabled ? "Voice Reading: ON" : "Voice Reading: OFF";
    }
    
    if (isVoiceReadingEnabled) {
        speakAloud("Voice reading enabled. Hover over titles to hear them read aloud.");
    } else {
        window.speechSynthesis.cancel();
    }
}

// Text-to-Speech Helper
function speakAloud(text) {
    if (!('speechSynthesis' in window)) return;
    
    // Stop any ongoing speech
    window.speechSynthesis.cancel();

    const cleanText = text.replace(/<[^>]*>/g, ''); # Remove HTML
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    utterance.volume = 1.0;
    window.speechSynthesis.speak(utterance);
}

// Attach hover speech triggers to accessible elements
document.addEventListener("mouseover", (event) => {
    if (!isVoiceReadingEnabled) return;

    const el = event.target;
    // Check if the hovered element has text we want to read
    if (el.tagName === "H1" || el.tagName === "H2" || el.tagName === "H3" || el.classList.contains("kpi-value") || el.classList.contains("kpi-title")) {
        speakAloud(el.textContent);
    }
});

// Load preferences on start
document.addEventListener("DOMContentLoaded", () => {
    if (localStorage.getItem("a11y_high_contrast") === "true") {
        document.body.classList.add("high-contrast");
    }
    if (localStorage.getItem("a11y_large_text") === "true") {
        document.body.classList.add("large-text");
    }

    // Append accessibility stylesheet styles programmatically to avoid rewriting CSS
    const styleEl = document.createElement("style");
    styleEl.innerHTML = `
        /* High Contrast Mode CSS Overrides */
        body.high-contrast {
            background: #000000 !important;
            color: #ffffff !important;
        }
        body.high-contrast .glass-card {
            background: #000000 !important;
            border: 2px solid #ffffff !important;
            backdrop-filter: none !important;
            color: #ffffff !important;
            box-shadow: none !important;
        }
        body.high-contrast .kpi-value,
        body.high-contrast .brand,
        body.high-contrast .action-value {
            color: #ffff00 !important;
            background: none !important;
            -webkit-text-fill-color: initial !important;
        }
        body.high-contrast button,
        body.high-contrast .btn-submit,
        body.high-contrast .btn-dispatch {
            background: #ffffff !important;
            color: #000000 !important;
            border: 2px solid #ffff00 !important;
            box-shadow: none !important;
        }
        body.high-contrast button:hover {
            background: #ffff00 !important;
        }
        body.high-contrast .badge-clear {
            background: #000000 !important;
            color: #00ff00 !important;
            border-color: #00ff00 !important;
        }
        body.high-contrast .badge-warning {
            background: #000000 !important;
            color: #ffaa00 !important;
            border-color: #ffaa00 !important;
        }
        body.high-contrast .badge-danger {
            background: #000000 !important;
            color: #ff0000 !important;
            border-color: #ff0000 !important;
            animation: none !important;
        }
        
        /* Large Text Mode CSS Overrides */
        body.large-text {
            font-size: 1.25rem !important;
        }
        body.large-text h1, body.large-text .portal-title {
            font-size: 2.8rem !important;
        }
        body.large-text h2, body.large-text .section-title {
            font-size: 1.8rem !important;
        }
        body.large-text h3 {
            font-size: 1.4rem !important;
        }
        body.large-text .kpi-value {
            font-size: 3rem !important;
        }
        body.large-text .chat-msg {
            font-size: 1.1rem !important;
        }
    `;
    document.head.appendChild(styleEl);
});
