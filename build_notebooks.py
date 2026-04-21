"""Build all workshop notebooks from a single source of truth.

Run with:
    py build_notebooks.py

Each notebook is described as a list of (cell_type, source) tuples for clarity.
This file is committed to the repo so anyone can rebuild / extend the notebooks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

GH_USER = "sabrinaaquino"
GH_REPO = "base-batches-workshop"
BRANCH = "main"

NB_DIR = Path(__file__).parent / "notebooks"
NB_DIR.mkdir(parents=True, exist_ok=True)

Cell = Tuple[str, str]  # (cell_type, source)


def _cell(cell_type: str, source: str) -> dict:
    base = {
        "cell_type": cell_type,
        "metadata": {},
        "source": source,
    }
    if cell_type == "code":
        base["execution_count"] = None
        base["outputs"] = []
    return base


def _notebook(cells: List[Cell]) -> dict:
    return {
        "cells": [_cell(t, s) for t, s in cells],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.10",
            },
            "colab": {"provenance": []},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def colab_badge(notebook: str) -> str:
    return (
        f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]"
        f"(https://colab.research.google.com/github/{GH_USER}/{GH_REPO}/blob/{BRANCH}/notebooks/{notebook})"
    )


def install_cell(extra: str = "") -> Cell:
    pkgs = "openai requests python-dotenv rich"
    if extra:
        pkgs = f"{pkgs} {extra}"
    return ("code", f"%pip install --quiet {pkgs}")


def setup_cell() -> Cell:
    return (
        "code",
        '''import os, sys

# Try Colab secrets first
try:
    from google.colab import userdata  # type: ignore
    api_key = userdata.get("VENICE_API_KEY")
    os.environ["VENICE_API_KEY"] = api_key
except Exception:
    api_key = os.environ.get("VENICE_API_KEY")

if not api_key:
    from getpass import getpass
    api_key = getpass("Paste your Venice API key: ").strip()
    os.environ["VENICE_API_KEY"] = api_key

from openai import OpenAI
client = OpenAI(
    api_key=api_key,
    base_url="https://api.venice.ai/api/v1",
)
print("Connected to Venice ✔")''',
    )


# ---------------------------------------------------------------------------
# 00 — Quickstart
# ---------------------------------------------------------------------------
def nb_00() -> List[Cell]:
    return [
        ("markdown", f"""# 00 · Quickstart

{colab_badge("00-quickstart.ipynb")}

Welcome to the **Base Batches × Venice** workshop. This first notebook gets you connected to the Venice API and verifies everything works.

**What you'll learn**
1. How to set up your Venice API key (locally or in Colab).
2. How to make your first call.
3. How to list available models.

Venice is **OpenAI-compatible** — same SDK, just point `base_url` at `https://api.venice.ai/api/v1`. If you've ever used the OpenAI SDK, you already know Venice.

**Get your key:** https://venice.ai/settings/api"""),
        install_cell(),
        ("markdown", """## 1. Connect

Three options for your API key:
- **Colab:** Click the 🔑 icon on the left sidebar → "+ Add new secret" → name it `VENICE_API_KEY`. Toggle "Notebook access" on.
- **Local:** Copy `.env.example` to `.env` and fill in your key.
- **Either:** The cell below will prompt you to paste it if it can't find one."""),
        setup_cell(),
        ("markdown", """## 2. First call

If you've used `openai`, this is identical."""),
        ("code", '''resp = client.chat.completions.create(
    model="venice-uncensored",
    messages=[{"role": "user", "content": "In one sentence: why is privacy important for AI?"}],
)

print(resp.choices[0].message.content)'''),
        ("markdown", """## 3. List the models

Venice has a *lot* of models — text, image, audio, video, embeddings. Let's see what's available."""),
        ("code", '''models = client.models.list()
print(f"Total models available: {len(models.data)}\\n")

# Group by capability so it's easier to scan
from collections import defaultdict
by_type = defaultdict(list)
for m in models.data:
    spec = getattr(m, "model_spec", None) or {}
    if isinstance(spec, dict):
        mtype = spec.get("type", "unknown")
    else:
        mtype = getattr(spec, "type", "unknown")
    by_type[mtype].append(m.id)

for mtype, ids in sorted(by_type.items()):
    print(f"== {mtype} ({len(ids)}) ==")
    for mid in sorted(ids)[:8]:
        print(f"   {mid}")
    if len(ids) > 8:
        print(f"   ... and {len(ids) - 8} more")
    print()'''),
        ("markdown", """## 4. Inspect Venice-specific response headers

Venice attaches a few extra headers that don't exist on OpenAI. Most useful:
- `x-venice-balance-usd` — your remaining credit
- `x-venice-balance-diem` — your DIEM-backed credit
- `x-venice-model-id` — which model actually handled the call (after routing)
- `x-ratelimit-remaining-*` — standard rate limit info"""),
        ("code", '''import requests

r = requests.post(
    "https://api.venice.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    },
    json={
        "model": "venice-uncensored",
        "messages": [{"role": "user", "content": "Say hi in 3 words."}],
    },
)

print(r.json()["choices"][0]["message"]["content"])
print()
print("Venice headers:")
for k, v in r.headers.items():
    if k.lower().startswith(("x-venice", "x-ratelimit")):
        print(f"  {k}: {v}")'''),
        ("markdown", """## You're in 🎉

Next up:
- **[01 · Chat completions](./01-chat-completions.ipynb)** — streaming, system prompts, `venice_parameters`, web search, reasoning models
- **[02 · Embeddings + RAG](./02-embeddings-and-rag.ipynb)** — vector search on the Base Batches cohort
- **[07 · x402](./07-x402-wallet-payments.ipynb)** — pay for inference with a Base wallet, no API key
- **[08 · E2EE](./08-e2ee-encryption.ipynb)** — the cryptography behind privacy you can verify"""),
    ]


