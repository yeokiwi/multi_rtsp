/**
 * Settings panel logic for managing RTSP streams.
 */
const Settings = (() => {
    let _editingId = null;

    function init() {
        document.getElementById("settings-btn").addEventListener("click", open);
        document.getElementById("settings-close").addEventListener("click", close);
        document.getElementById("overlay").addEventListener("click", close);
        document.getElementById("add-stream-btn").addEventListener("click", showAddForm);
        document.getElementById("form-cancel").addEventListener("click", hideForm);
        document.getElementById("form-save").addEventListener("click", saveForm);

        // Allow Enter key to submit the form
        document.getElementById("stream-url").addEventListener("keydown", (e) => {
            if (e.key === "Enter") saveForm();
        });
    }

    function open() {
        document.getElementById("settings-panel").classList.remove("hidden");
        document.getElementById("overlay").classList.remove("hidden");
        loadStreamList();
    }

    function close() {
        document.getElementById("settings-panel").classList.add("hidden");
        document.getElementById("overlay").classList.add("hidden");
        hideForm();
    }

    function showAddForm() {
        _editingId = null;
        document.getElementById("form-title").textContent = "Add Stream";
        document.getElementById("stream-name").value = "";
        document.getElementById("stream-url").value = "";
        document.getElementById("form-error").classList.add("hidden");
        document.getElementById("stream-form").classList.remove("hidden");
        document.getElementById("stream-name").focus();
    }

    function showEditForm(stream) {
        _editingId = stream.id;
        document.getElementById("form-title").textContent = "Edit Stream";
        document.getElementById("stream-name").value = stream.name;
        document.getElementById("stream-url").value = stream.url;
        document.getElementById("form-error").classList.add("hidden");
        document.getElementById("stream-form").classList.remove("hidden");
        document.getElementById("stream-name").focus();
    }

    function hideForm() {
        document.getElementById("stream-form").classList.add("hidden");
        _editingId = null;
    }

    function showError(msg) {
        const el = document.getElementById("form-error");
        el.textContent = msg;
        el.classList.remove("hidden");
    }

    async function saveForm() {
        const name = document.getElementById("stream-name").value.trim();
        const url = document.getElementById("stream-url").value.trim();

        if (!name) {
            showError("Name is required.");
            return;
        }
        if (!url) {
            showError("RTSP URL is required.");
            return;
        }
        if (!url.startsWith("rtsp://") && !url.startsWith("rtsps://")) {
            showError("URL must start with rtsp:// or rtsps://");
            return;
        }

        try {
            if (_editingId) {
                await fetch(`/api/streams/${encodeURIComponent(_editingId)}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, url }),
                });
            } else {
                await fetch("/api/streams", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, url }),
                });
            }

            hideForm();
            loadStreamList();

            // Refresh the main grid
            if (typeof App !== "undefined") {
                App.refreshGrid();
            }
        } catch (err) {
            showError("Failed to save stream. Check console for details.");
            console.error("Save error:", err);
        }
    }

    async function deleteStream(id) {
        if (!confirm("Remove this stream?")) return;

        try {
            await fetch(`/api/streams/${encodeURIComponent(id)}`, { method: "DELETE" });
            loadStreamList();
            if (typeof App !== "undefined") {
                App.refreshGrid();
            }
        } catch (err) {
            console.error("Delete error:", err);
        }
    }

    async function loadStreamList() {
        const container = document.getElementById("stream-list");
        try {
            const resp = await fetch("/api/streams");
            const streams = await resp.json();

            if (streams.length === 0) {
                container.innerHTML = '<p style="color: var(--text-secondary); margin-top: 16px; text-align: center;">No streams configured.</p>';
                return;
            }

            container.innerHTML = streams.map((s) => {
                // Mask password in URL for display
                const maskedUrl = s.url.replace(/:([^@/:]+)@/, ":****@");
                return `
                    <div class="stream-item" data-id="${s.id}">
                        <div class="stream-item-info">
                            <div class="stream-item-name">${escapeHtml(s.name)}</div>
                            <div class="stream-item-url" title="${escapeHtml(s.url)}">${escapeHtml(maskedUrl)}</div>
                        </div>
                        <div class="stream-item-actions">
                            <button class="btn-edit" onclick="Settings.editStream('${s.id}')">Edit</button>
                            <button class="btn-danger" onclick="Settings.deleteStream('${s.id}')">Delete</button>
                        </div>
                    </div>
                `;
            }).join("");
        } catch (err) {
            container.innerHTML = '<p style="color: var(--danger);">Failed to load streams.</p>';
        }
    }

    async function editStream(id) {
        try {
            const resp = await fetch("/api/streams");
            const streams = await resp.json();
            const stream = streams.find((s) => s.id === id);
            if (stream) showEditForm(stream);
        } catch (err) {
            console.error("Edit error:", err);
        }
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    return { init, open, close, editStream, deleteStream };
})();
