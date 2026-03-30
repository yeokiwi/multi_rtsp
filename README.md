# Multi-RTSP Stream Viewer

A web-based viewer for displaying multiple RTSP camera streams simultaneously in a browser. Uses [go2rtc](https://github.com/AlexxIT/go2rtc) for RTSP-to-WebRTC conversion, delivering sub-second latency video playback.

## Features

- **Low-latency streaming** -- WebRTC delivery with sub-second latency via go2rtc
- **Responsive grid layout** -- auto-adjusting columns that adapt from mobile to multi-monitor setups
- **Runtime stream management** -- add, edit, and remove RTSP streams through the web UI without restarting
- **Persistent configuration** -- streams are saved to a YAML config file and restored on startup
- **Auto-reconnect** -- streams automatically reconnect with exponential backoff if the connection drops
- **Status indicators** -- live connection status (connected/connecting/error) shown on each stream tile
- **Dark theme** -- designed for video monitoring use cases

## Architecture

```
Browser <──WebRTC──> go2rtc <──RTSP──> IP Cameras
   |                   ^
   └──HTTP/API──> FastAPI backend
                  (config + signaling proxy)
```

| Component | Role |
|-----------|------|
| **FastAPI** | Serves the web UI, REST API for stream CRUD, proxies WebRTC signaling |
| **go2rtc** | Converts RTSP streams to WebRTC (runs as a managed subprocess) |
| **Frontend** | Plain HTML/CSS/JS -- responsive grid with WebRTC video players |

## Requirements

- Python 3.10+
- Internet connection (for initial go2rtc binary download)
- RTSP camera streams accessible from the host machine

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yeokiwi/multi_rtsp.git
cd multi_rtsp
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Download the go2rtc binary

```bash
python setup_go2rtc.py
```

This auto-detects your platform (Linux/macOS/Windows, amd64/arm64) and downloads the appropriate go2rtc binary to the `bin/` directory.

To re-download or update:

```bash
python setup_go2rtc.py --force
```

## Configuration

Streams can be configured in two ways:

### Option A: Edit `config.yaml` before starting

```yaml
app:
  host: "0.0.0.0"
  port: 8000
  go2rtc_port: 1984

streams:
  front_door:
    name: "Front Door"
    url: "rtsp://admin:password@192.168.1.100:554/stream1"
  backyard:
    name: "Backyard"
    url: "rtsp://admin:password@192.168.1.101:554/stream1"
  garage:
    name: "Garage"
    url: "rtsp://admin:password@192.168.1.102:554/stream1"
```

### Option B: Use the web UI at runtime

Click the **Settings** button in the top-right corner to add, edit, or remove streams. Changes are automatically saved to `config.yaml`.

### Configuration reference

| Setting | Default | Description |
|---------|---------|-------------|
| `app.host` | `0.0.0.0` | Address the web server binds to |
| `app.port` | `8000` | Web server port |
| `app.go2rtc_port` | `1984` | Internal port for the go2rtc API |

## Running

```bash
python run.py
```

Then open **http://localhost:8000** in your browser.

### Command-line options

```
python run.py [--host HOST] [--port PORT] [--config CONFIG]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | from config | Override the bind address |
| `--port` | from config | Override the web server port |
| `--config` | `config.yaml` | Path to the configuration file |

### Examples

```bash
# Start on a custom port
python run.py --port 9000

# Use a different config file
python run.py --config /etc/multi_rtsp/config.yaml

# Bind to localhost only
python run.py --host 127.0.0.1
```

## Project Structure

```
multi_rtsp/
├── run.py                  # Entry point
├── setup_go2rtc.py         # go2rtc binary downloader
├── config.yaml             # Stream configuration
├── requirements.txt        # Python dependencies
├── app/
│   ├── main.py             # FastAPI app + lifecycle management
│   ├── config.py           # YAML config manager
│   ├── go2rtc_manager.py   # go2rtc subprocess manager
│   └── routers/
│       ├── streams.py      # Stream CRUD REST API
│       └── webrtc.py       # WebRTC signaling proxy
├── static/
│   ├── index.html          # Web UI
│   ├── css/style.css       # Dark theme + responsive grid
│   └── js/
│       ├── app.js          # Grid rendering + coordination
│       ├── webrtc-player.js# WebRTC player component
│       └── settings.js     # Settings panel logic
└── bin/                    # go2rtc binary (auto-downloaded)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web UI |
| `GET` | `/api/streams` | List all configured streams |
| `POST` | `/api/streams` | Add a new stream |
| `PUT` | `/api/streams/{id}` | Update a stream |
| `DELETE` | `/api/streams/{id}` | Remove a stream |
| `POST` | `/api/webrtc?src={id}` | WebRTC signaling (SDP exchange) |

## Troubleshooting

**"go2rtc binary not found"**
Run `python setup_go2rtc.py` to download it. The binary is placed in the `bin/` directory.

**Streams show "error" status**
- Verify the RTSP URL is correct and accessible from the host machine
- Test with VLC: `vlc rtsp://user:pass@camera-ip:554/stream`
- Check that the camera is on the same network as the server

**Video not playing in browser**
- WebRTC requires a secure context or localhost. If accessing from another machine, the browser may block WebRTC on plain HTTP. Access via `localhost` or set up HTTPS.
- Check browser console for errors

**Port conflicts**
- Change `app.port` (default 8000) or `app.go2rtc_port` (default 1984) in `config.yaml` if those ports are already in use

## License

MIT