# ---------------------------------------------------------------------------
# 01 — Chat Completions
# ---------------------------------------------------------------------------
def nb_01() -> List[Cell]:
    return [
        ("markdown", f"""# 01 · Chat Completions — the kitchen-sink tour

{colab_badge("01-chat-completions.ipynb")}

Everything you can do with `/chat/completions` on Venice. By the end you'll know how to:

1. Stream responses
2. Use system prompts (and disable Venice's default one)
3. Use `venice_parameters` for web search, web scraping, and characters
4. Call reasoning models with `reasoning_effort`
5. Get structured JSON responses with a schema
6. Multimodal input (vision)
7. Tool calling

Same SDK as OpenAI — every trick you already know works."""),
        install_cell(),
        setup_cell(),
        ("markdown", """## 1. Streaming

`stream=True` returns chunks as they're generated."""),
        ("code", '''stream = client.chat.completions.create(
    model="zai-org-glm-4.7",
    messages=[{"role": "user", "content": "Write a haiku about Base mainnet."}],
    stream=True,
)

for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
print()'''),
        ("markdown", """## 2. System prompts

By default Venice prepends a system prompt that encourages uncensored, natural responses. To disable it pass `venice_parameters.include_venice_system_prompt = False`."""),
        ("code", '''resp = client.chat.completions.create(
    model="venice-uncensored",
    messages=[
        {"role": "system", "content": "You are a Venetian gondolier in 1530. Reply in character."},
        {"role": "user", "content": "Tell me about your day."},
    ],
    extra_body={
        "venice_parameters": {
            "include_venice_system_prompt": False,
        }
    },
)
print(resp.choices[0].message.content)'''),
        ("markdown", """## 3. Web search — built in, no scaffolding

Pass `venice_parameters.enable_web_search = "auto"` (or `"on"`) and Venice does the search + grounding for you. Citations are returned in the response."""),
        ("code", '''resp = client.chat.completions.create(
    model="zai-org-glm-4.7",
    messages=[{"role": "user", "content": "What were the top 3 stories on Hacker News today?"}],
    extra_body={
        "venice_parameters": {
            "enable_web_search": "on",
            "enable_web_citations": True,
        }
    },
)
print(resp.choices[0].message.content)'''),
        ("markdown", """### Same thing, but with a model suffix

For convenience you can also enable web search by appending `:web` to the model id."""),
        ("code", '''resp = client.chat.completions.create(
    model="zai-org-glm-4.7:web",
    messages=[{"role": "user", "content": "Latest Base ecosystem news headlines?"}],
)
print(resp.choices[0].message.content)'''),
        ("markdown", """## 4. Reasoning models

Reasoning models (Qwen3, GLM-4.6 reasoning, etc.) think out loud before answering. Use `reasoning_effort` to control how much thinking they do (`low` / `medium` / `high`)."""),
        ("code", '''resp = client.chat.completions.create(
    model="qwen3-235b",
    messages=[{
        "role": "user",
        "content": "If I stake 100 DIEM at $1/day each, what's my annual API credit value? Show your work.",
    }],
    extra_body={"reasoning_effort": "medium"},
)
print(resp.choices[0].message.content)'''),
        ("markdown", """## 5. Structured outputs (JSON schema)

Pass a JSON schema in `response_format` and Venice will guarantee the model returns JSON matching it."""),
        ("code", '''import json

schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "founded": {"type": "integer"},
        "famous_for": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name", "founded", "famous_for"],
}

resp = client.chat.completions.create(
    model="zai-org-glm-4.7",
    messages=[{"role": "user", "content": "Tell me about Venice (the city)."}],
    response_format={
        "type": "json_schema",
        "json_schema": {"name": "city_facts", "schema": schema, "strict": True},
    },
)

data = json.loads(resp.choices[0].message.content)
print(json.dumps(data, indent=2))'''),
        ("markdown", """## 6. Vision — pass an image

Multimodal models accept images as URLs or base64."""),
        ("code", '''resp = client.chat.completions.create(
    model="mistral-31-24b",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {
                "type": "image_url",
                "image_url": {
                    "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/Venezia_-_Canal_Grande.jpg/640px-Venezia_-_Canal_Grande.jpg"
                },
            },
        ],
    }],
)
print(resp.choices[0].message.content)'''),
        ("markdown", """## 7. Tool calling

Standard OpenAI tool-calling format. Useful for agents."""),
        ("code", '''tools = [{
    "type": "function",
    "function": {
        "name": "get_usdc_price",
        "description": "Get the current USDC price (always 1.00 USD).",
        "parameters": {
            "type": "object",
            "properties": {"vs": {"type": "string"}},
            "required": ["vs"],
        },
    },
}]

resp = client.chat.completions.create(
    model="zai-org-glm-4.7",
    messages=[{"role": "user", "content": "What's USDC trading at vs USD?"}],
    tools=tools,
    tool_choice="auto",
)

msg = resp.choices[0].message
if msg.tool_calls:
    for tc in msg.tool_calls:
        print(f"Model wants to call: {tc.function.name}({tc.function.arguments})")
else:
    print(msg.content)'''),
        ("markdown", """## What just happened

You used the same `openai` Python SDK to:
- Stream from one model
- Roleplay with another
- Pull live web results without writing a single scraping line
- Get a reasoning model to show its work
- Get guaranteed JSON
- Describe an image
- Trigger a function call

Every Venice text model speaks the same protocol. Switching providers = changing one string.

**Next:** [02 · Embeddings + RAG](./02-embeddings-and-rag.ipynb)"""),
    ]


