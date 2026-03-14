"""
AI-powered transaction categoriser using Claude Haiku.
Adapted from backend — no FastAPI/config dependencies.
"""

import json
import logging
import os
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

CATEGORIES = [
    "Food & Drink",
    "Transport",
    "Shopping",
    "Groceries",
    "Healthcare",
    "Entertainment",
    "Bills & Utilities",
    "Travel",
    "Education",
    "Income",
    "Other",
]

SYSTEM_PROMPT = f"""You are a personal finance assistant that categorises bank transactions.

Given a list of transaction descriptions from Singapore bank statements, assign each one
to exactly one of these categories:
{json.dumps(CATEGORIES, indent=2)}

Rules:
- Food & Drink: restaurants, cafes, food delivery (Grab Food, Foodpanda, McDonald's, etc.)
- Transport: Grab rides, taxis, MRT/bus top-up, EZ-Link, petrol, parking, car-related
- Shopping: online/retail shopping (Lazada, Shopee, Amazon, clothing, electronics)
- Groceries: supermarkets (NTUC FairPrice, Cold Storage, Sheng Siong, Giant, RedMart)
- Healthcare: clinics, hospitals, pharmacies, dental, optical
- Entertainment: movies, concerts, games, streaming (Netflix, Spotify), sports
- Bills & Utilities: telco, electricity, water, internet, insurance premiums, town council
- Travel: flights, hotels, overseas merchants, Changi Airport
- Education: tuition, courses, school fees, books, Udemy/Coursera
- Income: salary, bank interest, cashback, refunds (positive amounts)
- Other: anything that doesn't fit above

Respond ONLY with a JSON array in this exact format:
[{{"description": "...", "category": "..."}}]

One object per input description, in the same order as input.
"""


def categorise_batch(descriptions: list[str], api_key: str) -> list[str]:
    if not descriptions:
        return []

    client = anthropic.Anthropic(api_key=api_key)
    results: list[str] = ["Other"] * len(descriptions)

    batch_size = 100
    for batch_start in range(0, len(descriptions), batch_size):
        batch = descriptions[batch_start : batch_start + batch_size]
        user_content = json.dumps(batch, ensure_ascii=False, indent=2)

        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = message.content[0].text.strip()

            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            parsed: list[dict[str, Any]] = json.loads(raw)
            for i, item in enumerate(parsed):
                cat = item.get("category", "Other")
                if cat not in CATEGORIES:
                    cat = "Other"
                results[batch_start + i] = cat

        except Exception as e:
            logger.warning("Categorisation batch failed: %s", e)

    return results
