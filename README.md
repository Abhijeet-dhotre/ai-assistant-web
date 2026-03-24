# AI Voice Assistant

A real-time voice assistant that listens, thinks, and speaks back — powered by Whisper, Groq, and Pocket TTS with WebSocket streaming.

## Architecture

```
Microphone / Audio File
        |
        v
  ┌─────────────┐
  │  WebSocket   │  (Frontend ↔ ws_server.py)
  │  Connection  │
  └──────┬──────┘
         |
    ┌────▼────┐     ┌──────────┐     ┌────────────┐
    │ Whisper  │ ──► │  Groq    │ ──► │ Pocket TTS │
    │ (STT)    │     │  (LLM)   │     │ (Speech)   │
    └─────────┘     └──────────┘     └────────────┘
         |               |                   |
    Transcription   Streaming tokens    Audio chunks
         |               |                   |
         └───────────────┼───────────────────┘
                         v
                  Browser plays audio
                   as it streams in
```

## Features

- **Real-time streaming** — LLM tokens stream word-by-word, TTS audio plays sentence-by-sentence
- **WebSocket pipeline** — single persistent connection, zero HTTP overhead
- **Sentence pipelining** — TTS starts on each complete sentence while the LLM is still generating
- **Audio queue** — browser auto-plays TTS chunks in order
- **Voice recording** — record directly from the browser microphone
- **File upload** — upload audio files if mic isn't available
- **Drag & drop** — drop audio files onto the page
- **Chat history** — conversation view with transcription and AI responses

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
- [FFmpeg](https://ffmpeg.org/download.html) (for audio conversion)
- Groq API key — get one free at [console.groq.com](https://console.groq.com)

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Abhijeet-dhotre/ai-assistant-web.git
cd ai-assistant-web
```

### 2. Set your Groq API key

```bash
# Option A: Environment variable
export GROQ_API_KEY="your_groq_api_key_here"

# Option B: Create a .env file
cp .env.example .env
# then edit .env and paste your key
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Run everything

**Windows:**
```batch
run.bat
```

**Manual (any OS):**

```bash
# Terminal 1 — Pocket TTS
uvx pocket-tts serve --voice alba

# Terminal 2 — WebSocket server
python ws_server.py

# Terminal 3 — Flask server
python server.py
```

Then open [http://localhost:5050](http://localhost:5050) in your browser.

### Stop

**Windows:**
```batch
stop.bat
```

**Manual:** `Ctrl+C` in each terminal.

## Configuration

### Pocket TTS Voice

Edit the `--voice` flag in `run.bat` or the serve command. Available voices:

| Voice | Gender | Style |
|-------|--------|-------|
| `alba` | Female | Casual |
| `marius` | Male | Reading |
| `javert` | Male | Reading |
| `jean` | Male | Reading |
| `fantine` | Female | Reading |
| `cosette` | Female | Reading |
| `eponine` | Female | Reading |
| `azelma` | Female | Reading |

You can also pass a path to a `.wav` file for voice cloning.

### Groq Model

Edit `GROQ_MODEL` in `server.py` and `ws_server.py`. Available models:

- `llama-3.3-70b-versatile` (default, best quality)
- `llama-3.1-8b-instant` (faster, lower quality)
- `mixtral-8x7b-32768`

### GPU Acceleration

Set the environment variable before running:

```bash
export USE_GPU=true
```

## API Endpoints

### Flask Server (port 5050)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serves the frontend |
| GET | `/audio/<filename>` | Serves generated audio files |
| GET | `/health` | Server health check |
| POST | `/upload` | HTTP audio upload (legacy, non-streaming) |

### WebSocket Server (port 5051)

| Path | Description |
|------|-------------|
| `ws://localhost:5051/ws` | Real-time audio processing pipeline |

**WebSocket message flow:**

```
Client → Server:  binary audio data (WAV/WebM)
Server → Client:  {"type": "status", "stage": "stt", "message": "Transcribing..."}
Server → Client:  {"type": "transcription", "text": "Hello"}
Server → Client:  {"type": "status", "stage": "llm", "message": "Thinking..."}
Server → Client:  {"type": "llm_token", "token": "Hey"}
Server → Client:  {"type": "llm_token", "token": " there"}
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
│   └── index.html       # Frontend (single-page app)
├── requirements.txt     # Python dependencies
├── run.bat              # Start everything (Windows)
├── stop.bat             # Kill all servers (Windows)
├── .env.example         # Example environment variables
└── .gitignore
```

## Troubleshooting

**Microphone not working:**
- Browsers require HTTPS or `localhost` for mic access
- If accessing from another device on the network, use the upload button instead

**Pocket TTS 404 error:**
- Make sure Pocket TTS is running: `uvx pocket-tts serve --voice alba`
- Check that port 8000 is not blocked

**Groq API error:**
- Verify your API key is set: `echo %GROQ_API_KEY%` (Windows) or `echo $GROQ_API_KEY` (Linux/Mac)
- Check your rate limits at [console.groq.com](https://console.groq.com)

**FFmpeg not found:**
- Install FFmpeg and add it to your PATH: [ffmpeg.org](https://ffmpeg.org/download.html)

## License

MIT