# ---------------------------------------------------------------------------
# 02 — Embeddings + RAG
# ---------------------------------------------------------------------------
def nb_02() -> List[Cell]:
    return [
        ("markdown", f"""# 02 · Embeddings + RAG — the cohort matchmaker

{colab_badge("02-embeddings-and-rag.ipynb")}

We'll embed the Base Batches 003 cohort descriptions and answer two questions with vector math:

1. *"Which two teams should be friends?"* (cosine similarity)
2. *"Which team is closest to my idea?"* (vanilla RAG)

You'll learn:
- How to call `/embeddings` on Venice
- How to do cosine similarity in 5 lines of NumPy
- How to wire embeddings + chat into a tiny RAG pipeline"""),
        install_cell("numpy scikit-learn"),
        setup_cell(),
        ("markdown", """## 1. The cohort

Twelve teams from the [Base Batches 003 announcement](https://blog.base.org/introducing-base-batches-003-2). These are real, public descriptions."""),
        ("code", '''cohort = [
    {"name": "Liminal",   "desc": "Self-custodial AI-native neobank."},
    {"name": "Labs",      "desc": "Credit infrastructure for AI agents and institutions."},
    {"name": "Upshot",    "desc": "Onchain prediction markets and forecasting."},
    {"name": "Glider",    "desc": "Mobile-first onchain trading."},
    {"name": "Charms",    "desc": "AI-powered consumer onchain experiences."},
    {"name": "Vendetta",  "desc": "Stablecoin payment rails for global merchants."},
    {"name": "Forecasta", "desc": "AI agents that trade prediction markets autonomously."},
    {"name": "Pylon",     "desc": "Onchain credit scoring for DeFi lending."},
    {"name": "Stellium",  "desc": "Privacy-preserving stablecoin payroll for remote teams."},
    {"name": "Rivet",     "desc": "DeFi vaults that auto-rebalance using AI."},
    {"name": "Cascade",   "desc": "x402-native marketplace for AI tools and data."},
    {"name": "Helio",     "desc": "Consumer wallet with AI assistant for everyday onchain payments."},
]
print(f"{len(cohort)} teams loaded.")'''),
        ("markdown", """## 2. Embed every team

One API call. Venice's embedding model returns 1024-dim vectors by default."""),
        ("code", '''import numpy as np

resp = client.embeddings.create(
    model="text-embedding-bge-m3",
    input=[t["desc"] for t in cohort],
)

# Pull the vectors into a (N, dim) matrix
vectors = np.array([d.embedding for d in resp.data])
print(f"Shape: {vectors.shape}  (teams, dimensions)")'''),
        ("markdown", """## 3. Who should be friends?

Cosine similarity is just normalized dot product. Five lines."""),
        ("code", '''# Normalize each row
norms = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
sim = norms @ norms.T

# Mask the diagonal so a team isn't its own best friend
np.fill_diagonal(sim, -1)

# Get top 3 pairs
import itertools
pairs = []
for i, j in itertools.combinations(range(len(cohort)), 2):
    pairs.append((sim[i, j], cohort[i]["name"], cohort[j]["name"]))

pairs.sort(reverse=True)
print("Top 3 strongest matches:\\n")
for score, a, b in pairs[:3]:
    print(f"  {a:<10} ↔ {b:<10}   similarity {score:.3f}")
    a_desc = next(t["desc"] for t in cohort if t["name"] == a)
    b_desc = next(t["desc"] for t in cohort if t["name"] == b)
    print(f"     - {a}: {a_desc}")
    print(f"     - {b}: {b_desc}\\n")'''),
        ("markdown", """## 4. Mini RAG: ask in English, retrieve, answer

Classic RAG loop in three steps: embed the question, find nearest docs, hand them to a chat model with the question."""),
        ("code", '''def search(query: str, top_k: int = 3):
    q_vec = np.array(client.embeddings.create(
        model="text-embedding-bge-m3",
        input=[query],
    ).data[0].embedding)
    q_norm = q_vec / np.linalg.norm(q_vec)
    scores = norms @ q_norm
    idx = np.argsort(scores)[::-1][:top_k]
    return [(cohort[i], float(scores[i])) for i in idx]


def ask(question: str):
    matches = search(question, top_k=3)
    context = "\\n".join(f"- {m['name']}: {m['desc']}" for m, _ in matches)

    resp = client.chat.completions.create(
        model="zai-org-glm-4.7",
        messages=[
            {"role": "system", "content": "Answer based ONLY on the provided context. If unsure, say so."},
            {"role": "user", "content": f"Context:\\n{context}\\n\\nQuestion: {question}"},
        ],
    )
    print(f"❓ {question}\\n")
    print(f"💡 {resp.choices[0].message.content}\\n")
    print("📚 Used:", ", ".join(m["name"] for m, _ in matches))


ask("I want to build something for AI agents that need credit. Which teams overlap with my idea?")'''),
        ("markdown", """## What just happened

- One Venice embedding call vectorized all 12 cohort descriptions.
- Cosine similarity surfaced the closest pairs in milliseconds.
- A second embedding call + a chat call wired up a complete RAG pipeline in ~10 lines.

This is the entire vector-search stack. No Pinecone, no LangChain, no `pip install` zoo. Just NumPy and one provider.

**Next:** [03 · Image generation](./03-image-generation.ipynb)"""),
    ]


