from __future__ import annotations

import hashlib
import json
import logging
from datetime import date

from app.config import get_settings
from app.db.repo import ai_cache_get, ai_cache_put, ai_usage_add, ai_usage_for

log = logging.getLogger("perfin.ai")


class BudgetExceeded(RuntimeError):
    pass


def _cache_key(model: str, feature: str, payload: dict) -> str:
    blob = json.dumps({"m": model, "f": feature, "p": payload}, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def _current_month() -> str:
    return date.today().strftime("%Y-%m")


def _check_budget(projected_tokens: int = 0) -> None:
    settings = get_settings()
    if settings.MAX_MONTHLY_TOKENS <= 0:
        return
    used_in, used_out = ai_usage_for(_current_month())
    if used_in + used_out + projected_tokens > settings.MAX_MONTHLY_TOKENS:
        raise BudgetExceeded(
            f"Monthly token budget exceeded ({used_in + used_out}/{settings.MAX_MONTHLY_TOKENS})"
        )


def run_feature(feature: str, payload: dict, system: str, *, heavy: bool = False) -> dict:
    settings = get_settings()
    model = settings.CLAUDE_MODEL_HEAVY if heavy else settings.CLAUDE_MODEL
    key = _cache_key(model, feature, payload)
    cached = ai_cache_get(key)
    if cached:
        return json.loads(cached["response_json"])

    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    _check_budget()

    from anthropic import Anthropic

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )

    text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {"raw": text}

    tokens_in = getattr(resp.usage, "input_tokens", 0)
    tokens_out = getattr(resp.usage, "output_tokens", 0)
    ai_usage_add(_current_month(), tokens_in, tokens_out)
    ai_cache_put(
        key=key,
        model=model,
        feature=feature,
        request_json=json.dumps(payload),
        response_json=json.dumps(parsed),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    return parsed
