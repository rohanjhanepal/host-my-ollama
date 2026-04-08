# Ollama Qwen Tunnel

A FastAPI gateway that acts as a secure gatekeeper for a local Ollama instance. It adds API key authentication, a browser chat UI, streaming responses, and a simple API discovery endpoint so you can safely expose your home-hosted `qwen2.5:7b` model through Cloudflare Tunnel.

This project currently proxies requests to Ollama's `generate` API at `http://localhost:11434/api/generate`, serves FastAPI on `http://0.0.0.0:5002`, and is set up to be published at `https://qwen.rohanjha.com.np`.

## Features

- API key protection using the `X-API-Key` header
- Browser chat UI at `/ui` and `/v1/ui`
- Standard JSON chat endpoint at `/v1/chat`
- Streaming SSE chat endpoint at `/v1/chat/stream`
- API catalog endpoint at `/v1/info` and `/v1/apis`
- WAN-friendly deployment via Cloudflare Tunnel
- Headless process management with PM2

## Requirements

- Python 3.10+
- Ollama installed locally
- `qwen2.5:7b` pulled in Ollama
- Node.js and npm for PM2
- `cloudflared` installed for tunnel access

## Setup

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
API_KEY=your_super_secure_key_here
```

You can also copy from `.env.example` and update the value.

### 4. Prepare Ollama

```powershell
ollama pull qwen2.5:7b
ollama serve
```

## Local Run

To run the gateway directly:

```powershell
py -3 main.py
```

The FastAPI app listens on:

```text
http://localhost:5002
```

## Running In The Background With PM2

To keep the gateway running without an open terminal window:

### 1. Install PM2

```powershell
npm install -g pm2
```

### 2. Start the gateway

```powershell
pm2 start main.py --interpreter python --name "qwen-gateway"
```

### 3. Save the PM2 process list

```powershell
pm2 save
```

Useful PM2 commands:

```powershell
pm2 list
pm2 logs qwen-gateway
pm2 restart qwen-gateway
pm2 stop qwen-gateway
```

## Cloudflare Tunnel Setup

This project is configured to expose the gateway at:

```text
https://qwen.rohanjha.com.np
```

The current tunnel routing points that hostname to:

```text
http://localhost:5002
```

### 1. Create and route the tunnel

```powershell
cloudflared tunnel login
cloudflared tunnel create qwen-tunnel
cloudflared tunnel route dns qwen-tunnel qwen.rohanjha.com.np
```

### 2. Example `config.yml`

Your working tunnel config matches this pattern:

```yaml
tunnel: <your-tunnel-id>
credentials-file: C:\Users\RJ\.cloudflared\<your-tunnel-id>.json

ingress:
  - hostname: qwen.rohanjha.com.np
    service: http://localhost:5002
  - service: http_status:404
```

### 3. Install the tunnel as a Windows service

For `cloudflared service install`, make sure the service account can see the config and credentials. On Windows that usually means placing `config.yml` and the tunnel credentials JSON under:

```text
C:\Windows\System32\config\systemprofile\.cloudflared\
```

Then install and start the service:

```powershell
cloudflared service install
sc start cloudflared
```

## API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/ui` | `GET` | Browser chat interface |
| `/v1/ui` | `GET` | Alias for the browser chat interface |
| `/v1/info` | `GET` | API catalog and request/response shapes |
| `/v1/apis` | `GET` | Alias for the API catalog |
| `/v1/chat` | `POST` | Standard JSON chat response |
| `/v1/chat/stream` | `POST` | SSE streaming chat response |

## API Usage

### Authentication

Protected endpoints require:

```http
X-API-Key: your_super_secure_key_here
```

### Request format

Both chat endpoints expect:

```json
{
  "prompt": "Hello Qwen!"
}
```

### `POST /v1/chat`

Returns a regular JSON response from Ollama's `generate` API.

Example:

```bash
curl -X POST https://qwen.rohanjha.com.np/v1/chat \
  -H "X-API-Key: your_super_secure_key_here" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Hello Qwen!\"}"
```

Typical response:

```json
{
  "model": "qwen2.5:7b",
  "created_at": "2026-04-08T10:00:00Z",
  "response": "Hello! How can I help?",
  "done": true
}
```

### `POST /v1/chat/stream`

Returns `text/event-stream` and emits incremental response chunks.

Example event stream:

```text
data: {"text":"Hello "}

data: {"text":"from Qwen"}

event: done
data: {}
```

### `GET /v1/info`

Returns a machine-readable catalog of available endpoints and their request/response formats.

Example:

```powershell
curl https://qwen.rohanjha.com.np/v1/info
```

## Web UI

Open the browser UI at:

```text
https://qwen.rohanjha.com.np/ui
```

or locally:

```text
http://localhost:5002/ui
```

The UI will prompt for your API key and store it in browser local storage for subsequent chat requests.

## Project Structure

```text
.
|-- main.py
|-- .env
|-- .env.example
|-- .gitignore
|-- requirements.txt
|-- README.md
`-- ui
    |-- index.html
    `-- static
        `-- ui.css
```

## Configuration Notes

These values are currently set in [`main.py`](main.py):

- `OLLAMA_URL = "http://localhost:11434/api/generate"`
- `MODEL_NAME = "qwen2.5:7b"`
- FastAPI host: `0.0.0.0`
- FastAPI port: `5002`

If you want to change the Ollama host, model, or public port target, update those values and your Cloudflare tunnel config together.

## Security Notes

- Keep Ollama bound to localhost and do not expose it directly to the internet.
- Do not commit your real `.env` file.
- Use a strong API key before exposing this gateway publicly.
- The browser UI stores the API key in local storage for convenience.
- Cloudflare Tunnel usually removes the need to open inbound router ports.

## Troubleshooting

### Cloudflare `1033`

The tunnel service is down or unreachable. Try:

```powershell
sc start cloudflared
```

### `502 Bad Gateway`

The tunnel is up, but the FastAPI app is not responding. Check PM2:

```powershell
pm2 restart qwen-gateway
pm2 logs qwen-gateway
```

### `403 Forbidden`

The supplied `X-API-Key` does not match the value in `.env`.

### `500 Ollama Error`

- Confirm Ollama is running.
- Confirm `qwen2.5:7b` is installed locally.
- Confirm Ollama is reachable at `http://localhost:11434`.

### UI loads but replies do not stream

- Hard refresh the browser to pick up the latest UI JavaScript.
- Check PM2 logs for the FastAPI process.
- Confirm Ollama is generating responses locally.

## Next Improvements

- Move `OLLAMA_URL` and `MODEL_NAME` into environment variables
- Add a `pyproject.toml`
- Add request logging and health checks
- Add tests for the chat and streaming endpoints