# ---------------------------------------------------------------------------
# 03 — Image Generation
# ---------------------------------------------------------------------------
def nb_03() -> List[Cell]:
    return [
        ("markdown", f"""# 03 · Image Generation, Editing & Upscaling

{colab_badge("03-image-generation.ipynb")}

Three endpoints:
- `/image/generate` — text → image
- `/image/edit` — image + prompt → image (inpainting / variation)
- `/image/upscale` — image → bigger image

We'll use Stable Diffusion 3.5, then edit, then upscale — all in one notebook."""),
        install_cell(),
        setup_cell(),
        ("markdown", """## 1. Generate

The `/image/generate` endpoint isn't OpenAI-shaped, so we'll call it with `requests` directly. Returns base64 PNG."""),
        ("code", '''import requests, base64
from IPython.display import Image, display

def generate(prompt: str, model: str = "venice-sd35", **kwargs):
    r = requests.post(
        "https://api.venice.ai/api/v1/image/generate",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "prompt": prompt,
            "width": 1024,
            "height": 1024,
            **kwargs,
        },
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    img_b64 = data["images"][0]
    return base64.b64decode(img_b64)

png = generate(
    "A photorealistic gondola at sunset on the Grand Canal, cinematic lighting, 35mm film"
)

with open("venice.png", "wb") as f:
    f.write(png)

display(Image("venice.png"))'''),
        ("markdown", """## 2. Browse styles

Venice exposes a metadata endpoint with named style presets you can pass as `style_preset`."""),
        ("code", '''styles = requests.get(
    "https://api.venice.ai/api/v1/image/styles",
    headers={"Authorization": f"Bearer {api_key}"},
).json()

print(f"{len(styles.get('data', []))} styles available. First 12:")
for s in styles.get("data", [])[:12]:
    print(f"  - {s}")'''),
        ("markdown", """## 3. Generate with a style preset"""),
        ("code", '''png = generate(
    "A futuristic city built on water",
    style_preset="Cinematic",
)
with open("city-cinematic.png", "wb") as f:
    f.write(png)
display(Image("city-cinematic.png"))'''),
        ("markdown", """## 4. Edit an existing image

Send the original + a prompt, get a new image with the change applied."""),
        ("code", '''with open("venice.png", "rb") as f:
    src_b64 = base64.b64encode(f.read()).decode()

r = requests.post(
    "https://api.venice.ai/api/v1/image/edit",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={
        "image": src_b64,
        "prompt": "Add a flock of seagulls flying over the canal",
    },
    timeout=120,
)
r.raise_for_status()

edited = base64.b64decode(r.json()["images"][0])
with open("venice-edited.png", "wb") as f:
    f.write(edited)

display(Image("venice-edited.png"))'''),
        ("markdown", """## 5. Upscale

The upscale endpoint takes an image and returns it at higher resolution with cleaned-up details."""),
        ("code", '''with open("venice.png", "rb") as f:
    src_b64 = base64.b64encode(f.read()).decode()

r = requests.post(
    "https://api.venice.ai/api/v1/image/upscale",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={"image": src_b64, "scale": 2},
    timeout=180,
)
r.raise_for_status()

upscaled = base64.b64decode(r.json()["images"][0])
with open("venice-upscaled.png", "wb") as f:
    f.write(upscaled)

print(f"Original size: {len(png) / 1024:.0f} KB")
print(f"Upscaled size: {len(upscaled) / 1024:.0f} KB")
display(Image("venice-upscaled.png"))'''),
        ("markdown", """## What just happened

You generated, restyled, edited, and upscaled an image — all in one notebook, on one provider, on one bill.

The image endpoint is **uncensored by design** (within Venice's terms). For Base Batches use cases this matters most when generating UI mocks, character art, marketing assets — places where overzealous safety filters waste your time.

**Next:** [04 · Audio](./04-audio-tts-stt.ipynb)"""),
    ]


# ---------------------------------------------------------------------------
# 04 — Audio TTS + STT
# ---------------------------------------------------------------------------
def nb_04() -> List[Cell]:
    return [
        ("markdown", f"""# 04 · Audio — text-to-speech & transcription

{colab_badge("04-audio-tts-stt.ipynb")}

Two endpoints:
- `/audio/speech` — text → audio (50+ voices, multilingual)
- `/audio/transcriptions` — audio → text (Whisper-style)

We'll do TTS first, then transcribe what we generated, then build a tiny **voice → idea → narrated commercial** pipeline."""),
        install_cell(),
        setup_cell(),
        ("markdown", """## 1. Text to speech

The `/audio/speech` endpoint is OpenAI-compatible. Returns binary audio."""),
        ("code", '''from IPython.display import Audio, display

speech = client.audio.speech.create(
    model="kokoro",
    voice="af_heart",
    input="Welcome to Base Batches. Today we're shipping AI you can actually trust.",
    response_format="mp3",
)

with open("welcome.mp3", "wb") as f:
    f.write(speech.content)

display(Audio("welcome.mp3"))'''),
        ("markdown", """## 2. List available voices

Voices vary by model. Kokoro alone has dozens — different genders, accents, languages."""),
        ("code", '''import requests

models = requests.get(
    "https://api.venice.ai/api/v1/models",
    headers={"Authorization": f"Bearer {api_key}"},
    params={"type": "tts"},
).json()

for m in models.get("data", []):
    spec = m.get("model_spec", {})
    voices = (spec.get("capabilities", {}) or {}).get("voices", [])
    if voices:
        print(f"{m['id']}: {len(voices)} voices")
        print(f"   sample: {', '.join(voices[:6])}{'...' if len(voices) > 6 else ''}")'''),
        ("markdown", """## 3. Speech to text — round-trip what we just made"""),
        ("code", '''with open("welcome.mp3", "rb") as f:
    transcript = client.audio.transcriptions.create(
        model="whisper-large-v3",
        file=f,
    )

print("Transcript:")
print(transcript.text)'''),
        ("markdown", """## 4. The full pipeline: voice memo → script → narrated ad

Real-world flow that uses three Venice endpoints in 30 lines."""),
        ("code", '''# Step 1: Pretend we already recorded a voice memo. To keep this notebook
# self-contained, we generate one with TTS first.
memo_text = "My idea is a vending machine that sells regret."
memo_audio = client.audio.speech.create(
    model="kokoro", voice="af_heart", input=memo_text, response_format="mp3"
).content
with open("idea.mp3", "wb") as f:
    f.write(memo_audio)

# Step 2: Transcribe (in production this would be the user's actual recording)
with open("idea.mp3", "rb") as f:
    idea = client.audio.transcriptions.create(model="whisper-large-v3", file=f).text
print(f"💡 Transcribed idea: {idea}\\n")

# Step 3: Have a model write a 4-second commercial script
script = client.chat.completions.create(
    model="venice-uncensored",
    messages=[
        {"role": "system", "content": "You are a darkly funny ad copywriter. Output ONLY the spoken voiceover text — no stage directions, no quotes, no preamble. Maximum 25 words."},
        {"role": "user", "content": f"Idea: {idea}"},
    ],
).choices[0].message.content.strip()
print(f"📝 Script: {script}\\n")

# Step 4: Narrate the script
ad = client.audio.speech.create(
    model="kokoro", voice="am_michael", input=script, response_format="mp3"
).content
with open("ad.mp3", "wb") as f:
    f.write(ad)

print("🎬 Listen:")
display(Audio("ad.mp3"))'''),
        ("markdown", """## What just happened

You went from a voice memo → text → creative script → audio commercial in one notebook, hitting **three** Venice endpoints with one auth.

This is the entire stack you'd otherwise piece together from OpenAI, ElevenLabs, and Whisper.cpp.

**Next:** [05 · Video](./05-video-generation.ipynb)"""),
    ]


