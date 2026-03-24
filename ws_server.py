import os
import re
import base64
import asyncio
import logging
import tempfile
import subprocess

import requests
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel

# ================= CONFIG =================

POCKET_TTS_URL = "http://localhost:8000/tts"

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

WHISPER_SIZE = "base.en"
DEVICE = "cuda" if os.getenv("USE_GPU") == "true" else "cpu"

# ===============================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ws_server")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("audio_responses", exist_ok=True)

print(f"[WS] Loading Whisper '{WHISPER_SIZE}' on {DEVICE}...")
asr_model = WhisperModel(WHISPER_SIZE, device=DEVICE, compute_type="int8")
print("[WS] Whisper loaded!")

SYSTEM_PROMPT = (
    "You are a close friend having a casual voice chat. "
    "Talk naturally like a real person - use contractions, "
    "slang, and a warm tone."
    "Be witty, a little funny, and real. No emojis or robotic phrases. "
    "Never say 'as an assistant' or 'I am a robot'."
)

SENTENCE_RE = re.compile(r"([^.!?]*[.!?])")


# ================= HELPERS =================


def pocket_tts(text: str, output_path: str) -> bool:
    resp = requests.post(POCKET_TTS_URL, data={"text": text}, timeout=120)
    if resp.status_code != 200:
        logger.error("Pocket TTS %s: %s", resp.status_code, resp.text)
        return False

    raw_path = output_path.replace(".wav", "_raw.wav")
    with open(raw_path, "wb") as f:
        f.write(resp.content)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            raw_path,
            "-ar",
            "16000",
            "-ac",
            "1",
            "-sample_fmt",
            "s16",
            output_path,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.remove(raw_path)
    return True


def read_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ================= WEBSOCKET =================


import json as _json
from datetime import datetime as _dt


@app.websocket("/ws")
async def ws_handler(ws: WebSocket):
    await ws.accept()
    logger.info("Client connected")

    try:
        while True:
            raw = await ws.receive_bytes()

            ts = _dt.now().strftime("%Y%m%d_%H%M%S_%f")

            # ---- save WAV audio (already PCM-encoded by browser) ----
            tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
            with open(tmp_wav, "wb") as f:
                f.write(raw)

            await ws.send_json(
                {"type": "status", "stage": "stt", "message": "Transcribing..."}
            )

            # ---- STT ----
            try:
                segments, _ = asr_model.transcribe(tmp_wav, beam_size=5)
                user_text = " ".join(s.text for s in segments).strip()
            except Exception as e:
                logger.error("STT error: %s", e)
                await ws.send_json({"type": "error", "message": f"STT failed: {e}"})
                os.unlink(tmp_wav)
                continue

            if not user_text:
                await ws.send_json({"type": "error", "message": "No speech detected"})
                os.unlink(tmp_wav)
                continue

            await ws.send_json({"type": "transcription", "text": user_text})
            await ws.send_json(
                {"type": "status", "stage": "llm", "message": "Thinking..."}
            )

            # ---- Groq streaming LLM ----
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text},
                ],
                "stream": True,
            }

            full_text = ""
            pending = ""
            idx = 0

            try:
                resp = requests.post(
                    GROQ_API_URL,
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=120,
                )

                for line in resp.iter_lines():
                    if not line:
                        continue
                    line = line.decode()
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break

                    chunk = _json.loads(data)
                    delta = chunk["choices"][0].get("delta", {}).get("content", "")
                    if not delta:
                        continue

                    full_text += delta
                    pending += delta

                    await ws.send_json({"type": "llm_token", "token": delta})

                    # ---- sentence pipeline ----
                    matches = list(SENTENCE_RE.finditer(pending))
                    for m in matches:
                        sentence = m.group(1).strip()
                        if len(sentence) < 4:
                            continue

                        await ws.send_json(
                            {
                                "type": "status",
                                "stage": "tts",
                                "message": f"Speaking part {idx + 1}...",
                            }
                        )

                        out = f"audio_responses/ws_{ts}_{idx}.wav"
                        loop = asyncio.get_event_loop()
                        ok = await loop.run_in_executor(None, pocket_tts, sentence, out)

                        if ok:
                            b64 = await loop.run_in_executor(None, read_base64, out)
                            await ws.send_json(
                                {
                                    "type": "tts_audio",
                                    "index": idx,
                                    "audio_base64": b64,
                                }
                            )
                            idx += 1

                    pending = SENTENCE_RE.sub("", pending)

            except Exception as e:
                logger.error("LLM error: %s", e)
                await ws.send_json({"type": "error", "message": f"LLM failed: {e}"})
                os.unlink(tmp_wav)
                continue

            # remaining text
            tail = pending.strip()
            if tail and len(tail) > 3:
                await ws.send_json(
                    {"type": "status", "stage": "tts", "message": "Speaking..."}
                )
                out = f"audio_responses/ws_{ts}_{idx}.wav"
                loop = asyncio.get_event_loop()
                ok = await loop.run_in_executor(None, pocket_tts, tail, out)
                if ok:
                    b64 = await loop.run_in_executor(None, read_base64, out)
                    await ws.send_json(
                        {"type": "tts_audio", "index": idx, "audio_base64": b64}
                    )

            await ws.send_json({"type": "done", "ai_response": full_text})
            os.unlink(tmp_wav)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.exception("WS error")


# ================= MAIN =================

if __name__ == "__main__":
    import uvicorn

    print("[WS] WebSocket server on port 5051")
    uvicorn.run(app, host="0.0.0.0", port=5051)
