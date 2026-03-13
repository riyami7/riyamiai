"""Interactive chat client for testing conversations with streaming.

Usage:
    python scripts/chat_client.py          # normal mode
    python scripts/chat_client.py --rag    # RAG-augmented mode

Requires the API server to be running at BASE_URL.
Update TOKEN with a valid Bearer token before running.
"""

import argparse
import httpx
import json
import sys

# ──────────────────────────────────────────────
# Configuration — update these before running
# ──────────────────────────────────────────────

BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzcxMzE5MTUyLCJpYXQiOjE3NzEzMTczNTJ9.B-xmx_Kq8DG3uv6VwgE5kQ1WCsMxmx445YH0QPtRwuM"

# ──────────────────────────────────────────────

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


def create_conversation() -> int:
    """Create a new conversation and return its ID."""
    response = httpx.post(
        f"{BASE_URL}/api/conversations/",
        headers=HEADERS,
        json={},
    )
    response.raise_for_status()
    data = response.json()
    return data["id"]


def stream_message(conversation_id: int, message: str, use_rag: bool = False) -> None:
    """Send a message and stream the response token by token."""
    with httpx.stream(
        "POST",
        f"{BASE_URL}/api/conversations/{conversation_id}/messages/stream",
        headers=HEADERS,
        json={"content": message, "use_rag": use_rag},
        timeout=300.0,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue

            payload = json.loads(line[6:])

            if payload.get("error"):
                print(f"\n[ERROR] {payload['error']}")
                return

            if payload.get("done"):
                print()  # Newline after streamed response
                return

            token = payload.get("token", "")
            print(token, end="", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive chat client with streaming")
    parser.add_argument("--rag", action="store_true", help="Enable RAG-augmented responses")
    args = parser.parse_args()

    rag_label = "ON" if args.rag else "OFF"

    print("=" * 50)
    print("  Interactive Chat Client (streaming)")
    print("=" * 50)
    print(f"  Server: {BASE_URL}")
    print(f"  RAG:    {rag_label}")
    print("  Type 'quit' or 'exit' to end")
    print("=" * 50)

    # Create a new conversation
    try:
        conversation_id = create_conversation()
    except httpx.HTTPStatusError as e:
        print(f"\nFailed to create conversation: {e.response.status_code}")
        print(e.response.text)
        sys.exit(1)
    except httpx.ConnectError:
        print(f"\nCannot connect to {BASE_URL}. Is the server running?")
        sys.exit(1)

    print(f"\n  Conversation #{conversation_id} created.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            print("\nGoodbye!")
            break

        print("Assistant: ", end="", flush=True)

        try:
            stream_message(conversation_id, user_input, use_rag=args.rag)
        except httpx.HTTPStatusError as e:
            print(f"\n[ERROR] {e.response.status_code}: {e.response.text}")
        except httpx.ConnectError:
            print(f"\n[ERROR] Cannot connect to {BASE_URL}")
        except httpx.ReadTimeout:
            print(f"\n[ERROR] Request timed out. The server may be busy with RAG processing — try again.")


if __name__ == "__main__":
    main()
