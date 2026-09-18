/**
 * Shared frontend configuration.
 *
 * The backend (Backend/main.py) runs on http://127.0.0.1:8000 by default
 * (uvicorn main:app --reload --port 8000). Override API_BASE_URL here if
 * you run the API somewhere else (a different port, a deployed host, etc).
 */
window.API_BASE_URL = "http://127.0.0.1:8000";
