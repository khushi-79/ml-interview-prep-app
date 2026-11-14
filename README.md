# ML Interview Prep App

A portfolio project — an AI-powered ML interview coach built with Flask + Claude API.

## Project Structure
```
ml-prep-app/
├── backend/
│   ├── app.py              ← Flask server + Claude API integration
│   ├── requirements.txt
│   └── .env                ← API key (never commit this)
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── README.md
```

## Setup

```bash
# 1. Go to backend
cd backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your API key to .env
# Edit .env and replace "your_api_key_here" with your real key

# 4. Run the server
python app.py
```

## API Endpoints

| Method | Endpoint   | What it does                        |
|--------|------------|-------------------------------------|
| GET    | /health    | Check if server is running          |
| POST   | /chat      | Send a message, get Claude's reply  |
| GET    | /history   | Fetch full conversation history     |
| POST   | /clear     | Wipe history, start fresh session   |

## Version Roadmap
- **v1** — AI Chatbot (current)
- **v2** — Quiz generator
- **v3** — Music genre classifier
- **v4** — Trained ML models
