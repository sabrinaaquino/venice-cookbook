"""04 - Audio. Tour every Venice TTS engine, drive emotion with prompt-based control,
segment long files, and use the OpenAI cookbook's baseline vs post-processed transcription
pattern to fix domain-specific STT errors.
"""

from ._common import Cell, header, install_cell, setup_cell


NOTEBOOK = "04-audio-tts-stt.ipynb"


def cells() -> list[Cell]:
    return [
        ("markdown", header(
            NOTEBOOK,
            "Audio: 10 TTS engines, emotion by prompt, and the post-processing trick",
            "Venice ships 10 text-to-speech models (Kokoro, Qwen 3, xAI, Inworld, Chatterbox HD, "
            "Orpheus, ElevenLabs Turbo, MiniMax HD, Gemini Flash) and several ASR engines "
            "(Parakeet, Whisper, Wizper, Scribe, xAI). We will tour them side by side, drive "
            "emotion via the `prompt` parameter on Qwen 3, and use the OpenAI cookbook pattern of "
            "post-processing transcripts to fix domain spellings.",
        )),
        ("markdown",
            "## What you will build\n\n"
            "1. **Live TTS catalog** pulled from `/models?type=tts`, with voice counts per engine.\n"
            "2. **Same line, five engines** so you can A/B voices in one ear-pass.\n"
            "3. **Prompt-controlled emotion** on Qwen 3 TTS: same text, same voice, four deliveries.\n"
            "4. **Two-host podcast intro** built by stitching xAI clips with pydub.\n"
            "5. **Silence trimming + segmentation** for anything longer than 30 seconds.\n"
            "6. **Baseline vs post-processed STT** with xAI transcription + a chat pass that fixes "
            "brand and acronym spellings.\n\n"
            "Cost: TTS is cents per call, STT is fractions of a cent per second."),
        ("markdown", "## Setup"),
        install_cell("pydub"),
        setup_cell(),
        ("code",
            '''import requests
from pathlib import Path
from IPython.display import Audio, display
import pandas as pd

OUT = Path("assets_audio")
OUT.mkdir(exist_ok=True)
API = "https://api.venice.ai/api/v1"
H   = {"Authorization": f"Bearer {api_key}"}

print("Helpers ready.")'''),
        ("markdown",
            "## 1. Live TTS catalog\n\n"
            "Instead of hard-coding a voice list that goes stale, pull it from `/models?type=tts` "
            "every run. Each model advertises its own voice set (Kokoro has 54, Gemini Flash 30, "
            "MiniMax 15, and so on)."),
        ("code",
            '''r = requests.get(f"{API}/models", params={"type": "tts"}, headers=H, timeout=30)
r.raise_for_status()

# Per the /audio/speech docs, these flags control which optional params each engine honors.
SUPPORTS_PROMPT      = {"tts-qwen3-0-6b", "tts-qwen3-1-7b"}
SUPPORTS_TEMPERATURE = {"tts-qwen3-0-6b", "tts-qwen3-1-7b", "tts-orpheus", "tts-chatterbox-hd"}

rows = []
for m in r.json().get("data", []):
    spec   = m.get("model_spec") or {}
    voices = spec.get("voices") or spec.get("availableVoices") or []
    rows.append({
        "model":        m["id"],
        "voices":       len(voices),
        "sample voice": (voices[:1] or [""])[0],
        "prompt?":      m["id"] in SUPPORTS_PROMPT,
        "temperature?": m["id"] in SUPPORTS_TEMPERATURE,
    })

tts_catalog = pd.DataFrame(rows).sort_values("voices", ascending=False).reset_index(drop=True)
tts_catalog'''),
        ("markdown",
            "## 2. Same line, five engines\n\n"
            "Identical text, five different TTS models, so you can hear how each engine sounds. Pick "
            "your favorite for the rest of the notebook."),
        ("code",
            '''LINE = "Welcome to Venice. This audio was generated with no logs, no retention, and no account required."

_EXT_FROM_CT = {"audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/wav": "wav",
                "audio/x-wav": "wav", "audio/flac": "flac", "audio/ogg": "ogg"}

def speak(text: str, *, model: str, voice: str, out_stem: str,
          prompt: str | None = None, temperature: float | None = None,
          response_format: str = "mp3") -> Path:
    """Returns the path of the saved audio. Extension is picked from the response
    content-type (some engines ignore response_format and always return mp3)."""
    body: dict = {"model": model, "voice": voice, "input": text,
                  "response_format": response_format}
    if prompt is not None:
        body["prompt"] = prompt           # emotion/delivery on Qwen 3 TTS
    if temperature is not None:
        body["temperature"] = temperature # variation on Qwen 3 / Orpheus / Chatterbox HD

    r = requests.post(f"{API}/audio/speech",
                      headers={**H, "Content-Type": "application/json"},
                      json=body, timeout=120)
    r.raise_for_status()
    ext = _EXT_FROM_CT.get(r.headers.get("content-type", "").split(";")[0], response_format)
    path = OUT / f"{out_stem}.{ext}"
    path.write_bytes(r.content)
    return path

ENGINES = [
    ("tts-xai-v1",                "leo",      "xAI Grok voice, broadcast-ready"),
    ("tts-kokoro",                "am_echo",  "Kokoro, 54 voices, multilingual"),
    ("tts-elevenlabs-turbo-v2-5", "Brian",    "ElevenLabs Turbo, most expressive"),
    ("tts-gemini-3-1-flash",      "Achernar", "Gemini Flash, huge voice pool"),
    ("tts-inworld-1-5-max",       "Craig",    "Inworld, game-ready characters"),
]

for i, (model, voice, note) in enumerate(ENGINES):
    p = speak(LINE, model=model, voice=voice, out_stem=f"engine_{i:02d}")
    print(f"[{model}] {voice}  -  {note}   -> {p.name}")
    display(Audio(str(p)))'''),
        ("markdown",
            "## 3. Drive emotion with a prompt\n\n"
            "Venice's **Qwen 3 TTS** models advertise `supportsPromptParam: true`. That means you "
            "can pass a style instruction (up to 500 chars) alongside the text, and the model will "
            "adjust delivery to match. Same voice, same line, four very different takes:"),
        ("code",
            '''SAME_LINE  = "Our latest model beats every benchmark in its class."
SAME_VOICE = "Serena"
QWEN_MODEL = "tts-qwen3-1-7b"

PROMPTS = [
    ("neutral",    None),
    ("excited",    "Excited and energetic, like announcing a product launch on stage."),
    ("whisper",    "Whispered and conspiratorial, as if sharing a secret with one person."),
    ("sarcastic",  "Dry and sarcastic, with a small scoff in the delivery."),
]

for label, prompt in PROMPTS:
    p = speak(SAME_LINE, model=QWEN_MODEL, voice=SAME_VOICE, prompt=prompt,
              temperature=0.9, out_stem=f"emotion_{label}")
    print(f"[{label}]  prompt={prompt!r}")
    display(Audio(str(p)))'''),
        ("markdown",
            "Models that do **not** advertise `supportsPromptParam` (xAI, ElevenLabs, Gemini, "
            "Kokoro, and friends) silently ignore the `prompt` field. To change their delivery you "
            "either pick a different voice or rewrite the text itself (add punctuation, ellipses, "
            "stage directions in brackets, etc.)."),
        ("markdown",
            "## 4. Two-host podcast intro\n\n"
            "Stitch multiple TTS calls into a single file with pydub. We use **Kokoro** here because "
            "it returns WAV natively, which means pydub does not need ffmpeg to read the clips. "
            "(xAI and most other engines return MP3, which pydub can still handle if ffmpeg is on "
            "your PATH. Colab has ffmpeg preinstalled, local Windows usually does not.)"),
        ("code",
            '''from pydub import AudioSegment

SCRIPT = [
    ("am_echo",     "Welcome to Private by Default, the show where we put privacy back into AI."),
    ("af_bella",    "Today on the show: end-to-end encrypted inference. What it actually means and why your hospital should care."),
    ("am_echo",     "Plus: a live demo where we encrypt a prompt on the client and watch Venice generate a reply they cannot read."),
    ("af_bella",    "Stick around. This is going to be fun."),
]

clips = []
for i, (voice, line) in enumerate(SCRIPT):
    p = speak(line, model="tts-kokoro", voice=voice, out_stem=f"podcast_{i}",
              response_format="wav")
    clips.append(AudioSegment.from_wav(p))

gap = AudioSegment.silent(duration=180, frame_rate=clips[0].frame_rate)
intro = clips[0]
for c in clips[1:]:
    intro += gap + c

podcast_path = OUT / "podcast_intro.wav"
intro.export(podcast_path, format="wav")
print(f"Podcast: {len(intro)/1000:.1f}s")
display(Audio(str(podcast_path)))'''),
        ("markdown",
            "## 5. Silence trimming and segmentation\n\n"
            "Long files trip up STT in two ways: leading silence confuses the start, and >30s of "
            "audio in one shot hurts accuracy. The OpenAI cookbook fix is to trim leading silence "
            "and chunk into 60-second segments. Same pattern in 20 lines:"),
        ("code",
            '''def first_sound_ms(sound: AudioSegment, threshold_db: float = -35.0, step_ms: int = 10) -> int:
    """Return the offset in ms where audio first crosses `threshold_db`."""
    t = 0
    while t < len(sound) and sound[t:t + step_ms].dBFS < threshold_db:
        t += step_ms
    return t

def trim_and_segment(audio: AudioSegment, segment_seconds: int = 60) -> list[AudioSegment]:
    start = first_sound_ms(audio)
    trimmed = audio[start:]
    seg_ms = segment_seconds * 1000
    return [trimmed[i:i + seg_ms] for i in range(0, len(trimmed), seg_ms)]

segments = trim_and_segment(intro, segment_seconds=15)
print(f"Trimmed leading silence, split into {len(segments)} segment(s).")'''),
        ("markdown",
            "## 6. Baseline transcription\n\n"
            "Run xAI STT on the podcast we just generated. Expect domain words like \"Venice\" and "
            "\"TEE\" to occasionally come out wrong. That is what the next step fixes."),
        ("code",
            '''def transcribe(path: Path, *, model: str = "stt-xai-v1") -> str:
    with open(path, "rb") as f:
        files = {"file": (path.name, f.read(), "audio/wav")}
    r = requests.post(f"{API}/audio/transcriptions",
                      headers=H, files=files,
                      data={"model": model, "response_format": "text"},
                      timeout=60)
    r.raise_for_status()
    try:
        return r.json().get("text", "").strip()
    except Exception:
        return r.text.strip()

baseline = transcribe(podcast_path)
print(baseline)'''),
        ("markdown",
            "Other ASR engines available on Venice in case you want to A/B: "
            "`nvidia/parakeet-tdt-0.6b-v3` (fastest), `openai/whisper-large-v3` "
            "(most accurate general-purpose), `fal-ai/wizper`, `elevenlabs/scribe-v2`. Swap the "
            "`model` arg above to try them."),
        ("markdown",
            "## 7. Post-processed transcription\n\n"
            "Pipe the raw transcript through a chat call with a glossary of domain terms. The model "
            "fixes brand names, acronyms, and capitalization in one pass. Same trick the OpenAI "
            "cookbook uses for ZyntriQix product SKUs, applied to our world."),
        ("code",
            '''GLOSSARY = """
Domain terms that must appear exactly as written:
- Venice (the AI platform; never "Vinnies" or "Venezia")
- TEE (Trusted Execution Environment, always uppercase)
- E2EE (End-to-End Encryption, always uppercase)
- x402 (the protocol; lowercase x, no space)
- DIEM (the Venice credit token, always uppercase)
- Kimi, Kokoro, Qwen (model names, capitalize)
"""

def postprocess(transcript: str) -> str:
    r = client.chat.completions.create(
        model="kimi-k2-6",
        messages=[
            {"role": "system", "content": (
                "You correct speech-to-text transcripts. Fix capitalization, punctuation, and "
                "domain term spellings using the glossary. Do NOT add or remove content.\\n"
                + GLOSSARY
            )},
            {"role": "user", "content": transcript},
        ],
        temperature=0,
    )
    return r.choices[0].message.content.strip()

cleaned = postprocess(baseline)

print("BEFORE:\\n", baseline)
print()
print("AFTER:\\n", cleaned)'''),
        ("markdown",
            "Side by side as a DataFrame so you can copy it into a deck:"),
        ("code",
            '''pd.DataFrame({
    "version":    ["raw STT", "STT + post-process"],
    "transcript": [baseline, cleaned],
})'''),
        ("markdown",
            "## Recap\n\n"
            "- **Voices live in the API.** Pull `/models?type=tts` at runtime; do not hard-code.\n"
            "- **Pick an engine for the vibe**, not the voice name. xAI is broadcast-ready, Kokoro "
            "is multilingual, ElevenLabs is the most expressive, Gemini has the biggest pool.\n"
            "- **Qwen 3 TTS is the only family that takes a `prompt`** for emotion/delivery today. "
            "On everything else the field is silently ignored, so fall back to text rewriting or "
            "voice selection.\n"
            "- **Post-process your STT.** It is the cheapest 90% accuracy boost you will ever get.\n\n"
            "Next: `05-video-generation.ipynb`."),
    ]
