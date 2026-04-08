from pathlib import Path
import json
from typing import Any

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import requests
import os
import dotenv

dotenv.load_dotenv()

app = FastAPI(title="Ollama WAN Gateway")

# Configuration
BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"
OLLAMA_URL = "http://localhost:11434/api/generate"
API_KEY = os.getenv("API_KEY")
MODEL_NAME = "qwen2.5:7b"
api_key_header = APIKeyHeader(name="X-API-Key")

app.mount("/static", StaticFiles(directory=UI_DIR / "static"), name="static")


class ChatRequest(BaseModel):
    prompt: str = Field(..., description="User prompt to send to the Ollama model.")


class EndpointDescriptor(BaseModel):
    path: str
    method: str
    description: str
    auth: str
    request_format: dict[str, Any]
    response_format: dict[str, Any]


class ApiCatalogResponse(BaseModel):
    service: str
    model: str
    endpoints: list[EndpointDescriptor]

def validate_api_key(key: str = Depends(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid API Key")
    return key

# --- CHAT UI ENDPOINT ---
@app.get("/ui")
@app.get("/v1/ui")
async def get_ui():
    return FileResponse(
        UI_DIR / "index.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )

@app.get("/v1/apis", response_model=ApiCatalogResponse)
@app.get("/v1/info", response_model=ApiCatalogResponse)
async def get_api_info():
    return ApiCatalogResponse(
        service="Ollama WAN Gateway",
        model=MODEL_NAME,
        endpoints=[
            EndpointDescriptor(
                path="/ui",
                method="GET",
                description="Browser chat interface.",
                auth="No API header required. The UI prompts for an API key and uses it for chat requests.",
                request_format={
                    "content_type": "text/html",
                    "body": None,
                },
                response_format={
                    "content_type": "text/html",
                    "body": "Chat UI page",
                },
            ),
            EndpointDescriptor(
                path="/v1/ui",
                method="GET",
                description="Alias for the browser chat interface.",
                auth="No API header required. The UI prompts for an API key and uses it for chat requests.",
                request_format={
                    "content_type": "text/html",
                    "body": None,
                },
                response_format={
                    "content_type": "text/html",
                    "body": "Chat UI page",
                },
            ),
            EndpointDescriptor(
                path="/v1/chat",
                method="POST",
                description="Sends a prompt to Ollama and returns the non-streaming generate response.",
                auth="Required header: X-API-Key",
                request_format={
                    "content_type": "application/json",
                    "body": {
                        "prompt": "string"
                    },
                },
                response_format={
                    "content_type": "application/json",
                    "body": {
                        "model": "string",
                        "created_at": "string",
                        "response": "string",
                        "done": "boolean",
                        "context": ["integer"],
                        "total_duration": "integer",
                        "load_duration": "integer",
                        "prompt_eval_count": "integer",
                        "eval_count": "integer"
                    },
                    "notes": "Exact fields depend on Ollama's /api/generate response.",
                },
            ),
            EndpointDescriptor(
                path="/v1/chat/stream",
                method="POST",
                description="Sends a prompt to Ollama and streams generated text back incrementally.",
                auth="Required header: X-API-Key",
                request_format={
                    "content_type": "application/json",
                    "body": {
                        "prompt": "string"
                    },
                },
                response_format={
                    "content_type": "text/event-stream",
                    "events": [
                        {
                            "event": "message",
                            "data": {
                                "text": "partial generated text"
                            },
                        },
                        {
                            "event": "done",
                            "data": {},
                        },
                        {
                            "event": "error",
                            "data": {
                                "message": "error details"
                            },
                        },
                    ],
                },
            ),
            EndpointDescriptor(
                path="/v1/apis",
                method="GET",
                description="Returns this API catalog.",
                auth="No API header required.",
                request_format={
                    "content_type": "application/json",
                    "body": None,
                },
                response_format={
                    "content_type": "application/json",
                    "body": "API catalog",
                },
            ),
            EndpointDescriptor(
                path="/v1/info",
                method="GET",
                description="Alias for the API catalog endpoint.",
                auth="No API header required.",
                request_format={
                    "content_type": "application/json",
                    "body": None,
                },
                response_format={
                    "content_type": "application/json",
                    "body": "API catalog",
                },
            ),
        ],
    )

# --- EXISTING API ENDPOINT ---
@app.post("/v1/chat")
async def chat_qwen(user_data: ChatRequest, _=Depends(validate_api_key)):
    payload = {
        "model": MODEL_NAME,
        "prompt": user_data.prompt,
        "stream": False 
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ollama Error: {str(e)}")

@app.post("/v1/chat/stream")
async def chat_qwen_stream(user_data: ChatRequest, _=Depends(validate_api_key)):
    payload = {
        "model": MODEL_NAME,
        "prompt": user_data.prompt,
        "stream": True
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, stream=True)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ollama Error: {str(e)}")

    def generate():
        try:
            for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                if not line:
                    continue

                chunk = json.loads(line)
                text = chunk.get("response", "")
                if text:
                    yield f"data: {json.dumps({'text': text})}\n\n"
            yield "event: done\ndata: {}\n\n"
        except requests.exceptions.RequestException as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
        finally:
            response.close()

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(generate(), media_type="text/event-stream", headers=headers)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
