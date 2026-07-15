// --- AI SUPER ASSISTANT & TOURIST AGENT ---

async function handleSuperChatSubmit(event) {
    event.preventDefault();
    const chatInput = document.getElementById("super-chat-input");
    const chatBox = document.getElementById("super-chat-messages");
    if (!chatInput || !chatBox) return;

    const message = chatInput.value.trim();
    if (!message) return;

    chatInput.value = "";

    // Append user message bubble
    const userDiv = document.createElement("div");
    userDiv.className = "chat-msg user";
    userDiv.textContent = message;
    chatBox.appendChild(userDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    // Loading indicator
    const typingDiv = document.createElement("div");
    typingDiv.className = "chat-msg bot";
    typingDiv.innerHTML = "<span style='opacity:0.6;'>Super Assistant is querying stadium maps and Gemini context...</span>";
    chatBox.appendChild(typingDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const response = await fetch("/extended/api/chatbot/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message })
        });
        const data = await response.json();
        
        typingDiv.remove();

        const botDiv = document.createElement("div");
        botDiv.className = "chat-msg bot";
        
        // Sanitize response to prevent Cross-Site Scripting (XSS)
        const escaped = escapeHTML(data.reply);
        let formatted = escaped
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*\s(.*?)\n/g, '<li>$1</li>')
            .replace(/\n/g, '<br>');
            
        botDiv.innerHTML = formatted;
        chatBox.appendChild(botDiv);
        chatBox.scrollTop = chatBox.scrollHeight;

        // Auto Speak out loud if Voice Assist is active
        if (typeof voiceSpeakAloud === "function") {
            voiceSpeakAloud(data.reply);
        }
    } catch (e) {
        typingDiv.remove();
        const errDiv = document.createElement("div");
        errDiv.className = "chat-msg bot";
        errDiv.textContent = "❌ Connection failed. AI Assistant is offline.";
        chatBox.appendChild(errDiv);
    }
}

// Utility: HTML Sanitizer to prevent Script Injection attacks
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
