# =============================================================
# ML Interview Prep App — Backend (Streaming, fixed)
# =============================================================

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

MODEL_NAME       = "gemini-3.8-flash"
HISTORY_FILE     = "conversation_history.json"
MAX_HISTORY_PAIRS = 10

SYSTEM_PROMPT = """You are an expert ML interview coach helping someone with 2 years of 
experience prepare for machine learning engineering interviews.

The user already understands: forward pass, backprop, chain rule, matrix shapes, 
vanishing gradients, ReLU vs Sigmoid, loss functions, gradient descent, training loops.
Do NOT re-explain these basics unless specifically asked.

Your job:
1. EXPLAIN — Give clear, concise explanations of ML concepts. Use analogies, 
   but don't be patronizing. The user is smart.
2. QUIZ — When asked, generate interview-style questions, then evaluate their answers 
   with specific feedback (what was right, what was missing, what to study).
3. GUIDE — When asked "what should I study next", identify weak areas from the 
   conversation and suggest a prioritized study plan.

Style rules:
- Short paragraphs. No walls of text.
- Use bullet points for lists.
- If explaining math, show the equation AND the intuition behind it.
- Be direct. Skip filler phrases like "Great question!".
- When you ask a quiz question, wait for the user's answer before giving the answer.
"""


# ── HELPERS ──────────────────────────────────────────────────

def load_history():
    """
    Load, sanitize, and trim history.
    Returns Gemini-formatted messages: [{role, parts:[{text}]}, ...]
    
    Key rule: history must strictly alternate user/model.
    Trailing user message is dropped (we add it via generate_content).
    """
    if not os.path.exists(HISTORY_FILE):
        return []

    with open(HISTORY_FILE, "r") as f:
        data = json.load(f)

    raw = []
    for msg in data:
        role = "model" if msg["role"] == "assistant" else msg["role"]
        raw.append({"role": role, "parts": [{"text": msg["content"]}]})

    # Enforce strict alternation
    sanitized = []
    for msg in raw:
        if not sanitized:
            if msg["role"] == "user":
                sanitized.append(msg)
        else:
            if msg["role"] != sanitized[-1]["role"]:
                sanitized.append(msg)
            else:
                sanitized[-1] = msg

    # Drop trailing user message
    if sanitized and sanitized[-1]["role"] == "user":
        sanitized.pop()

    # Trim to last N pairs
    max_items = MAX_HISTORY_PAIRS * 2
    return sanitized[-max_items:] if len(sanitized) > max_items else sanitized


def save_turn(user_content, assistant_content):
    """
    Save a completed (user, assistant) turn together.
    Saving atomically ensures conversation_history.json never has
    orphaned or consecutive user messages if an API call fails mid-way.
    """
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            raw = json.load(f)
    else:
        raw = []

    now = datetime.now().isoformat()
    raw.append({
        "role": "user",
        "content": user_content,
        "timestamp": now
    })
    raw.append({
        "role": "assistant",
        "content": assistant_content,
        "timestamp": now
    })

    with open(HISTORY_FILE, "w") as f:
        json.dump(raw, f, indent=2)


# ── ROUTES ───────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    def generate_stream():
        full_reply = []
        try:
            model = genai.GenerativeModel(
                model_name=MODEL_NAME,
                system_instruction=SYSTEM_PROMPT
            )

            history = load_history()

            # Build full conversation: prior history + current user message
            contents = history + [{"role": "user", "parts": [{"text": user_message}]}]

            # Stream response tokens
            response = model.generate_content(contents, stream=True)

            for chunk in response:
                text = ""
                try:
                    text = chunk.text
                except Exception:
                    continue

                if text:
                    full_reply.append(text)
                    payload = json.dumps({"chunk": text})
                    yield f"data: {payload}\n\n"

            # Save the completed turn only when we got a valid response
            if full_reply:
                complete_text = "".join(full_reply)
                save_turn(user_message, complete_text)
            else:
                yield f"data: {json.dumps({'error': 'Gemini returned an empty response. Try rephrasing.'})}\n\n"

        except Exception as e:
            error_str = str(e)
            print(f"Gemini API error: {error_str}")

            if "api key" in error_str.lower() or "API_KEY" in error_str:
                msg = "Invalid API key. Check your .env file."
            elif "quota" in error_str.lower() or "429" in error_str:
                msg = "Rate limit hit. Wait a moment and try again."
            elif "not found" in error_str.lower() or "404" in error_str:
                msg = f"Model '{MODEL_NAME}' not found. Check the model name in app.py."
            else:
                msg = f"Error: {error_str[:120]}"

            yield f"data: {json.dumps({'error': msg})}\n\n"

        finally:
            # Always send [DONE] so the frontend's read loop terminates cleanly
            yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate_stream()),
        mimetype="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control":     "no-cache",
        }
    )


@app.route("/history", methods=["GET"])
def get_history():
    if not os.path.exists(HISTORY_FILE):
        return jsonify({"history": []})
    with open(HISTORY_FILE, "r") as f:
        raw = json.load(f)
    return jsonify({"history": raw})


@app.route("/clear", methods=["POST"])
def clear_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    return jsonify({"message": "History cleared."})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": MODEL_NAME})


if __name__ == "__main__":
    print("🚀 ML Interview Prep backend starting...")
    print(f"   Model: {MODEL_NAME}")
    print(f"   History window: last {MAX_HISTORY_PAIRS} pairs")
    print("   Health: http://localhost:5000/health")
    print()
    app.run(debug=True, port=5000)
