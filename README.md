# EduGenie

A lightweight AI-powered educational assistant. FastAPI backend, Gemini AI
under the hood, single-page HTML/CSS/JS frontend, no build step required.

## Features

- **Ask** — question answering with extra context and related topics
- **Quiz me** — auto-generated multiple-choice self-assessment quizzes
- **Summarize** — condenses pasted text into a summary + key points
- **Learning path** — beginner → intermediate → advanced roadmap for any topic

The app runs in **demo mode** out of the box (canned example responses) so
you can try the full UI with zero setup. Add a Gemini API key to get live
AI-generated answers.

## Project structure

```
edugenie/
├── backend/
│   ├── main.py              FastAPI app + routes, serves the frontend
│   ├── gemini_service.py    Gemini API wrapper (with demo-mode fallback)
│   ├── models.py            Pydantic request/response schemas
│   ├── requirements.txt
│   └── .env.example         Copy to .env and add your key
└── frontend/
    ├── index.html
    ├── style.css
    └── script.js
```

## Setup

1. **Install Python 3.10+**, then create a virtual environment:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **(Optional) Add a Gemini API key** for live AI responses:
   - Get a free key at https://aistudio.google.com/app/apikey
   - Copy `.env.example` to `.env` and paste your key in:
     ```
     GEMINI_API_KEY=your_key_here
     ```
   - Without a key, the app still runs fully in demo mode.

4. **Run the server**:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

5. Open **http://127.0.0.1:8000** in your browser. The frontend is served
   directly by FastAPI — no separate frontend server needed.

## API reference

| Method | Path                | Purpose                          |
|--------|---------------------|-----------------------------------|
| GET    | `/api/health`        | Health check + demo-mode status  |
| POST   | `/api/ask`            | Ask a question                   |
| POST   | `/api/quiz`           | Generate a quiz                  |
| POST   | `/api/summarize`      | Summarize text                   |
| POST   | `/api/learning-path`  | Build a learning roadmap         |

Interactive API docs (Swagger UI) are available at `/docs` once the server
is running.

## Notes on the architecture

- `gemini_service.py` centralizes all AI calls. If `GEMINI_API_KEY` is unset,
  every route returns realistic demo data instead of calling out to Gemini —
  useful for frontend development, demos, and offline testing.
- Responses are requested from Gemini as strict JSON
  (`response_mime_type: application/json`) and parsed directly into the
  Pydantic response models, so the API contract stays stable regardless of
  demo vs. live mode.
- The frontend is vanilla HTML/CSS/JS — no build tooling — so it's easy to
  read, modify, and deploy anywhere that can serve static files.

## Next steps / ideas

- Add a lightweight local model (e.g. via `llama.cpp` or `ollama`) as a
  second fallback tier between "demo mode" and "Gemini" for fully offline use
  on constrained devices like an M1 Mac.
- Persist quiz results and learning-path progress in SQLite for the
  "personalized" part of personalized learning.
- Add user accounts if multiple students/educators need separate histories.
