# """Minimal OpenRouter client for the Nemotron model. Run directly to smoke-test."""
# import os
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# # IMPORTANT: confirm this exact slug on the OpenRouter model page (copy icon next to the
# # name). The free variant ends in ":free". Replace if it differs.
# MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

# def chat(messages, temperature=0.3, max_tokens=1024):
#     if not OPENROUTER_API_KEY:
#         raise RuntimeError("OPENROUTER_API_KEY missing — check your .env")
#     resp = requests.post(
#         OPENROUTER_URL,
#         headers={
#             "Authorization": f"Bearer {OPENROUTER_API_KEY}",
#             "Content-Type": "application/json",
#             # optional, used by OpenRouter for app ranking — harmless to keep:
#             "HTTP-Referer": "http://localhost",
#             "X-Title": "AskDSA",
#         },
#         json={
#             "model": MODEL,
#             "messages": messages,
#             "temperature": temperature,
#             "max_tokens": max_tokens,
#         },
#         timeout=120,
#     )
#     # resp.raise_for_status()
#     # return resp.json()["choices"][0]["message"]["content"]
#     if resp.status_code >= 400:
#         raise RuntimeError(f"OpenRouter {resp.status_code}: {resp.text}")
#     data = resp.json()
#     if not data.get("choices"):
#         # OpenRouter sometimes returns 200 with an error payload (e.g. rate limit)
#         raise RuntimeError(f"OpenRouter returned no choices: {data}")
#     msg = data["choices"][0]["message"]
#     # reasoning models can leave `content` empty and put text in `reasoning`
#     return msg.get("content") or msg.get("reasoning") or ""

# if __name__ == "__main__":
#     reply = chat([{"role": "user", "content": "In one sentence, what is a hash map?"}])
#     print("MODEL REPLY:\n", reply)




"""Minimal OpenRouter client for the Nemotron model. Run directly to smoke-test."""
import os, time
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

TRANSIENT = {429, 500, 502, 503, 504}   # retry these; they're temporary

def chat(messages, temperature=0.3, max_tokens=1024, retries=4):
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY missing — check your .env")
    last = None
    for attempt in range(retries):
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-Title": "AskDSA",
            },
            json={"model": MODEL, "messages": messages,
                  "temperature": temperature, "max_tokens": max_tokens,
                  "reasoning": {"enabled": False}},
            timeout=120,
        )
        # transient HTTP status -> wait and retry
        if resp.status_code in TRANSIENT:
            last = f"HTTP {resp.status_code}: {resp.text[:200]}"
            time.sleep(2 * (attempt + 1)); continue
        if resp.status_code >= 400:
            raise RuntimeError(f"OpenRouter {resp.status_code}: {resp.text}")
        data = resp.json()
        if not data.get("choices"):
            # OpenRouter sometimes returns 200 with an error payload (e.g. provider overloaded)
            err = data.get("error", {}) or {}
            if err.get("code") in TRANSIENT or "overload" in str(err).lower():
                last = str(err)
                time.sleep(2 * (attempt + 1)); continue
            raise RuntimeError(f"OpenRouter returned no choices: {data}")
        msg = data["choices"][0]["message"]
        return msg.get("content") or ""   # never surface the model's internal reasoning
    raise RuntimeError(f"OpenRouter unavailable after {retries} tries (provider overloaded): {last}")

if __name__ == "__main__":
    print(chat([{"role": "user", "content": "In one sentence, what is a hash map?"}]))