/**
 * Main application logic - grid rendering and player management.
 */
const App = (() => {
    const players = new Map(); // streamId -> WebRTCPlayer

    function init() {
        Settings.init();
        refreshGrid();
    }

    async function refreshGrid() {
        let streams;
        try {
            const resp = await fetch("/api/streams");
            streams = await resp.json();
        } catch (err) {
            console.error("Failed to fetch streams:", err);
            return;
        }

        const grid = document.getElementById("stream-grid");
        const emptyState = document.getElementById("empty-state");

        // Determine which streams to add, remove, or keep
        const currentIds = new Set(players.keys());
        const newIds = new Set(streams.map((s) => s.id));

        // Remove players that no longer exist
        for (const id of currentIds) {
            if (!newIds.has(id)) {
                const player = players.get(id);
                player.disconnect();
                players.delete(id);
                const tile = document.querySelector(`.stream-tile[data-stream-id="${id}"]`);
                if (tile) tile.remove();
            }
        }

        // Add new streams
        for (const stream of streams) {
            if (!currentIds.has(stream.id)) {
                addStreamTile(grid, stream);
            } else {
                // Update label if name changed
                const label = document.querySelector(`.stream-tile[data-stream-id="${stream.id}"] .label-text`);
                if (label) label.textContent = stream.name;
            }
        }

        // Show/hide empty state
        if (emptyState) {
            if (streams.length === 0) {
                emptyState.classList.remove("hidden");
                // Re-add to grid if removed
                if (!grid.contains(emptyState)) {
                    grid.appendChild(emptyState);
                }
            } else {
                emptyState.classList.add("hidden");
            }
        }
    }

    function addStreamTile(grid, stream) {
        const tile = document.createElement("div");
        tile.className = "stream-tile";
        tile.dataset.streamId = stream.id;

        const video = document.createElement("video");
        video.autoplay = true;
        video.muted = true;
        video.playsInline = true;

        const label = document.createElement("div");
        label.className = "stream-label";

        const labelText = document.createElement("span");
        labelText.className = "label-text";
        labelText.textContent = stream.name;

        const statusDot = document.createElement("span");
        statusDot.className = "status-dot connecting";
        statusDot.title = "Connecting...";

        label.appendChild(labelText);
        label.appendChild(statusDot);
        tile.appendChild(video);
        tile.appendChild(label);
        grid.appendChild(tile);

        // Create and connect WebRTC player
        const player = new WebRTCPlayer(video, stream.id);
        player.onStatusChange((status) => {
            statusDot.className = `status-dot ${status}`;
            const titles = {
                connecting: "Connecting...",
                connected: "Connected",
                disconnected: "Disconnected",
                error: "Connection error - retrying...",
            };
            statusDot.title = titles[status] || status;
        });

        players.set(stream.id, player);
        player.connect();
    }

    // Initialize when DOM is ready
    document.addEventListener("DOMContentLoaded", init);

    return { refreshGrid };
})();
