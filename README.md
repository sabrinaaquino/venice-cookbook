# Base Batches × Venice — Workshop

> Build with private, uncensored, multimodal AI on Base — endpoints, x402, E2EE, DIEM.

A hands-on workshop for the [Base Batches 003](https://batches.base.org/) cohort. Nine self-contained Python notebooks that walk through every Venice endpoint, including the things that make Venice different — **x402 wallet payments** (no API key, pay per call in USDC on Base) and **E2EE inference** with **provable privacy** (encrypt client-side, only a hardware enclave can decrypt).

Every notebook runs in **Google Colab** with one click — no local setup needed.

---

## Notebooks

| # | Notebook | What you'll learn | Open in Colab |
|---|---|---|---|
| 00 | [Quickstart](notebooks/00-quickstart.ipynb) | First call. List models. Inspect Venice headers. | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sabrinaaquino/base-batches-workshop/blob/main/notebooks/00-quickstart.ipynb) |
| 01 | [Chat Completions](notebooks/01-chat-completions.ipynb) | Streaming, system prompts, web search, reasoning, JSON schema, vision, tool calling. | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sabrinaaquino/base-batches-workshop/blob/main/notebooks/01-chat-completions.ipynb) |
| 02 | [Embeddings + RAG](notebooks/02-embeddings-and-rag.ipynb) | Vector search on the BB003 cohort. Mini RAG pipeline in 10 lines. | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sabrinaaquino/base-batches-workshop/blob/main/notebooks/02-embeddings-and-rag.ipynb) |
| 03 | [Image Generation](notebooks/03-image-generation.ipynb) | Generate, style preset, edit, upscale. | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sabrinaaquino/base-batches-workshop/blob/main/notebooks/03-image-generation.ipynb) |
| 04 | [Audio (TTS + STT)](notebooks/04-audio-tts-stt.ipynb) | Voice memo → script → narrated commercial. | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sabrinaaquino/base-batches-workshop/blob/main/notebooks/04-audio-tts-stt.ipynb) |
| 05 | [Video Generation](notebooks/05-video-generation.ipynb) | Async queue + poll for text-to-video. | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sabrinaaquino/base-batches-workshop/blob/main/notebooks/05-video-generation.ipynb) |
| 06 | [Characters](notebooks/06-characters.ipynb) | Use prebuilt AI personas. | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sabrinaaquino/base-batches-workshop/blob/main/notebooks/06-characters.ipynb) |
| 07 | [x402 Wallet Payments](notebooks/07-x402-wallet-payments.ipynb) | No API key. Pay per call in USDC on Base. | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sabrinaaquino/base-batches-workshop/blob/main/notebooks/07-x402-wallet-payments.ipynb) |
| 08 | [End-to-End Encryption](notebooks/08-e2ee-encryption.ipynb) | Full ECDH + HKDF + AES-GCM in pure Python. Verify TEE attestation. | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sabrinaaquino/base-batches-workshop/blob/main/notebooks/08-e2ee-encryption.ipynb) |

---

## Quickstart

### Option A — Run in Colab (recommended)

1. Click any **Open in Colab** badge above.
2. In Colab, open the **🔑 Secrets** panel (left sidebar) and add:
   - `VENICE_API_KEY` — get one at [venice.ai/settings/api](https://venice.ai/settings/api)
   - `WALLET_PRIVATE_KEY` *(only needed for notebook 07)* — a Base wallet private key
3. Run each cell.

### Option B — Run locally

```bash
git clone https://github.com/sabrinaaquino/base-batches-workshop.git
cd base-batches-workshop

python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env       # then fill in your Venice API key

jupyter notebook
```

---

## What's inside

```
base-batches-workshop/
├── README.md                          ← you are here
├── requirements.txt                   ← all Python deps
├── .env.example                       ← template for local secrets
├── helpers/
│   └── venice.py                      ← shared client setup (env / Colab / .env)
├── notebooks/
│   ├── 00-quickstart.ipynb
│   ├── 01-chat-completions.ipynb
│   ├── 02-embeddings-and-rag.ipynb
│   ├── 03-image-generation.ipynb
│   ├── 04-audio-tts-stt.ipynb
│   ├── 05-video-generation.ipynb
│   ├── 06-characters.ipynb
│   ├── 07-x402-wallet-payments.ipynb
│   └── 08-e2ee-encryption.ipynb
├── build_notebooks.py                 ← single source of truth for all notebooks
└── validate_notebooks.py              ← syntax-checks every code cell
```

The notebooks themselves are generated from `build_notebooks.py`. To edit them, edit that file and re-run:

```bash
python build_notebooks.py
python validate_notebooks.py
```

---

## Why Venice on Base?

- **Same SDK as OpenAI** — change one URL, you're done.
- **Privacy you can verify** — TEE & E2EE inference signed by hardware enclaves. Math, not promises.
- **Pay with USDC** — no API key, no signup, no email. x402 turns your Base wallet into your account.
- **DIEM** — lock VVV → mint DIEM → perpetual $1/day API credit. Tradeable. Forever.
- **Uncensored** — open-source models with no content filters. Build the apps other providers won't ship.

---

## Resources

- 📚 [Venice API docs](https://docs.venice.ai/)
- 🔒 [Privacy architecture](https://venice.ai/privacy)
- 💸 [x402 guide](https://docs.venice.ai/overview/guides/x402-venice-api)
- 🔐 [TEE & E2EE guide](https://docs.venice.ai/overview/guides/tee-e2ee-models)
- 💎 [DIEM tokenomics](https://venice.ai/lp/diem)
- 💬 [Venice Discord](https://discord.gg/venice-ai)

---

## License

MIT — see [LICENSE](LICENSE).

Built with ♥ for [Base Batches 003](https://batches.base.org/) by the Venice team.
