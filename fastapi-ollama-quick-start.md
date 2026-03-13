# FastAPI + Ollama Integration

## Quick Start Guide

## 2. Prerequisites Check

Before starting, verify your setup:

```bash
# 1. Check Ollama is running
curl http://localhost:11434/api/tags
# You should see llama3.2 in the models list

# 2. Quick test that the model responds
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [{"role": "user", "content": "Say hello in one word"}],
  "stream": false
}'

# 3. Verify your FastAPI app runs
# (You should already have this working)
```

> **Note:** Ollama's default port is `11434`. If you changed it, adjust the `OLLAMA_BASE_URL` in the code below.

---

## Step 1: Install Dependencies

We only need one new package — `httpx` for async HTTP calls:

```bash
pip install httpx
```

That's it. We're using:

| Package    | Purpose                      | Already Have?               |
| ---------- | ---------------------------- | --------------------------- |
| `fastapi`  | Web framework                | ✅ Yes                      |
| `uvicorn`  | ASGI server                  | ✅ Yes                      |
| `pydantic` | Request/response validation  | ✅ Yes (comes with FastAPI) |
| `httpx`    | Async HTTP client for Ollama | 🆕 Install now              |

---

## Step 2: Understand Ollama's API

Before writing any code, let's understand what Ollama expects and returns. Ollama exposes a REST API at `http://localhost:11434`. The endpoint we'll use is:

### `POST /api/chat`

**Request Body:**

```json
{
  "model": "llama3.2",
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user", "content": "What is Python?" },
    { "role": "assistant", "content": "Python is a programming language..." },
    { "role": "user", "content": "What about FastAPI?" }
  ],
  "stream": false
}
```

**Key fields:**

- `model` — which model to use
- `messages` — array of message objects with `role` and `content`
- `stream` — `false` for a single JSON response, `true` for newline-delimited JSON chunks

**Response (non-streaming):**

```json
{
  "model": "llama3.2",
  "message": {
    "role": "assistant",
    "content": "FastAPI is a modern web framework..."
  },
  "done": true,
  "total_duration": 1234567890
}
```

**Response (streaming):** Each line is a separate JSON object:

```
{"model":"llama3.2","message":{"role":"assistant","content":"Fast"},"done":false}
{"model":"llama3.2","message":{"role":"assistant","content":"API"},"done":false}
{"model":"llama3.2","message":{"role":"assistant","content":" is"},"done":false}
...
{"model":"llama3.2","message":{"role":"assistant","content":""},"done":true,"total_duration":...}
```

> **Important:** Notice that in streaming mode, each chunk contains only a **fragment** of the content, not the full response. The client must concatenate all fragments.

---

## Step 3: Create the Ollama Service Layer

We'll create a clean service layer that handles all communication with Ollama. This keeps our endpoint code clean and makes it easy to swap Ollama for another provider later.

Create a new file `services/ollama_service.py`:

```python
import httpx
import json
from typing import AsyncGenerator

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"


async def chat_completion(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Send messages to Ollama and get a complete response.
    No streaming — waits for the full response.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
            },
            timeout=120.0,  # LLMs can be slow, especially on first load
        )
        response.raise_for_status()
        return response.json()


async def chat_completion_stream(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
) -> AsyncGenerator[str, None]:
    """
    Send messages to Ollama and stream the response token by token.
    Yields each content fragment as it arrives.
    """
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": True,
            },
            timeout=120.0,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
                # If done, we can stop
                if chunk.get("done", False):
                    break
```

**What's happening here:**

- `chat_completion()` — sends a request with `stream: false` and returns the full JSON response. Simple and straightforward.
- `chat_completion_stream()` — sends a request with `stream: true` and uses `httpx`'s `client.stream()` to read the response line by line. Each line is a JSON object containing a content fragment. We yield each fragment as a Python async generator.
- We set `timeout=120.0` because the first request to Ollama can be slow (it needs to load the model into memory).

---

## Step 4: Build the Single Message Endpoint

Now let's create our first endpoint. This is the simplest case: the user sends one message, gets one response, no history kept.

Create a new file `routers/chat.py`:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.ollama_service import chat_completion

router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ──────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────

class SingleMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's message")
    system_prompt: str = Field(
        default="You are a helpful assistant.",
        description="Optional system prompt to control behavior",
    )
    model: str = Field(default="llama3.2", description="Ollama model name")


class SingleMessageResponse(BaseModel):
    response: str
    model: str


# ──────────────────────────────────────────────
# Endpoint
# ──────────────────────────────────────────────

@router.post("/single", response_model=SingleMessageResponse)
async def single_message(request: SingleMessageRequest):
    """
    Send a single message to the LLM and get a complete response.
    No conversation history — each request is independent.
    """
    messages = [
        {"role": "system", "content": request.system_prompt},
        {"role": "user", "content": request.message},
    ]

    try:
        result = await chat_completion(messages, model=request.model)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Ollama. Is it running on localhost:11434?",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return SingleMessageResponse(
        response=result["message"]["content"],
        model=result["model"],
    )
```

**Don't forget** to register the router in your main app:

```python
# In your main.py or app.py
from routers.chat import router as chat_router

app.include_router(chat_router)
```

**Test it:**

```bash
curl -X POST http://localhost:8000/api/chat/single \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is FastAPI in one sentence?"
  }'
```

**Expected response:**

```json
{
  "response": "FastAPI is a modern, fast, web framework for building APIs with Python...",
  "model": "llama3.2"
}
```

---

## Step 5: Add Streaming to Single Message

Now let's add a streaming version of the same endpoint. The client will receive tokens as they're generated using **Server-Sent Events (SSE)**.

Add this to `routers/chat.py`:

```python
from fastapi.responses import StreamingResponse
from services.ollama_service import chat_completion_stream
import json


async def _sse_generator(messages: list[dict], model: str):
    """
    Wraps the Ollama stream into SSE format.
    SSE format: each event is "data: <json>\n\n"
    """
    try:
        async for token in chat_completion_stream(messages, model=model):
            # Send each token as an SSE event
            event_data = json.dumps({"token": token})
            yield f"data: {event_data}\n\n"

        # Signal that streaming is complete
        yield f"data: {json.dumps({'done': True})}\n\n"

    except httpx.ConnectError:
        error = json.dumps({"error": "Cannot connect to Ollama"})
        yield f"data: {error}\n\n"


@router.post("/single/stream")
async def single_message_stream(request: SingleMessageRequest):
    """
    Send a single message and stream the response via SSE.
    Each event contains a token fragment.
    """
    messages = [
        {"role": "system", "content": request.system_prompt},
        {"role": "user", "content": request.message},
    ]

    return StreamingResponse(
        _sse_generator(messages, model=request.model),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

**How SSE works:**

```
Client sends POST request
    │
Server responds with Content-Type: text/event-stream
    │
    ├── data: {"token": "Fast"}\n\n
    ├── data: {"token": "API"}\n\n
    ├── data: {"token": " is"}\n\n
    ├── data: {"token": " a"}\n\n
    ├── ...
    └── data: {"done": true}\n\n
    │
Connection closes
```

**Test it:**

```bash
curl -X POST http://localhost:8000/api/chat/single/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Count from 1 to 5"}' \
  --no-buffer
```

---
