"""OPTIONAL wording suggestion. Active only when ANTHROPIC_API_KEY is set.
The calculation and the document never depend on this."""
import httpx

from . import config


def enabled() -> bool:
    return bool(config.ANTHROPIC_API_KEY)


def client_message_hint(title, option_label, new_date, extra_cost, rationale) -> str:
    prompt = (
        "You help a first-time project manager. Write a short, polite message (max 120 words) to the client "
        "announcing this decision on their change request. Use only the facts given. No placeholders other than [Name].\n\n"
        f"Change: {title}\nDecision: {option_label}\nRelease date: {new_date}\nExtra cost: ${extra_cost}\n"
        f"Manager's reason: {rationale or 'n/a'}"
    )
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
        json={"model": config.LLM_MODEL, "max_tokens": 400, "messages": [{"role": "user", "content": prompt}]},
        timeout=20,
    )
    r.raise_for_status()
    return "".join(c.get("text", "") for c in r.json().get("content", [])).strip()
