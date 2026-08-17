"""Google reCAPTCHA v3 verification."""
import os
import logging
from typing import Tuple

import httpx  # PERF FIX [PERF-002]: async-capable HTTP client (already in requirements.txt)

logger = logging.getLogger(__name__)

RECAPTCHA_SECRET = os.getenv("RECAPTCHA_SECRET_KEY", "")
RECAPTCHA_URL    = "https://www.google.com/recaptcha/api/siteverify"
SCORE_THRESHOLD  = 0.5

# SECURITY FIX [SEC-004]: DEV_MODE must be explicitly enabled in .env.
# When False (default/production), a missing secret key is treated as a
# configuration error and raises RuntimeError rather than silently bypassing CAPTCHA.
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"


async def verify_captcha(token: str, remote_ip: str = "") -> Tuple[bool, float]:
    """
    Verify reCAPTCHA v3 token asynchronously. Returns (passed, score).

    SECURITY FIX [SEC-004]: Fails closed — raises RuntimeError if the secret
    key is missing in non-dev mode, preventing silent CAPTCHA bypass.
    PERF FIX [PERF-002]: Uses httpx.AsyncClient to avoid blocking the event loop.
    """
    if not RECAPTCHA_SECRET:
        if DEV_MODE:
            logger.warning(
                "DEV_MODE enabled: RECAPTCHA_SECRET_KEY not set — skipping CAPTCHA verification. "
                "NEVER deploy with DEV_MODE=true."
            )
            return True, 1.0
        # Fail closed: refuse to process submissions without a valid key
        raise RuntimeError(
            "RECAPTCHA_SECRET_KEY is not configured. "
            "Set it in .env or disable CAPTCHA for local dev with DEV_MODE=true."
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                RECAPTCHA_URL,
                data={"secret": RECAPTCHA_SECRET, "response": token, "remoteip": remote_ip},
            )
        resp.raise_for_status()
        result  = resp.json()
        success = result.get("success", False)
        score   = float(result.get("score", 0.0))
        logger.info("reCAPTCHA: success=%s, score=%.2f", success, score)
        if not success or score < SCORE_THRESHOLD:
            return False, score
        return True, score
    except httpx.RequestError as exc:
        logger.error("reCAPTCHA API request error: %s", exc)
        return False, 0.0
    except httpx.HTTPStatusError as exc:
        logger.error("reCAPTCHA API HTTP error: %s", exc)
        return False, 0.0
