// --- INDIAN LANGUAGE TRANSLATIONS MODULE ---

async function changeIndianLanguage(lang) {
    // Save language selection
    localStorage.setItem("stadium_indian_lang", lang);

    // Urdu requires RTL layouts
    if (lang === "ur") {
        document.body.style.direction = "rtl";
        document.body.style.textAlign = "right";
    } else {
        document.body.style.direction = "ltr";
        document.body.style.textAlign = "left";
    }

    // Load language translation cache from LocalStorage
    const cacheKey = `lang_cache_${lang}`;
    let cachedDict = {};
    try {
        const stored = localStorage.getItem(cacheKey);
        if (stored) {
            cachedDict = JSON.parse(stored);
        }
    } catch (e) {
        console.warn("Translation cache read error", e);
    }

    // Find all translatable elements
    const elements = document.querySelectorAll("[data-translate]");
    let cacheDirty = false;

    for (let el of elements) {
        const key = el.getAttribute("data-translate");
        
        // Cache-First: Use local translation if available
        if (cachedDict[key]) {
            el.textContent = cachedDict[key];
            continue;
        }

        // Cache Miss: Query server
        try {
            const response = await fetch("/extended/api/translation", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ key: key, lang: lang })
            });
            const data = await response.json();
            if (response.ok) {
                el.textContent = data.translated;
                cachedDict[key] = data.translated;
                cacheDirty = true;
            }
        } catch (e) {
            console.error("Translation API fetch error", e);
        }
    }

    // Commit populated dictionary back to cache
    if (cacheDirty) {
        try {
            localStorage.setItem(cacheKey, JSON.stringify(cachedDict));
        } catch (e) {
            console.warn("Failed to write translation cache", e);
        }
    }
}

// Load selected language on page load
document.addEventListener("DOMContentLoaded", () => {
    const saved = localStorage.getItem("stadium_indian_lang") || "en";
    const selector = document.getElementById("indian-lang-selector");
    if (selector) {
        selector.value = saved;
        changeIndianLanguage(saved);
    }
});
