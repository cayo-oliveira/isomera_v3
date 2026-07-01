"""Optional GenAI-assisted pair validation utilities.

The module intentionally uses only the Python standard library so Isomera can
offer an optional OpenAI validation path without adding a hard dependency.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


OPENAI_API_BASE = "https://api.openai.com/v1"

OPENAI_PRICING_HINTS: dict[str, dict[str, str]] = {
    "gpt-5.4": {"input": "$2.50 / 1M", "cached_input": "$0.25 / 1M", "output": "$15.00 / 1M"},
    "gpt-5.4-mini": {"input": "$0.75 / 1M", "cached_input": "$0.075 / 1M", "output": "$4.50 / 1M"},
    "gpt-5.4-nano": {"input": "$0.20 / 1M", "cached_input": "$0.02 / 1M", "output": "$1.25 / 1M"},
    "gpt-5.2": {"input": "$1.75 / 1M", "cached_input": "$0.175 / 1M", "output": "$14.00 / 1M"},
    "gpt-5.2-codex": {"input": "$1.75 / 1M", "cached_input": "$0.175 / 1M", "output": "$14.00 / 1M"},
    "gpt-5.1": {"input": "$1.25 / 1M", "cached_input": "$0.125 / 1M", "output": "$10.00 / 1M"},
    "gpt-5.1-codex-max": {"input": "$1.25 / 1M", "cached_input": "$0.125 / 1M", "output": "$10.00 / 1M"},
    "gpt-5-mini": {"input": "$0.25 / 1M", "cached_input": "$0.025 / 1M", "output": "$2.00 / 1M"},
    "gpt-5-nano": {"input": "$0.05 / 1M", "cached_input": "$0.005 / 1M", "output": "$0.40 / 1M"},
}

OPENAI_PRICING_USD_PER_1M: dict[str, dict[str, float]] = {
    "gpt-5.4": {"input": 2.50, "cached_input": 0.25, "output": 15.00},
    "gpt-5.4-mini": {"input": 0.75, "cached_input": 0.075, "output": 4.50},
    "gpt-5.4-nano": {"input": 0.20, "cached_input": 0.02, "output": 1.25},
    "gpt-5.2": {"input": 1.75, "cached_input": 0.175, "output": 14.00},
    "gpt-5.2-codex": {"input": 1.75, "cached_input": 0.175, "output": 14.00},
    "gpt-5.1": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
    "gpt-5.1-codex-max": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
    "gpt-5-mini": {"input": 0.25, "cached_input": 0.025, "output": 2.00},
    "gpt-5-nano": {"input": 0.05, "cached_input": 0.005, "output": 0.40},
}


@dataclass(frozen=True)
class GenAIValidationResult:
    raw_text: str
    parsed: dict[str, Any]
    response_id: str | None
    model: str
    elapsed_seconds: float
    usage: dict[str, Any]


def estimate_text_tokens(text: str) -> int:
    """Cheap local token estimate used before paid API calls.

    OpenAI billing uses model tokenization; this estimate is intentionally
    conservative enough for UI budgeting, not for invoices.
    """
    normalized = str(text or "")
    if not normalized:
        return 0
    return max(1, int(len(normalized) / 3.6))


def estimate_pair_validation_usage(
    *,
    prompt: str,
    pair_payload: dict[str, Any],
    max_output_tokens: int,
    pair_count: int = 1,
) -> dict[str, int]:
    payload_text = json.dumps(pair_payload, ensure_ascii=False, separators=(",", ":"))
    input_tokens = estimate_text_tokens(prompt) + estimate_text_tokens(payload_text)
    output_tokens = max(1, int(max_output_tokens))
    return {
        "estimated_input_tokens": input_tokens * max(1, int(pair_count)),
        "estimated_output_tokens": output_tokens * max(1, int(pair_count)),
        "estimated_total_tokens": (input_tokens + output_tokens) * max(1, int(pair_count)),
        "pair_count": max(1, int(pair_count)),
    }


def estimate_cost_usd(model: str, *, input_tokens: int, output_tokens: int) -> float | None:
    pricing = OPENAI_PRICING_USD_PER_1M.get(str(model))
    if not pricing:
        return None
    input_cost = (max(0, int(input_tokens)) / 1_000_000) * float(pricing["input"])
    output_cost = (max(0, int(output_tokens)) / 1_000_000) * float(pricing["output"])
    return round(input_cost + output_cost, 6)


def _request_json(
    method: str,
    path: str,
    api_key: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int = 45,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{OPENAI_API_BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-provided API key and official endpoint.
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI API connection error: {exc}") from exc


def list_openai_models(api_key: str, *, timeout: int = 30) -> list[dict[str, Any]]:
    """List models available to the provided key through OpenAI's Models API."""
    payload = _request_json("GET", "/models", api_key, timeout=timeout)
    rows = list(payload.get("data") or [])
    rows.sort(key=lambda item: str(item.get("id") or ""))
    for row in rows:
        model_id = str(row.get("id") or "")
        row["pricing_hint"] = OPENAI_PRICING_HINTS.get(model_id, {})
    return rows