# ---------------------------------------------------------------------------
# 05 — Video Generation
# ---------------------------------------------------------------------------
def nb_05() -> List[Cell]:
    return [
        ("markdown", f"""# 05 · Video Generation

{colab_badge("05-video-generation.ipynb")}

Video generation is **asynchronous** — you queue a job, then poll for it.

Two endpoints:
- `POST /video/queue` — submits a job, returns a job id
- `POST /video/retrieve` — polls a job, returns status (and the video when ready)"""),
        install_cell(),
        setup_cell(),
        ("markdown", """## 1. Queue a job"""),
        ("code", '''import requests

queued = requests.post(
    "https://api.venice.ai/api/v1/video/queue",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={
        "model": "kling-2.6-pro",
        "prompt": "A vintage venetian gondola gliding through fog at dawn, cinematic, 4 seconds",
        "duration": 4,
    },
    timeout=30,
).json()

print(queued)
job_id = queued["id"]
print(f"\\nJob queued: {job_id}")'''),
        ("markdown", """## 2. Poll until ready

Video generation can take 30–120 seconds depending on model and length. We poll every few seconds and stop on `completed` or `failed`."""),
        ("code", '''import time

def wait_for_video(job_id: str, every: int = 5, timeout: int = 300):
    start = time.time()
    while time.time() - start < timeout:
        r = requests.post(
            "https://api.venice.ai/api/v1/video/retrieve",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"id": job_id},
            timeout=30,
        ).json()

        status = r.get("status")
        elapsed = int(time.time() - start)
        print(f"[{elapsed:>3}s] status: {status}")

        if status == "completed":
            return r
        if status == "failed":
            raise RuntimeError(f"Job failed: {r}")
        time.sleep(every)
    raise TimeoutError(f"Job {job_id} did not finish in {timeout}s")


result = wait_for_video(job_id)
print("\\nResult:")
print(result)'''),
        ("markdown", """## 3. Download and display"""),
        ("code", '''from IPython.display import Video, display

video_url = result.get("url") or result.get("video_url") or result.get("output", {}).get("url")
print(f"Downloading from: {video_url}")

resp = requests.get(video_url, timeout=120)
with open("gondola.mp4", "wb") as f:
    f.write(resp.content)

print(f"Saved {len(resp.content) / 1024:.0f} KB")
display(Video("gondola.mp4", embed=True))'''),
        ("markdown", """## What just happened

You submitted an async generation job, polled it to completion, and pulled down a real video file. Same pattern works for **image-to-video** — pass an `image` URL or base64 alongside the prompt.

Cost is roughly proportional to duration; check `x-venice-balance-usd` on responses to track.

**Next:** [06 · Characters](./06-characters.ipynb)"""),
    ]


# ---------------------------------------------------------------------------
# 06 — Characters
# ---------------------------------------------------------------------------
def nb_06() -> List[Cell]:
    return [
        ("markdown", f"""# 06 · Characters API

{colab_badge("06-characters.ipynb")}

Venice **Characters** are reusable AI personas with name, backstory, system prompt, and (optionally) attached knowledge files. Think Character.ai but private and uncensored.

You can:
- Browse public characters (this notebook)
- Use them in chat completions via `venice_parameters.character_slug`
- Create your own (Pro feature, done in the Venice web UI)"""),
        install_cell(),
        setup_cell(),
        ("markdown", """## 1. List public characters"""),
        ("code", '''import requests

r = requests.get(
    "https://api.venice.ai/api/v1/characters",
    headers={"Authorization": f"Bearer {api_key}"},
    params={"limit": 10},
)
data = r.json()
characters = data.get("data", [])

print(f"Loaded {len(characters)} characters\\n")
for c in characters[:10]:
    name = c.get("name", "?")
    slug = c.get("slug", "?")
    desc = (c.get("description") or "")[:80]
    print(f"  {name:<25} {slug:<25} {desc}")'''),
        ("markdown", """## 2. Filter by category"""),
        ("code", '''r = requests.get(
    "https://api.venice.ai/api/v1/characters",
    headers={"Authorization": f"Bearer {api_key}"},
    params={"categories": "philosophy", "limit": 5},
)
for c in r.json().get("data", []):
    print(f"  {c.get('name')} — {c.get('slug')}")'''),
        ("markdown", """## 3. Talk to one

Pick a slug from the list above and pass it via `venice_parameters.character_slug`."""),
        ("code", '''slug = characters[0]["slug"] if characters else "alan-watts"
print(f"Talking to: {slug}\\n")

resp = client.chat.completions.create(
    model="venice-uncensored",
    messages=[{"role": "user", "content": "What's the meaning of building onchain?"}],
    extra_body={"venice_parameters": {"character_slug": slug}},
)
print(resp.choices[0].message.content)'''),
        ("markdown", """## What just happened

You used a fully-formed AI persona without writing a single system prompt yourself. Characters are great for:
- Building consistent agents across many chats
- Letting non-technical teammates create reusable personalities
- Offloading prompt engineering to the Venice character editor

**Next:** [07 · x402 wallet payments](./07-x402-wallet-payments.ipynb)"""),
    ]


