"""Venice client helpers shared across notebooks.

Works in three environments without changes:
  1. Local with a `.env` file (loaded via python-dotenv).
  2. Plain shell with environment variables already exported.
  3. Google Colab via `userdata.get(...)` for stored secrets.
"""

from __future__ import annotations

import os
from typing import Optional

BASE_URL = "https://api.venice.ai/api/v1"


def _try_load_dotenv() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
    except ImportError:
        pass


def _try_colab_secret(name: str) -> Optional[str]:
    try:
        from google.colab import userdata  # type: ignore
        try:
            return userdata.get(name)
        except Exception:
            return None
    except ImportError:
        return None


def get_api_key(var_name: str = "VENICE_API_KEY") -> str:
    """Return the Venice API key from env / dotenv / Colab secrets, or raise."""
    _try_load_dotenv()
    val = os.environ.get(var_name) or _try_colab_secret(var_name)
    if not val:
        raise RuntimeError(
            f"{var_name} is not set.\n"
            "  - Local: copy .env.example -> .env and fill it in\n"
            "  - Colab: add it under the key icon (Secrets) in the left sidebar"
        )
    return val


def get_wallet_key(var_name: str = "WALLET_PRIVATE_KEY") -> str:
    """Return a Base wallet private key for the x402 notebook."""
    _try_load_dotenv()
    val = os.environ.get(var_name) or _try_colab_secret(var_name)
    if not val:
        raise RuntimeError(
            f"{var_name} is not set. Generate a fresh wallet and fund it with "
            "a small amount of USDC on Base mainnet first."
        )
    return val if val.startswith("0x") else f"0x{val}"


def get_client(api_key: Optional[str] = None):
    """Return an OpenAI client wired to the Venice base URL."""
    from openai import OpenAI  # imported lazily so the module loads without it

    return OpenAI(
        api_key=api_key or get_api_key(),
        base_url=BASE_URL,
    )