def default_pair_validation_prompt() -> str:
    return (
        "You are validating structural redundancy in Isomera. Decide whether two "
        "lineage subgraphs represent duplicate data products. Use table lineage, "
        "layer, domain, parent/child signatures, and semantic names. Return JSON only "
        "with keys: decision ('duplicate' or 'not_duplicate'), target (1 or 0), "
        "confidence (0-1), rationale, matching_features, conflicting_features."
    )


def _extract_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return str(response["output_text"])
    chunks: list[str] = []
    for item in list(response.get("output") or []):
        for content in list(item.get("content") or []):
            if isinstance(content.get("text"), str):
                chunks.append(str(content["text"]))
    return "\n".join(chunks).strip()


def validate_pair_with_openai(
    api_key: str,
    *,
    model: str,
    prompt: str,
    pair_payload: dict[str, Any],
    max_output_tokens: int = 600,
    timeout: int = 90,
) -> GenAIValidationResult:
    """Validate one pair using the Responses API and parse a JSON decision."""
    started = time.perf_counter()
    payload = {
        "model": model,
        "instructions": prompt,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(pair_payload, indent=2, ensure_ascii=False),
                    }
                ],
            }
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "isomera_pair_validation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "decision": {"type": "string", "enum": ["duplicate", "not_duplicate"]},
                        "target": {"type": "integer", "enum": [0, 1]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "rationale": {"type": "string"},
                        "matching_features": {"type": "array", "items": {"type": "string"}},
                        "conflicting_features": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "decision",
                        "target",
                        "confidence",
                        "rationale",
                        "matching_features",
                        "conflicting_features",
                    ],
                },
            }
        },
        "max_output_tokens": max_output_tokens,
    }
    response = _request_json("POST", "/responses", api_key, payload=payload, timeout=timeout)
    raw_text = _extract_output_text(response)
    parsed: dict[str, Any] = {}
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(raw_text[start : end + 1])
            except json.JSONDecodeError:
                parsed = {"raw_decision": raw_text}
        else:
            parsed = {"raw_decision": raw_text}
    return GenAIValidationResult(
        raw_text=raw_text,
        parsed=parsed,
        response_id=response.get("id"),
        model=model,
        elapsed_seconds=round(time.perf_counter() - started, 3),
        usage=dict(response.get("usage") or {}),
    )


def save_genai_agent_config(root: str | Path, config: dict[str, Any]) -> Path:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(config.get("name") or "agent"))
    path = root / f"{time.strftime('%Y%m%d_%H%M%S')}_{safe_name}.json"
    path.write_text(json.dumps(config, indent=2, ensure_ascii=True), encoding="utf-8")
    return path
