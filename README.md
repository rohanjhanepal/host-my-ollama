# Ollama Qwen Tunnel

A small FastAPI gateway that sits in front of a local Ollama instance and exposes:

- a protected chat API
- a streaming chat API for live UI responses
- a simple browser chat UI
- a discovery endpoint that lists the available APIs and their request/response formats

This project currently proxies requests to Ollama's `generate` API at `http://localhost:11434/api/generate` and uses the `qwen2.5:7b` model.

## Features

- API key protection using the `X-API-Key` header
- Web UI at `/ui`
- Non-streaming chat endpoint
- Streaming SSE chat endpoint
- API catalog endpoint for integration discovery
- Static HTML/CSS UI served by FastAPI

## Requirements

- Python 3.10+
- Ollama installed and running locally
- The target Ollama model pulled locally

Example:

```powershell
ollama pull qwen2.5:7b
ollama serve
```

## Setup

1. Clone the repository.
2. Create a virtual environment.
3. Install the Python dependencies.
4. Create your `.env` file.
5. Start the server.

### 1. Create a virtual environment

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install fastapi uvicorn requests python-dotenv
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and set your own key:

```env
API_KEY=your_secure_api_key_here
```

## Run the app

```powershell
py -3 main.py
```

The server starts on:

```text
http://localhost:8000
```

## Available Endpoints

### UI

- `GET /ui`
- `GET /v1/ui`

Opens the browser chat UI. The page asks for your API key and stores it in local storage for chat requests.

### API catalog

- `GET /v1/apis`
- `GET /v1/info`

Returns a JSON summary of the available endpoints, auth requirements, and request/response shapes.

Example:

```powershell
curl http://localhost:8000/v1/info
```

### Chat

- `POST /v1/chat`

Headers:

```http
X-API-Key: your_secure_api_key_here
Content-Type: application/json
```

Request body:

```json
{
  "prompt": "Write a short poem about the ocean."
}
```

Response:

```json
{
  "model": "qwen2.5:7b",
  "created_at": "2026-04-08T10:00:00Z",
  "response": "The ocean whispers...",
  "done": true
}
```

Note: the exact JSON fields come from Ollama's `/api/generate` response.

### Streaming chat

- `POST /v1/chat/stream`

Headers:

```http
X-API-Key: your_secure_api_key_here
Content-Type: application/json
Accept: text/event-stream
```

Request body:

```json
{
  "prompt": "Explain photosynthesis simply."
}
```

Response type:

```text
text/event-stream
```

Example stream events:

```text
data: {"text":"Photo"}

data: {"text":"synthesis "}

event: done
data: {}
```

## Example Requests

### PowerShell

```powershell
$headers = @{
  "X-API-Key" = "your_secure_api_key_here"
  "Content-Type" = "application/json"
}

$body = @{
  prompt = "Tell me a fun fact about Saturn."
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/chat" `
  -Headers $headers `
  -Body $body
```

### cURL

```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "X-API-Key: your_secure_api_key_here" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Hello from curl\"}"
```

## Project Structure

```text
.
|-- main.py
|-- .env
|-- .env.example
|-- .gitignore
|-- README.md
`-- ui
    |-- index.html
    `-- static
        `-- ui.css
```

## Configuration Notes

These values are currently defined directly in `main.py`:

- `OLLAMA_URL = "http://localhost:11434/api/generate"`
- `MODEL_NAME = "qwen2.5:7b"`

If you want to point to a different Ollama host or model, update those values in [`main.py`](main.py).

## Security Notes

- Do not commit your real `.env` file.
- Use a strong API key before exposing this app outside your local machine.
- The UI stores the API key in browser local storage for convenience.

## Troubleshooting

### `403 Unauthorized`

- Make sure the `X-API-Key` header matches the value in `.env`.

### `500 Ollama Error`

- Confirm Ollama is running.
- Confirm `qwen2.5:7b` is installed locally.
- Confirm Ollama is reachable at `http://localhost:11434`.

### UI loads but responses do not work

- Check that Ollama is running.
- Hard refresh the browser so the newest UI JavaScript is loaded.
- Confirm the API key was entered correctly in the UI.

## Next improvements

- Move `OLLAMA_URL` and `MODEL_NAME` into environment variables
- Add a `requirements.txt` or `pyproject.toml`
- Add request logging and health checks
- Add tests for the chat and streaming endpoints
