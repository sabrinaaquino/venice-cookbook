"""08 - End-to-end encrypted inference. The headliner.

Walks from plain-English explainer -> TEE-only (zero crypto work on the client)
-> full E2EE handshake (secp256k1 ECDH + HKDF + AES-256-GCM + per-chunk decrypt).
"""

from ._common import Cell, header, install_cell, setup_cell


NOTEBOOK = "08-e2ee-encryption.ipynb"


def cells() -> list[Cell]:
    return [
        ("markdown", header(
            NOTEBOOK,
            "Private inference you can verify: TEE and E2EE on Venice",
            "Most AI providers ask you to trust them. Venice gives you two provable privacy modes: "
            "**TEE** (inference runs inside a hardware-sealed enclave, one line of code to use) and "
            "**E2EE** (plus client-side encryption so even Venice's network sees only ciphertext). "
            "We will run both in pure Python and inspect every byte.",
        )),
        ("markdown",
            "## What you will build\n\n"
            "1. **A privacy mode comparison table** so you know what each tier guarantees.\n"
            "2. **A plain-English explainer** of what a TEE actually is and why attestation matters.\n"
            "3. **TEE-only mode**: one normal chat call + an attestation check. The easiest "
            "provable-privacy win you will ever get.\n"
            "4. **Full E2EE**: discover an `e2ee-*` model, pull a hardware-attested key, do "
            "secp256k1 ECDH + HKDF + AES-256-GCM in 30 lines of Python.\n"
            "5. **Send an encrypted prompt** with the right `X-Venice-TEE-*` headers and "
            "**decrypt the streamed reply** chunk by chunk.\n"
            "6. **Side-by-side diff** of what Venice's network sees in private vs TEE vs E2EE mode.\n\n"
            "Cost: zero extra. TEE and E2EE are included on Pro tiers."),
        ("markdown",
            "## Privacy modes at a glance\n\n"
            "| Mode | Who can read your prompt | Hardware proof | How to opt in |\n"
            "|---|---|---|---|\n"
            "| Anonymized (3rd party) | 3rd party provider only, never linked to you | no | default for proxied frontier models |\n"
            "| Private (Venice default) | Venice infra for the duration of inference, then discarded | no | default for open-source models |\n"
            "| **TEE** | Only the verified enclave. Even Venice operators cannot read it | yes (remote attestation) | use a `tee-*` or `e2ee-*` model id, send normal requests |\n"
            "| **E2EE** | Encrypted on your device first. Even Venice's network sees only ciphertext | yes (attestation + ECDH) | use an `e2ee-*` model id with encryption headers |\n\n"
            "Anonymized and Private are enforced by **policy**. TEE and E2EE are enforced by "
            "**hardware and cryptography**. You do not have to trust Venice, you verify."),
        ("markdown",
            "## How this actually works (the plain-English version)\n\n"
            "Three mental models. Pick whichever sticks.\n\n"
            "**The locked vault analogy.** A TEE is a locked vault built into the chip itself "
            "(Intel TDX on the CPU side, NVIDIA Confidential Computing on the GPU side). Once code "
            "is running inside, even the person who owns the physical server cannot look in. The "
            "memory is encrypted, the debug ports are disabled, and the chip refuses to run unless "
            "the vault is intact.\n\n"
            "**The tamper-evident sticker (attestation).** Every vault ships with a signed "
            "certificate from the chip manufacturer that says \"I am a genuine vault, and the code "
            "inside me hashes to exactly X.\" You send a random nonce, the chip includes your "
            "nonce in its signed certificate, and you verify the signature. If someone swapped the "
            "code, the hash changes and the check fails. If someone replays an old certificate, "
            "the nonce does not match. This is what `/tee/attestation` returns.\n\n"
            "**The mail analogy.**\n"
            "- **Private mode:** you hand Venice an open postcard. Venice promises to read it, "
            "reply, and forget it happened. Trust us.\n"
            "- **TEE mode:** you hand Venice an open postcard. Venice does not read it, it drops "
            "it straight into a sealed robot that reads, replies, and shreds. The robot has a "
            "factory-signed receipt proving it has not been tampered with. Trust the chip, not Venice.\n"
            "- **E2EE mode:** you seal the postcard in an envelope that only the robot can open, "
            "then hand it to Venice. Now even a Venice employee tapping the network wire sees only "
            "the envelope. Trust nothing but math.\n\n"
            "### So when is TEE alone enough?\n\n"
            "TEE-only is the right pick for most business use cases: legal, medical, financial, "
            "HR, source code. Your prompt travels over TLS to Venice, goes straight into the "
            "enclave without Venice infra retaining a copy, and the enclave's integrity is "
            "verifiable. Plus you keep every feature (web search, function calling, file uploads, "
            "non-streaming), which E2EE has to disable.\n\n"
            "You step up to **E2EE** when your threat model includes a compromise of Venice's "
            "front door itself (a rogue engineer, a malicious TLS middlebox, a court order for "
            "network taps), or when your compliance team wants \"zero-knowledge\" on paper. In "
            "E2EE, even if every network link at Venice were wiretapped, the attacker gets hex.\n\n"
            "The rest of the notebook makes all three modes concrete."),
        ("markdown", "## Setup"),
        install_cell("ecdsa cryptography"),
        setup_cell(),
        ("code",
            '''import json, secrets, requests, re
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from ecdsa import SECP256k1, VerifyingKey, SigningKey

API_BASE  = "https://api.venice.ai/api/v1"
HEADERS   = {"Authorization": f"Bearer {api_key}"}
HKDF_INFO = b"ecdsa_encryption"  # Venice's fixed HKDF info string'''),
        ("markdown",
            "## 1. Discover TEE and E2EE capable models\n\n"
            "The capability flags on `/models` are the source of truth. Every `e2ee-*` model also "
            "supports plain TEE mode, which means the same model id can be called two ways. You "
            "pick the mode per request based on how much effort you want to do on the client."),
        ("code",
            '''import pandas as pd

models = requests.get(f"{API_BASE}/models", headers=HEADERS, timeout=30).json()["data"]
capable = [m for m in models
           if m.get("model_spec", {}).get("capabilities", {}).get("supportsTeeAttestation")
           or m.get("model_spec", {}).get("capabilities", {}).get("supportsE2EE")]

pd.DataFrame([{
    "model": m["id"],
    "ctx":   m["model_spec"].get("availableContextTokens"),
    "tee":   m["model_spec"]["capabilities"].get("supportsTeeAttestation", False),
    "e2ee":  m["model_spec"]["capabilities"].get("supportsE2EE", False),
} for m in capable])'''),
        ("code",
            '''MODEL = "e2ee-glm-4-7-flash-p"  # pick any from the table above; this one is fast
print("Using:", MODEL)'''),
        ("markdown",
            "## 2. TEE-only mode: one line of code\n\n"
            "If your threat model is \"I trust the wire to Venice, I do not trust the box the "
            "model runs on\" (that is, you are OK with TLS and standard policy for transit but "
            "want hardware-enforced isolation during inference), TEE-only mode is the answer. "
            "**No client crypto, no special headers, no streaming requirement.** Just use the "
            "`e2ee-*` (or `tee-*`) model id with the regular OpenAI SDK and you are done."),
        ("code",
            '''PROMPT = (
    "I am a doctor reviewing a patient case. The patient is a 47-year-old female with "
    "chest pain radiating to the left arm. Suggest a differential diagnosis in 3 bullets."
)

tee_response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": PROMPT}],
)
print(tee_response.choices[0].message.content)
print()
print(f"(request id: {tee_response.id})")'''),
        ("markdown",
            "That call was routed straight into a hardware enclave. Your prompt was never written "
            "to Venice's logs, never cached on disk, and is unreadable to Venice operators. Now "
            "let us prove it instead of promising it."),
        ("markdown",
            "### Verify the enclave with an attestation check\n\n"
            "This is the \"show me the receipt\" step. We send a fresh 32-byte nonce (64 hex "
            "characters), the TEE signs it along with a hash of the code running inside, and the "
            "server verifies the Intel TDX quote before handing the response back. You can "
            "re-verify client-side in production."),
        ("code",
            '''nonce_hex = secrets.token_hex(32)  # 32 BYTES, 64 hex chars, fresh per check

att = requests.get(
    f"{API_BASE}/tee/attestation",
    params={"model": MODEL, "nonce": nonce_hex},
    headers=HEADERS,
    timeout=30,
).json()

assert att.get("verified") is True,    f"Attestation not verified: {att}"
assert att.get("nonce") == nonce_hex, "Nonce mismatch, possible replay attack"

print(f"verified        : {att.get('verified')}")
print(f"tee_provider    : {att.get('tee_provider')}     (Phala = Intel TDX partner)")
print(f"signing_address : {att.get('signing_address')}  (Ethereum-style hash of the enclave pubkey)")
print(f"model           : {att.get('model')}")
print(f"nonce matches   : {att.get('nonce') == nonce_hex}")'''),
        ("markdown",
            "### So what does that attestation actually prove?\n\n"
            "- **`verified: true`** means Venice checked the Intel TDX quote against Intel's "
            "signing chain and the code hash matches an approved enclave image.\n"
            "- **`nonce` matches yours** means this is a live enclave, not a replay of an old report.\n"
            "- **`signing_address`** is the Ethereum-style fingerprint of the enclave's public "
            "key. If you keep using that address across calls and it ever changes without a "
            "corresponding release note, you have a reason to be suspicious.\n\n"
            "If `verified` were `false`, the responsible move is to not send real data. The "
            "assertions above make that automatic."),
        ("markdown",
            "### When TEE alone is enough\n\n"
            "TEE-only is the right default for most production apps. You get:\n\n"
            "- Hardware isolation during inference (Venice operators and even the enclave host "
            "cannot read memory).\n"
            "- Cryptographic proof that the enclave has not been tampered with.\n"
            "- Full Venice feature set: web search, function calling, vision, file uploads, "
            "non-streaming, caching. E2EE has to disable most of those.\n"
            "- Zero extra code on your side. It is a normal chat completion call.\n\n"
            "The remaining trust assumption is that Venice's edge (the TLS terminator in front of "
            "the enclave) does not retain your plaintext in transit. Venice commits to this in its "
            "privacy architecture, and the enclave's attested code can refuse to answer if the "
            "request did not arrive through the expected path. If that residual trust is more "
            "than you want to hold, the next section removes it."),
        ("markdown",
            "## 3. Full E2EE: encrypt on the client, decrypt only inside the enclave\n\n"
            "We now encrypt the prompt ourselves before it leaves the machine, so Venice's network "
            "never sees plaintext even for a millisecond. The protocol:\n\n"
            "1. Generate an ephemeral secp256k1 keypair on the client.\n"
            "2. Ask `/tee/attestation` for the enclave's public key, verifying the nonce.\n"
            "3. ECDH + HKDF-SHA256 derive a shared AES-256-GCM key.\n"
            "4. Encrypt each message, hex-encode it, put it in `messages[i].content`.\n"
            "5. Send with three `X-Venice-TEE-*` headers and `stream=true`.\n"
            "6. Decrypt each streamed chunk with the same ECDH scheme against the enclave's "
            "per-chunk ephemeral key."),
        ("markdown",
            "### 3a. Generate your ephemeral keypair\n\n"
            "secp256k1 is the same curve as Bitcoin and Ethereum. The private key never leaves "
            "your machine. Regenerate per session; never reuse."),
        ("code",
            '''client_priv = SigningKey.generate(curve=SECP256k1)
client_pub  = client_priv.get_verifying_key()
client_pub_hex = (b"\\x04" + client_pub.to_string()).hex()  # 04 || x || y, 130 chars
print("Client public key (uncompressed, 130 hex chars):", client_pub_hex)'''),
        ("markdown",
            "### 3b. Fetch an E2EE attestation (includes `signing_key`)\n\n"
            "Same endpoint as before, but this time we need the `signing_key` field too: the "
            "enclave's secp256k1 public key that we will do ECDH against. Plain-TEE responses can "
            "omit this field; E2EE responses always include it."),
        ("code",
            '''nonce_hex = secrets.token_hex(32)

att = requests.get(
    f"{API_BASE}/tee/attestation",
    params={"model": MODEL, "nonce": nonce_hex},
    headers=HEADERS,
    timeout=30,
).json()

assert att.get("verified") is True,    f"Attestation not verified: {att}"
assert att.get("nonce") == nonce_hex, "Nonce mismatch, possible replay attack"

model_pub_key = att.get("signing_key") or att.get("signing_public_key")
assert model_pub_key, "This model did not return a signing_key; cannot do E2EE."

print(f"TEE provider    : {att.get('tee_provider')}")
print(f"Signing address : {att.get('signing_address')}")
print(f"Model pub key   : {model_pub_key[:20]} ... {model_pub_key[-10:]}")
print(f"Intel TDX quote : {str(att.get('intel_quote', ''))[:60]} ... (truncated)")'''),
        ("markdown",
            "### 3c. The encryption helper\n\n"
            "Fresh ephemeral keypair per message, ECDH with the enclave's key, HKDF-SHA256 with "
            "Venice's fixed info string `b\"ecdsa_encryption\"`, then AES-256-GCM. Wire format is "
            "`ephemeral_pub_key (65 bytes) || nonce (12 bytes) || ciphertext`, hex-encoded. That "
            "hex string goes into `messages[i].content`."),
        ("code",
            '''import os as _os

def _normalize_pub(hex_key: str) -> bytes:
    """Accept uncompressed (130 chars) or raw (128 chars) and return 65 bytes."""
    if len(hex_key) == 128:
        hex_key = "04" + hex_key
    if not hex_key.startswith("04") or len(hex_key) != 130:
        raise ValueError(f"Bad pubkey: len={len(hex_key)}")
    return bytes.fromhex(hex_key)

def encrypt_for_tee(plaintext: str, model_pub_hex: str) -> str:
    model_pub_bytes = _normalize_pub(model_pub_hex)
    model_vk = VerifyingKey.from_string(model_pub_bytes[1:], curve=SECP256k1)

    eph_priv = SigningKey.generate(curve=SECP256k1)
    eph_pub  = eph_priv.get_verifying_key()

    shared_pt     = model_vk.pubkey.point * eph_priv.privkey.secret_multiplier
    shared_secret = shared_pt.x().to_bytes(32, "big")

    aes_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=HKDF_INFO).derive(shared_secret)

    nonce  = _os.urandom(12)
    cipher = AESGCM(aes_key).encrypt(nonce, plaintext.encode(), None)

    eph_pub_bytes = b"\\x04" + eph_pub.to_string()  # 65 bytes
    return (eph_pub_bytes + nonce + cipher).hex()

# Inspect the wire format with a throwaway string
sample = encrypt_for_tee("What is the capital of France?", model_pub_key)
print("Ciphertext (hex):", sample[:80], "... total", len(sample), "chars")
print("First 130 hex chars = ephemeral pubkey, next 24 = nonce, rest = GCM ciphertext+tag.")'''),
        ("markdown",
            "### 3d. Send the E2EE request\n\n"
            "Three things make a request E2EE:\n\n"
            "1. The model id starts with `e2ee-`.\n"
            "2. Every `user` and `system` message has its `content` field encrypted (hex string).\n"
            "3. Three headers: `X-Venice-TEE-Client-Pub-Key`, `X-Venice-TEE-Model-Pub-Key`, "
            "`X-Venice-TEE-Signing-Algo: ecdsa`.\n\n"
            "E2EE **requires** `stream=true` so each delta chunk can be encrypted independently."),
        ("code",
            '''encrypted_messages = [
    {"role": "user", "content": encrypt_for_tee(PROMPT, model_pub_key)},
]

resp = requests.post(
    f"{API_BASE}/chat/completions",
    headers={
        **HEADERS,
        "Content-Type": "application/json",
        "X-Venice-TEE-Client-Pub-Key": client_pub_hex,
        "X-Venice-TEE-Model-Pub-Key":  model_pub_key,
        "X-Venice-TEE-Signing-Algo":   "ecdsa",
    },
    json={"model": MODEL, "messages": encrypted_messages, "stream": True},
    stream=True,
    timeout=60,
)
print("Status:", resp.status_code)
print("Server saw this in the body:")
print(json.dumps({"messages": encrypted_messages}, indent=2)[:240], "...")'''),
        ("markdown",
            "### 3e. Decrypt the stream in real time\n\n"
            "Each SSE chunk is an OpenAI-shaped delta whose `content` is a hex-encoded encrypted "
            "blob in the same wire format as our request. We decrypt with our client private key "
            "against the server's per-chunk ephemeral key."),
        ("code",
            '''_HEX = re.compile(r"^[0-9a-fA-F]+$")

def looks_encrypted(s: str) -> bool:
    return len(s) >= 186 and bool(_HEX.match(s))

def decrypt_chunk(hex_chunk: str, client_priv_key: SigningKey) -> str:
    raw     = bytes.fromhex(hex_chunk)
    eph_pub = raw[:65]; nonce = raw[65:77]; cipher = raw[77:]

    server_vk     = VerifyingKey.from_string(eph_pub[1:], curve=SECP256k1)
    shared_pt     = server_vk.pubkey.point * client_priv_key.privkey.secret_multiplier
    shared_secret = shared_pt.x().to_bytes(32, "big")

    aes_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=HKDF_INFO).derive(shared_secret)
    return AESGCM(aes_key).decrypt(nonce, cipher, None).decode()

full = ""
for line in resp.iter_lines():
    if not line:
        continue
    line = line.decode()
    if not line.startswith("data: ") or "[DONE]" in line:
        continue
    try:
        chunk = json.loads(line[6:])
    except json.JSONDecodeError:
        continue
    choices = chunk.get("choices") or []
    delta = (choices[0].get("delta", {}) if choices else {}).get("content", "")
    if not delta:
        continue
    if looks_encrypted(delta):
        delta = decrypt_chunk(delta, client_priv)
    full += delta
    print(delta, end="", flush=True)
print("\\n\\n--- decrypted", len(full), "characters end-to-end ---")'''),
        ("markdown",
            "## 4. The diff: what Venice's network would have seen\n\n"
            "Same prompt, three modes, side by side. In Private mode the literal patient case is "
            "in the body. In TEE mode it is still plaintext over TLS to Venice but nobody at "
            "Venice can read it during inference. In E2EE mode the body is unreadable hex even "
            "before it leaves your machine."),
        ("code",
            '''private_body = json.dumps({
    "model": "kimi-k2-6",
    "messages": [{"role": "user", "content": PROMPT}],
}, indent=2)

tee_body = json.dumps({
    "model": MODEL,  # same request as Private, just a different model id
    "messages": [{"role": "user", "content": PROMPT}],
}, indent=2)

e2ee_body = json.dumps({
    "model": MODEL,
    "messages": encrypted_messages,
    "stream": True,
}, indent=2)

pd.DataFrame({
    "mode":         ["Private", "TEE", "E2EE"],
    "protects_in_transit":  ["TLS", "TLS", "TLS + client-side AES-GCM"],
    "protects_at_inference":["policy only", "hardware enclave", "hardware enclave"],
    "wire_payload": [
        private_body[:200] + " ...",
        tee_body[:200] + " ...",
        e2ee_body[:200] + " ...",
    ],
})'''),
        ("markdown",
            "## What you just proved\n\n"
            "**With TEE alone:**\n"
            "1. The model ran inside a hardware enclave, verified by an Intel TDX attestation you "
            "can re-check from any language on any machine.\n"
            "2. Venice operators and the enclave host cannot read memory during inference.\n"
            "3. You did it with one line of code and kept every feature Venice offers.\n\n"
            "**With E2EE on top:**\n"
            "1. The prompt was encrypted on your machine with a key Venice never had.\n"
            "2. Only an enclave holding the matching private key (verified via Intel TDX quote) "
            "could decrypt it.\n"
            "3. The reply came back encrypted to your ephemeral key.\n"
            "4. Anyone sniffing Venice's network sees only ciphertext.\n\n"
            "If the enclave is ever compromised, the attestation breaks and your client refuses to "
            "send. If Venice is subpoenaed, the only thing handed over is hex. That is the "
            "difference between **trust us** and **here is your receipt**."),
        ("markdown",
            "## Mode picker: which one do I use?\n\n"
            "- **Private** is the default for open-source models on Venice. Use it when you want "
            "zero extra work and your data is not sensitive.\n"
            "- **TEE** is the sweet spot for business workloads: legal, medical, financial, HR, "
            "source code. One-line switch, full feature set, hardware-verified.\n"
            "- **E2EE** is for threat models that include Venice itself, or for compliance teams "
            "who need provable zero-knowledge on paper. Expect to give up streaming-optional, "
            "function calling, web search, and file uploads inside E2EE requests.\n\n"
            "## E2EE limitations to know\n\n"
            "- Streaming is required (no non-streaming).\n"
            "- Web search and function calling are disabled (they would leak plaintext).\n"
            "- File uploads are not supported.\n"
            "- Use a fresh ephemeral keypair per session and discard it after use.\n\n"
            "Welcome to provable AI privacy. Now go ship something with it."),
    ]
