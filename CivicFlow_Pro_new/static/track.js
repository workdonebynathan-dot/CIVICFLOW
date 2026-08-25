document.addEventListener("DOMContentLoaded", function() {
    // Check if we are on the tracking page and have a tracking ID
    const trackingIdElement = document.getElementById("tracking-id-display");
    
    if (trackingIdElement) {
        const trackingId = trackingIdElement.innerText.trim();
        startPolling(trackingId);
    }
});

function startPolling(trackingId) {
    // Poll every 5 seconds (5000 ms)
    setInterval(() => {
        fetch(`/api/status/${trackingId}`)
            .then(response => response.json())
            .then(data => {
                updateStatusUI(data);
            })
            .catch(error => console.error("Error fetching updates:", error));
    }, 5000);
}

function updateStatusUI(data) {
    const currentStatus = data.current_status.status;
    
    // 1. Update the main status badge
    const statusBadge = document.querySelector(".badge");
    if (statusBadge) {
        statusBadge.innerText = currentStatus;
        // Update class for color (e.g., badge registered -> badge resolved)
        statusBadge.className = `badge ${currentStatus.toLowerCase()}`;
    }

    // 2. Update the timeline
    const timelineContainer = document.querySelector(".timeline");
    if (timelineContainer && data.timeline) {
        timelineContainer.innerHTML = ""; // Clear existing list
        
        data.timeline.forEach(item => {
            const html = `
                <div class="timeline-item">
                    <div class="dot"></div>
                    <div class="content">
                        <strong>${item.status}</strong>
                        <p>${item.remarks || "No remarks"}</p>
                        <small>${item.updated_at}</small>
                    </div>
                </div>
            `;
            timelineContainer.innerHTML += html;
        });
    }
}