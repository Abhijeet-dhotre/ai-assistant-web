# AI Voice Assistant

A conversational voice assistant that listens continuously, thinks, and speaks back — powered by Whisper, Groq, and Pocket TTS with WebSocket streaming.

## How It Works

The assistant is **always listening**. Just speak naturally — it detects your voice, transcribes it, sends it to an LLM, and streams audio responses back in real time. If you start speaking while the assistant is talking, it **interrupts** itself and listens to you.

```
You speak  ──►  Energy Detection  ──►  Whisper (STT)  ──►  Groq (LLM)  ──►  Pocket TTS  ──►  Audio plays
                    │                                          │                    │
              silence detected                          streaming tokens     sentence-by-sentence
              after 800ms                               appear on screen     audio chunks
```

## Features

- **Always-on mic** — no button to press, detects speech automatically via energy-based VAD
- **Interrupt support** — start speaking while the assistant is talking and it stops immediately
- **Real-time streaming** — LLM text appears word-by-word, audio plays sentence-by-sentence
- **WebSocket pipeline** — single persistent connection, minimal latency
- **File upload** — upload audio files as an alternative to mic input
- **Raw PCM capture** — mic audio encoded to WAV in the browser, no ffmpeg needed
- **Debug console** — real-time log panel shows energy levels, state, and errors

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Speech-to-Text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (base.en) |
| LLM | [Groq API](https://console.groq.com) (llama-3.3-70b-versatile) |
| Text-to-Speech | [Pocket TTS](https://github.com/kyutai-labs/pocket-tts) (Kyutai, 100M params, CPU) |
| Backend | Flask (static files) + FastAPI (WebSocket) |
| Frontend | Vanilla HTML/CSS/JS |

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (for Pocket TTS)
- [FFmpeg](https://ffmpeg.org/download.html) (used by Pocket TTS internally)
- Groq API key — free at [console.groq.com](https://console.groq.com)

## Setup

### 1. Clone

```bash
git clone https://github.com/Abhijeet-dhotre/ai-assistant-web.git
cd ai-assistant-web
```

### 2. Set your Groq API key

```bash
# Option A: Environment variable
export GROQ_API_KEY="your_groq_api_key_here"

# Option B: .env file
cp .env.example .env
# edit .env and paste your key
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run

**Windows (one click):**
```batch
run.bat
```

This opens 3 windows: Pocket TTS, WebSocket server, Flask server. Then opens the browser.

**Manual (any OS):**
```bash
# Terminal 1 — Pocket TTS
uvx pocket-tts serve --voice alba

# Terminal 2 — WebSocket server
python ws_server.py

# Terminal 3 — Flask server
python server.py
```

Then open [http://localhost:5050](http://localhost:5050).

### Stop

**Windows:** `stop.bat`
**Manual:** `Ctrl+C` in each terminal.

## User Interface

The app has a single screen with:
- **Chat area** — shows transcription and AI responses
- **Debug log** — real-time status (energy, state, errors)
- **Mic orb** — color-coded status indicator:
  - 🟢 Green = listening
  - 🔴 Red = recording your speech
  - 🟠 Orange = processing (STT → LLM → TTS)
  - 🔵 Blue = speaking (click to interrupt)
- **Upload button** — send audio files instead of mic

## Configuration

### Voice Detection Sensitivity

Edit these constants in the `<script>` section of `static/index.html`:

| Constant | Default | Description |
|----------|---------|-------------|
| `ENERGY_THRESHOLD` | `0.01` | RMS level to trigger speech (lower = more sensitive) |
| `SILENCE_MS` | `800` | Milliseconds of silence to end speech |
| `MIN_SPEECH_MS` | `300` | Ignore utterances shorter than this |

### Pocket TTS Voice

Edit `--voice` in `run.bat`. Available voices: `alba`, `marius`, `javert`, `jean`, `fantine`, `cosette`, `eponine`, `azelma`. You can also pass a path to a `.wav` file for voice cloning.

### Groq Model

Edit `GROQ_MODEL` in `server.py` and `ws_server.py`:
- `llama-3.3-70b-versatile` — best quality (default)
- `llama-3.1-8b-instant` — faster, lower quality

### GPU Acceleration

For Whisper:
```bash
export USE_GPU=true
```

Pocket TTS is CPU-optimized by design and runs faster on CPU than GPU for single requests.

## API Endpoints

### Flask Server (port 5050)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serves the frontend |
| GET | `/health` | Server health check |
| POST | `/upload` | HTTP audio upload (non-streaming fallback) |

### WebSocket Server (port 5051)

| Path | Description |
|------|-------------|
| `ws://localhost:5051/ws` | Real-time audio pipeline |

**Message flow:**
```
Client → Server:  binary WAV data
Server → Client:  {"type": "status", "stage": "stt"}
Server → Client:  {"type": "transcription", "text": "Hello"}
Server → Client:  {"type": "llm_token", "token": "Hey"}
Server → Client:  {"type": "llm_token", "token": " there!"}
Server → Client:  {"type": "tts_audio", "index": 0, "audio_base64": "..."}
Server → Client:  {"type": "done", "ai_response": "Hey there!"}
```

### Pocket TTS Server (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tts` | Generate speech (form data: `text`) |
| GET | `/` | Web UI for testing |

## Project Structure

```
.
├── server.py            # Flask server (static files, HTTP fallback)
├── ws_server.py         # FastAPI WebSocket server (real-time pipeline)
├── static/
│   └── index.html       # Frontend (continuous mic, VAD, streaming UI)
├── requirements.txt     # Python dependencies
├── run.bat              # Start everything (Windows)
├── stop.bat             # Kill all servers (Windows)
├── .env.example         # Example environment variables
└── .gitignore
```

## Troubleshooting

**Mic not working:**
- Browsers require HTTPS or `localhost` for mic access
- Check the debug log at the bottom of the page
- Use the upload button if mic is unavailable

**No response after speaking:**
- Check the debug log — it shows energy levels and state changes
- Lower `ENERGY_THRESHOLD` if your mic is quiet
- Make sure Pocket TTS is running on port 8000

**Pocket TTS 404 error:**
- Ensure `uvx pocket-tts serve --voice alba` is running
- Check that port 8000 is not blocked

**Groq API error:**
- Verify your API key: `echo %GROQ_API_KEY%`
- Check rate limits at [console.groq.com](https://console.groq.com)

## License

MIT