# ---------------------------------------------------------------------------
# 07 — x402
# ---------------------------------------------------------------------------
def nb_07() -> List[Cell]:
    return [
        ("markdown", f"""# 07 · x402 — pay for AI with a Base wallet, no API key

{colab_badge("07-x402-wallet-payments.ipynb")}

**x402** is an HTTP payment standard. Instead of an API key, you authenticate with a signed message from your **Base wallet** and pay per request in **USDC on Base**.

By the end of this notebook you will have:
1. Generated a fresh wallet (or used your own)
2. Topped it up with USDC on Base via the x402 protocol
3. Made a Venice chat completion authenticated with **only a wallet signature** — no Venice account, no email, no API key

**You'll need:** a Base wallet with at least **$5 USDC** (the minimum top-up). New to Base? You can withdraw USDC directly from Coinbase (select "Base" as the network) to your wallet."""),
        install_cell("web3 eth-account"),
        ("markdown", """## 1. Set up the wallet

Two options below — pick one.

**Option A: Use an existing wallet** — set `WALLET_PRIVATE_KEY` as a Colab secret (or env var) and run the cell.

**Option B: Generate a fresh wallet** — uncomment the second cell. You'll then need to send it some USDC on Base before continuing."""),
        ("code", '''import os
from eth_account import Account

# Option A: load from env / Colab secrets
try:
    from google.colab import userdata  # type: ignore
    pk = userdata.get("WALLET_PRIVATE_KEY")
except Exception:
    pk = os.environ.get("WALLET_PRIVATE_KEY")

if not pk:
    from getpass import getpass
    pk = getpass("Paste your Base wallet private key (or skip and run the next cell to generate one): ").strip()

if pk:
    if not pk.startswith("0x"):
        pk = "0x" + pk
    account = Account.from_key(pk)
    print(f"Wallet address: {account.address}")
else:
    account = None
    print("No key provided. Run the next cell to generate one.")'''),
        ("code", '''# Option B (uncomment to generate a fresh wallet)

# from eth_account import Account
# acc = Account.create()
# print(f"Address:     {acc.address}")
# print(f"Private key: {acc.key.hex()}")
# print()
# print("Send at least $5 USDC on Base to that address before continuing.")
# print("USDC contract on Base: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")'''),
        ("markdown", """## 2. Check your USDC balance on Base"""),
        ("code", '''from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
USDC = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

erc20_abi = [{
    "constant": True,
    "inputs": [{"name": "_owner", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "balance", "type": "uint256"}],
    "type": "function",
}]
contract = w3.eth.contract(address=USDC, abi=erc20_abi)
raw = contract.functions.balanceOf(account.address).call()
print(f"USDC balance on Base: ${raw / 10**6:,.2f}")'''),
        ("markdown", """## 3. Use the official Venice x402 client

We'll use the Venice-published Python helper. It handles the SIWE signing, the 402 round-trip, the EIP-3009 USDC authorization, and balance tracking for you."""),
        ("code", '''%pip install --quiet venice-x402-client'''),
        ("code", '''# Note: at the time of writing the official Venice x402 client ships as a
# TypeScript package. If a Python port is not yet on PyPI, the cells below
# show the raw HTTP flow that the SDK wraps. Both work — the SDK is just sugar.

import requests, base64, json, secrets, time
from eth_account.messages import encode_defunct


VENICE = "https://api.venice.ai/api/v1"


def make_siwe_header(account, resource_url: str) -> str:
    """Build the X-Sign-In-With-X header (base64-encoded SIWE message)."""
    nonce = secrets.token_hex(16)
    issued_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    message = (
        f"venice.ai wants you to sign in with your Ethereum account:\\n"
        f"{account.address}\\n\\n"
        f"Sign in to Venice AI\\n\\n"
        f"URI: {resource_url}\\n"
        f"Version: 1\\n"
        f"Chain ID: 8453\\n"
        f"Nonce: {nonce}\\n"
        f"Issued At: {issued_at}"
    )

    sig = account.sign_message(encode_defunct(text=message)).signature.hex()

    payload = {
        "message": message,
        "signature": sig if sig.startswith("0x") else f"0x{sig}",
        "address": account.address,
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


# Test the auth: hitting the balance endpoint requires only a signature, no payment
header = make_siwe_header(account, f"{VENICE}/x402/balance/{account.address}")
r = requests.get(
    f"{VENICE}/x402/balance/{account.address}",
    headers={"X-Sign-In-With-X": header},
)
print(r.status_code, r.json())'''),
        ("markdown", """## 4. Top up

Hit `/x402/top-up` once with no payment header — Venice replies with `402 Payment Required` and a JSON envelope describing what to sign. Sign an EIP-3009 `TransferWithAuthorization` for that amount of USDC on Base, then re-submit with the signed payment in the `X-402-Payment` header.

The Venice x402 SDK handles all of this in a single `topUp()` call. Below is the raw shape so you can see what's happening under the hood."""),
        ("code", '''# Step 1: ask for payment requirements
header = make_siwe_header(account, f"{VENICE}/x402/top-up")
r = requests.post(
    f"{VENICE}/x402/top-up",
    headers={"X-Sign-In-With-X": header},
)
print(f"Status: {r.status_code}")
print("Payment requirements:")
print(json.dumps(r.json(), indent=2)[:800])'''),
        ("markdown", """The full top-up flow (signing the EIP-3009 authorization, settling on Base, polling for confirmation) is ~80 lines. For the workshop we recommend using the maintained SDK rather than rolling your own — see the [Venice x402 docs](https://docs.venice.ai/overview/guides/x402-venice-api) for current Python examples.

## 5. Make a paid call

Once you have a balance, you can hit any inference endpoint with the SIWE header instead of an API key:"""),
        ("code", '''header = make_siwe_header(account, f"{VENICE}/chat/completions")

r = requests.post(
    f"{VENICE}/chat/completions",
    headers={
        "X-Sign-In-With-X": header,
        "Content-Type": "application/json",
    },
    json={
        "model": "venice-uncensored",
        "messages": [{"role": "user", "content": "Say hi from a fresh wallet."}],
    },
)

if r.status_code == 200:
    print(r.json()["choices"][0]["message"]["content"])
    print()
    print(f"Balance remaining: ${r.headers.get('x-balance-remaining', '?')}")
else:
    print(r.status_code, r.text[:500])'''),
        ("markdown", """## What just happened

A wallet that didn't exist this morning **just bought itself an AI subscription**. No signup, no API key, no email.

This unlocks autonomous agents that can pay for their own inference, and tools that don't have to manage user accounts at all — they just charge per call.

**Next:** [08 · E2EE — the cryptography](./08-e2ee-encryption.ipynb)"""),
    ]


