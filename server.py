import os
import time
import logging
import subprocess
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_file, send_from_directory
from faster_whisper import WhisperModel

# ================= CONFIG =================

# Pocket TTS (local server, run separately: uvx pocket-tts serve --voice alba)
# Voice is set at pocket-tts startup, not per request
POCKET_TTS_URL = "http://localhost:8000/tts"

# Groq API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

WHISPER_SIZE = "base.en"
DEVICE = "cuda" if os.getenv("USE_GPU") == "true" else "cpu"

# ===============================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static")

print(f"Loading Whisper model '{WHISPER_SIZE}' on {DEVICE}...")
asr_model = WhisperModel(WHISPER_SIZE, device=DEVICE, compute_type="int8")
print("Whisper Loaded!")

ROBOT_SYSTEM_PROMPT = (
    "You are a close friend having a casual voice chat. "
    "Talk naturally like a real person — use contractions, "
    "slang, and a warm tone. Keep responses to 1-2 sentences max. "
    "Be witty, a little funny, and real. No emojis or robotic phrases. "
    "Never say 'as an assistant' or 'I am a robot'."
)

# ================= ROUTES =================


@app.route("/")
def root():
    return send_from_directory("static", "index.html")


@app.route("/upload", methods=["POST"])
def upload():
    start_time = time.time()

    if "audio" not in request.files:
        return jsonify({"error": "No audio file"}), 400

    audio_file = request.files["audio"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    os.makedirs("mic_input", exist_ok=True)
    os.makedirs("audio_responses", exist_ok=True)

    input_wav = f"mic_input/req_{timestamp}.wav"
    output_wav = f"audio_responses/resp_{timestamp}.wav"

    audio_file.save(input_wav)

    try:
        # ---------- STT ----------
        print("Transcribing...")
        segments, _ = asr_model.transcribe(input_wav, beam_size=5)
        user_text = " ".join(seg.text for seg in segments).strip()

        if not user_text:
            return jsonify({"error": "No speech detected"}), 400

        print(f"User: {user_text}")

        # ---------- LLM (Groq) ----------
        print("Thinking...")
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": ROBOT_SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
        }

        r = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=120)

        ai_text = "I am not sure."
        if r.status_code == 200:
            ai_text = r.json()["choices"][0]["message"]["content"].strip()
        else:
            logger.error(f"Groq API error {r.status_code}: {r.text}")

        print(f"AI: {ai_text}")

        # ---------- TTS (Pocket TTS) ----------
        audio_ok = generate_pocket_tts(ai_text, output_wav)

        total_time = time.time() - start_time
        print(f"Total Latency: {total_time:.2f}s")

        return jsonify(
            {
                "user_text": user_text,
                "ai_response": ai_text,
                "has_audio": audio_ok,
                "audio_url": f"/audio/resp_{timestamp}.wav" if audio_ok else None,
            }
        )

    except Exception as e:
        logger.error(e)
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# ================= TTS =================


def generate_pocket_tts(text, output_path):
    try:
        print("Sending to Pocket TTS...")
        response = requests.post(
            POCKET_TTS_URL,
            data={"text": text},
            timeout=120,
        )

        if response.status_code != 200:
            print(f"Pocket TTS Error {response.status_code}: {response.text}")
            return False

        temp_raw = output_path.replace(".wav", "_raw.wav")
        with open(temp_raw, "wb") as f:
            f.write(response.content)

        # Convert to 16kHz mono
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                temp_raw,
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

        if os.path.exists(temp_raw):
            os.remove(temp_raw)

        print("Audio Ready")
        return True

    except Exception as e:
        print(f"Pocket TTS failed: {e}")
        return False


# ================= AUDIO SERVE =================


@app.route("/audio/<filename>")
def serve_audio(filename):
    return send_file(f"audio_responses/{filename}", mimetype="audio/wav")


# ================= MAIN =================

if __name__ == "__main__":
    print("Server running on port 5050")
    app.run(host="0.0.0.0", port=5050)
