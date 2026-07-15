// --- KICKOFF COUNTDOWN TIMER CLOCK ---

function initKickoffCountdown() {
    const clock = document.getElementById("countdown-clock");
    if (!clock) return;

    // Target kickoff time: Today at 19:30
    const now = new Date();
    const kickoff = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 19, 30, 0);
    
    // If kickoff has already passed for the day, target tomorrow
    if (now.getTime() > kickoff.getTime()) {
        kickoff.setDate(kickoff.getDate() + 1);
    }

    function updateTimer() {
        const timeDiff = kickoff.getTime() - new Date().getTime();
        if (timeDiff <= 0) {
            clock.textContent = "00:00:00";
            document.getElementById("countdown-label").textContent = "Match started! Gates are open.";
            return;
        }

        const hrs = Math.floor(timeDiff / (1000 * 60 * 60));
        const mins = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
        const secs = Math.floor((timeDiff % (1000 * 60)) / 1000);

        const pad = (n) => str = n.toString().padStart(2, '0');
        clock.textContent = `${pad(hrs)}:${pad(mins)}:${pad(secs)}`;
    }

    updateTimer();
    setInterval(updateTimer, 1000);
}

document.addEventListener("DOMContentLoaded", initKickoffCountdown);
