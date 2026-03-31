/**
 * WebRTC player component for a single RTSP stream via go2rtc.
 */
class WebRTCPlayer {
    constructor(videoElement, streamId) {
        this.video = videoElement;
        this.streamId = streamId;
        this.pc = null;
        this._status = "disconnected";
        this._statusCallbacks = [];
        this._reconnectTimer = null;
        this._reconnectDelay = 5000;
        this._maxReconnectDelay = 30000;
        this._stopped = false;
    }

    async connect() {
        this._stopped = false;
        this._setStatus("connecting");

        try {
            // Clean up any previous connection
            this._closePeerConnection();

            this.pc = new RTCPeerConnection({
                iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
            });

            // Receive-only transceivers for video and audio
            this.pc.addTransceiver("video", { direction: "recvonly" });
            this.pc.addTransceiver("audio", { direction: "recvonly" });

            // Handle incoming tracks
            this.pc.ontrack = (event) => {
                if (event.streams && event.streams[0]) {
                    this.video.srcObject = event.streams[0];
                }
            };

            // Monitor connection state
            this.pc.onconnectionstatechange = () => {
                const state = this.pc.connectionState;
                if (state === "connected") {
                    this._setStatus("connected");
                    this._reconnectDelay = 5000; // Reset backoff
                } else if (state === "failed" || state === "disconnected") {
                    this._setStatus("error");
                    this._scheduleReconnect();
                }
            };

            // Create and set local offer
            const offer = await this.pc.createOffer();
            await this.pc.setLocalDescription(offer);

            // Wait for ICE gathering to complete (or timeout)
            await this._waitForIceGathering(2000);

            // Send offer to our signaling proxy
            const response = await fetch(`/api/webrtc?src=${encodeURIComponent(this.streamId)}`, {
                method: "POST",
                headers: { "Content-Type": "application/sdp" },
                body: this.pc.localDescription.sdp,
            });

            if (!response.ok) {
                const detail = await response.text();
                if (response.status === 503) {
                    // go2rtc is restarting — retry silently
                    console.log(`[WebRTCPlayer:${this.streamId}] go2rtc restarting, will retry...`);
                    this._closePeerConnection();
                    this._scheduleReconnect();
                    return;
                }
                throw new Error(`Signaling failed (${response.status}): ${detail}`);
            }

            // go2rtc may return raw SDP or JSON {"type":"answer","sdp":"..."}
            const answerText = await response.text();
            let answerSdp;
            try {
                const parsed = JSON.parse(answerText);
                answerSdp = parsed.sdp || answerText;
            } catch {
                // Not JSON — treat as raw SDP
                answerSdp = answerText;
            }

            await this.pc.setRemoteDescription(new RTCSessionDescription({
                type: "answer",
                sdp: answerSdp,
            }));
        } catch (err) {
            console.error(`[WebRTCPlayer:${this.streamId}] Connection error:`, err);
            this._setStatus("error");
            this._scheduleReconnect();
        }
    }

    disconnect() {
        this._stopped = true;
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
            this._reconnectTimer = null;
        }
        this._closePeerConnection();
        this.video.srcObject = null;
        this._setStatus("disconnected");
    }

    getStatus() {
        return this._status;
    }

    onStatusChange(callback) {
        this._statusCallbacks.push(callback);
    }

    _setStatus(status) {
        if (this._status !== status) {
            this._status = status;
            this._statusCallbacks.forEach((cb) => cb(status, this.streamId));
        }
    }

    _closePeerConnection() {
        if (this.pc) {
            this.pc.ontrack = null;
            this.pc.onconnectionstatechange = null;
            this.pc.close();
            this.pc = null;
        }
    }

    _scheduleReconnect() {
        if (this._stopped || this._reconnectTimer) return;

        console.log(`[WebRTCPlayer:${this.streamId}] Reconnecting in ${this._reconnectDelay / 1000}s...`);
        this._reconnectTimer = setTimeout(() => {
            this._reconnectTimer = null;
            if (!this._stopped) {
                this.connect();
            }
        }, this._reconnectDelay);

        // Exponential backoff
        this._reconnectDelay = Math.min(this._reconnectDelay * 1.5, this._maxReconnectDelay);
    }

    _waitForIceGathering(timeout) {
        return new Promise((resolve) => {
            if (this.pc.iceGatheringState === "complete") {
                resolve();
                return;
            }

            const timer = setTimeout(() => {
                this.pc.removeEventListener("icegatheringstatechange", check);
                resolve();
            }, timeout);

            const check = () => {
                if (this.pc.iceGatheringState === "complete") {
                    clearTimeout(timer);
                    this.pc.removeEventListener("icegatheringstatechange", check);
                    resolve();
                }
            };

            this.pc.addEventListener("icegatheringstatechange", check);
        });
    }
}
