// --- VOICE ASSISTANT ENGINE (SPEECH-TO-TEXT & TEXT-TO-SPEECH) ---

let speechRecognitionInstance = null;
let isVoiceListening = false;

function initVoiceAssistant() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("SpeechRecognition API is not supported in this browser.");
        return;
    }

    speechRecognitionInstance = new SpeechRecognition();
    speechRecognitionInstance.continuous = false;
    speechRecognitionInstance.interimResults = false;
    speechRecognitionInstance.lang = 'en-US';

    speechRecognitionInstance.onstart = () => {
        isVoiceListening = true;
        const btn = document.getElementById("btn-voice-chat");
        if (btn) btn.textContent = "🎙️ Listening...";
    };

    speechRecognitionInstance.onend = () => {
        isVoiceListening = false;
        const btn = document.getElementById("btn-voice-chat");
        if (btn) btn.textContent = "🎤 Listen Mode";
    };

    speechRecognitionInstance.onresult = (event) => {
        const text = event.results[0][0].transcript;
        const input = document.getElementById("super-chat-input");
        if (input) {
            input.value = text;
            // Trigger submit automatically
            handleSuperChatSubmit(new Event('submit'));
        }
    };

    speechRecognitionInstance.onerror = (event) => {
        console.error("Speech Recognition Error", event.error);
    };
}

function startVoiceRecognition() {
    if (!speechRecognitionInstance) {
        initVoiceAssistant();
    }
    
    if (!speechRecognitionInstance) {
        alert("Voice recognition is not supported or was blocked by browser security.");
        return;
    }

    if (isVoiceListening) {
        speechRecognitionInstance.stop();
    } else {
        speechRecognitionInstance.start();
    }
}

// Speak response out loud using Web Speech Synthesis API
function voiceSpeakAloud(text) {
    if (!('speechSynthesis' in window)) return;
    
    // Stop any ongoing narration
    window.speechSynthesis.cancel();
    
    const cleaned = text.replace(/<[^>]*>/g, ''); // Strip HTML tags
    const utterance = new SpeechSynthesisUtterance(cleaned);
    
    // Check if Indian language is selected to adjust accent if supported
    const lang = localStorage.getItem("stadium_indian_lang") || "en";
    const langCodes = {
        hi: 'hi-IN',
        kn: 'kn-IN',
        ta: 'ta-IN',
        te: 'te-IN'
    };
    if (langCodes[lang]) {
        utterance.lang = langCodes[lang];
    }
    
    window.speechSynthesis.speak(utterance);
}

// Hold to Speak triggers
function toggleHoldToSpeak() {
    startVoiceRecognition();
}

document.addEventListener("DOMContentLoaded", initVoiceAssistant);