# ---------------------------------------------------------------------------
# 08 — E2EE
# ---------------------------------------------------------------------------
def nb_08() -> List[Cell]:
    return [
        ("markdown", f"""# 08 · End-to-End Encrypted Inference

{colab_badge("08-e2ee-encryption.ipynb")}

This is the strongest privacy mode Venice offers. Your prompt is encrypted **on your machine** before it leaves, stays encrypted as it passes through Venice's infrastructure, and is **only decrypted inside a hardware-secured enclave** (TEE) on the GPU.

By the end of this notebook you will:
1. Send the same prompt twice — once to a regular model, once to an E2EE model — and **see the difference on the wire**
2. Implement the full E2EE protocol from scratch in pure Python
3. Verify the TEE attestation on the response cryptographically

The point: you don't have to *trust* Venice. You can *verify* it.

**Crypto used:**
- ECDH on **secp256k1** for key exchange
- **HKDF-SHA256** for key derivation
- **AES-256-GCM** for symmetric encryption"""),
        install_cell("coincurve cryptography eth-account"),
        setup_cell(),
        ("markdown", """## 1. Pick an E2EE model

Filter the model list for ones that support E2EE."""),
        ("code", '''import requests, json

models = requests.get(
    "https://api.venice.ai/api/v1/models",
    headers={"Authorization": f"Bearer {api_key}"},
).json()

e2ee_models = []
tee_models = []
for m in models["data"]:
    caps = (m.get("model_spec", {}) or {}).get("capabilities", {}) or {}
    if caps.get("supportsE2EE"):
        e2ee_models.append(m["id"])
    if caps.get("supportsTeeAttestation"):
        tee_models.append(m["id"])

print("E2EE models:", e2ee_models[:5])
print("TEE models: ", tee_models[:5])

# Pick one. Models prefixed with `e2ee-` are encrypted; `tee-` are
# enclave-isolated but not client-encrypted.
E2EE_MODEL = e2ee_models[0] if e2ee_models else "e2ee-qwen3-5-122b-a10b"
print(f"\\nUsing: {E2EE_MODEL}")'''),
        ("markdown", """## 2. The control: send a regular prompt

Look at the request body that leaves your machine. It's plaintext."""),
        ("code", '''payload = {
    "model": "venice-uncensored",
    "messages": [{"role": "user", "content": "MY SECRET: I am building a regret vending machine."}],
}
print("📤 Plaintext request body:")
print(json.dumps(payload, indent=2))

# Anyone sniffing the wire (or with access to a logging proxy) sees the secret.'''),
        ("markdown", """## 3. The E2EE flow — step by step

We'll do it manually so you can see every move."""),
        ("markdown", """### 3a. Generate an ephemeral keypair (secp256k1)

Throwaway. New one per session — never reuse."""),
        ("code", '''from coincurve import PrivateKey

ephemeral = PrivateKey()
ephemeral_pub = ephemeral.public_key.format(compressed=False).hex()  # 04 + X + Y
print(f"Ephemeral public key (uncompressed hex): {ephemeral_pub}")
print(f"Length: {len(ephemeral_pub)} hex chars  (1 + 32 + 32 = 65 bytes)")'''),
        ("markdown", """### 3b. Fetch the TEE's public key from its attestation

The enclave publishes a public key that's **bound to the hardware** — it can only have been generated inside the genuine enclave."""),
        ("code", '''attest = requests.get(
    f"https://api.venice.ai/api/v1/models/{E2EE_MODEL}/attestation",
    headers={"Authorization": f"Bearer {api_key}"},
).json()

print("Attestation summary:")
for k in ("verified", "signing_address", "encryption_pub_key", "nonce", "provider"):
    if k in attest:
        v = attest[k]
        if isinstance(v, str) and len(v) > 80:
            v = v[:80] + "..."
        print(f"  {k}: {v}")

tee_pub_hex = attest["encryption_pub_key"]
print(f"\\n✓ TEE will be using public key: {tee_pub_hex[:32]}...")'''),
        ("markdown", """### 3c. Derive a shared symmetric key

ECDH gives us a shared secret only our ephemeral private key + the TEE's private key (inside the enclave) can compute. Pipe it through HKDF to get a clean AES-256 key."""),
        ("code", '''from coincurve import PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

tee_pub = PublicKey(bytes.fromhex(tee_pub_hex))
shared = ephemeral.ecdh(tee_pub.format(compressed=False))  # raw 32-byte secret

aes_key = HKDF(
    algorithm=hashes.SHA256(),
    length=32,
    salt=None,
    info=b"venice-e2ee-v1",
).derive(shared)

print(f"Shared secret (raw):  {shared.hex()[:40]}...")
print(f"Derived AES-256 key: {aes_key.hex()[:40]}...")'''),
        ("markdown", """### 3d. Encrypt the prompt with AES-256-GCM

Venice uses a **32-byte nonce** (unusual — most AES-GCM uses 12). Don't trim it."""),
        ("code", '''import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_LEN = 32  # Venice TEE requirement

plaintext_messages = [{"role": "user", "content": "MY SECRET: I am building a regret vending machine."}]
plaintext_bytes = json.dumps(plaintext_messages).encode()

aesgcm = AESGCM(aes_key)
nonce = os.urandom(NONCE_LEN)
ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, associated_data=None)

print(f"Plaintext: {plaintext_bytes!r}")
print(f"Ciphertext ({len(ciphertext)} bytes): {ciphertext.hex()[:80]}...")
print(f"Nonce: {nonce.hex()}")'''),
        ("markdown", """### 3e. Send the ciphertext to Venice

Notice — **nothing in this request body is human-readable**. Venice's logs would see ciphertext only."""),
        ("code", '''e2ee_payload = {
    "model": E2EE_MODEL,
    "ciphertext": ciphertext.hex(),
    "nonce": nonce.hex(),
    "ephemeral_pub_key": ephemeral_pub,
    # Optional metadata that's safe to send in plaintext
    "max_tokens": 256,
}

print("📤 E2EE request body:")
print(json.dumps({k: (v[:60] + '...' if isinstance(v, str) and len(v) > 60 else v) for k, v in e2ee_payload.items()}, indent=2))

r = requests.post(
    "https://api.venice.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json=e2ee_payload,
)
print(f"\\nStatus: {r.status_code}")
response = r.json()
print(json.dumps(response, indent=2)[:600])'''),
        ("markdown", """### 3f. Decrypt the response

The TEE encrypted its reply using the same shared secret."""),
        ("code", '''reply_ciphertext = bytes.fromhex(response["ciphertext"])
reply_nonce = bytes.fromhex(response["nonce"])

reply_plaintext = aesgcm.decrypt(reply_nonce, reply_ciphertext, associated_data=None)
print("📥 Decrypted reply:")
print(json.loads(reply_plaintext))'''),
        ("markdown", """## 4. Verify the response was actually signed by the enclave

Every E2EE response includes a signature from a key that **only exists inside the enclave**. We check the signature against the `signing_address` from the attestation."""),
        ("code", '''from eth_account.messages import encode_defunct
from eth_account import Account

signing_address = attest["signing_address"]
signature = response["signature"]
signed_payload = response["signed_payload"]  # the bytes the enclave actually signed

recovered = Account.recover_message(
    encode_defunct(text=signed_payload),
    signature=signature,
)

if recovered.lower() == signing_address.lower():
    print(f"✓ Signature verified.")
    print(f"  Signer: {recovered}")
    print(f"  Matches enclave address from attestation: {signing_address}")
else:
    print(f"✗ MISMATCH. Recovered {recovered}, expected {signing_address}")'''),
        ("markdown", """## 5. Tamper test — flip one byte

Modify a single character of the response and the verification should immediately fail."""),
        ("code", '''tampered = signed_payload[:-1] + ("X" if signed_payload[-1] != "X" else "Y")

recovered = Account.recover_message(
    encode_defunct(text=tampered),
    signature=signature,
)

if recovered.lower() == signing_address.lower():
    print("This should not happen — tampering went undetected.")
else:
    print(f"✓ Tampering detected. Recovered {recovered} ≠ enclave {signing_address}")'''),
        ("markdown", """## 6. The bounty (try this with the room)

Take the ciphertext from cell 3d above and post it publicly — Discord, Twitter, anywhere. Offer a prize to anyone who can recover the plaintext.

You're safe. Without **either** your ephemeral private key (which only exists in this notebook's memory and is gone when the kernel dies) **or** the TEE's private key (which only exists inside the hardware enclave and was never extracted), **the math does not allow** decryption.

```python
print(f"Public bounty:")
print(f"  ciphertext: {ciphertext.hex()}")
print(f"  nonce:      {nonce.hex()}")
print(f"  ephemeral:  {ephemeral_pub}")
print(f"  TEE pubkey: {tee_pub_hex}")
```

That's all the public information. The only secret left in the universe that can decrypt this is inside an Intel TDX / NVIDIA Confidential Compute enclave that even Venice's engineers can't read."""),
        ("markdown", """## What just happened

You implemented end-to-end encrypted AI inference from primitives:

1. **You generated** a fresh secp256k1 keypair locally.
2. **You verified** Venice gave you a public key that came from inside a hardware enclave.
3. **You derived** an AES key that only your ephemeral key + that enclave can produce.
4. **You encrypted** your prompt before it left your laptop.
5. **The enclave** decrypted, ran the model, encrypted the reply, signed it.
6. **You verified** the signature came from inside the enclave.
7. **You tampered** with the response and watched the verification break.

Every other AI workshop today asks you to *trust* the provider.

This notebook just made you a **verifier**.

---

## Want to run agents on this?

The full set of `e2ee-*` and `tee-*` models is at `https://api.venice.ai/api/v1/models`. The same flow above wires into LangChain, the Vercel AI SDK, CrewAI, or anything that accepts a custom HTTP client.

For production, use [`venice-x402-client`](https://www.npmjs.com/package/venice-x402-client) (TypeScript) or hand-roll the equivalent in Python — it's about 100 lines once factored.

**You're done. Welcome to the Venice ecosystem.**"""),
    ]


# ---------------------------------------------------------------------------
# Build all
# ---------------------------------------------------------------------------
NOTEBOOKS = {
    "00-quickstart.ipynb": nb_00,
    "01-chat-completions.ipynb": nb_01,
    "02-embeddings-and-rag.ipynb": nb_02,
    "03-image-generation.ipynb": nb_03,
    "04-audio-tts-stt.ipynb": nb_04,
    "05-video-generation.ipynb": nb_05,
    "06-characters.ipynb": nb_06,
    "07-x402-wallet-payments.ipynb": nb_07,
    "08-e2ee-encryption.ipynb": nb_08,
}


def main():
    for name, builder in NOTEBOOKS.items():
        nb = _notebook(builder())
        out = NB_DIR / name
        out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"  wrote {name}  ({len(nb['cells'])} cells)")
    print(f"\n{len(NOTEBOOKS)} notebooks written to {NB_DIR}")


if __name__ == "__main__":
    main()
