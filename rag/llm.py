"""Minimal OpenRouter client for the Nemotron model. Run directly to smoke-test."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# IMPORTANT: confirm this exact slug on the OpenRouter model page (copy icon next to the
# name). The free variant ends in ":free". Replace if it differs.
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

def chat(messages, temperature=0.3, max_tokens=1024):
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY missing — check your .env")
    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            # optional, used by OpenRouter for app ranking — harmless to keep:
            "HTTP-Referer": "http://localhost",
            "X-Title": "AskDSA",
        },
        json={
            "model": MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

if __name__ == "__main__":
    reply = chat([{"role": "user", "content": "In one sentence, what is a hash map?"}])
    print("MODEL REPLY:\n", reply)