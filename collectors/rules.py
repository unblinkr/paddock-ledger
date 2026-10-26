"""Rule-text fingerprints for the venues whose APIs serve rules text.

Every row that can carry one gets `rules_sha256`, so a change in a contract's
rules shows up as a changed hash between two days without storing the text
twice. The hash is only a fingerprint of what the venue served; it says
nothing about what changed. The text itself stays in the daily and settled
rows.

Definitions (permanent: changing one breaks comparison with older rows, so a
change needs a new field name, never a new meaning for this one):

  Kalshi        collectors/kalshi.py rules_sha256: rules_primary, one newline,
                rules_secondary. Unchanged here.
  Polymarket US sha256 of the market's `description` as served, UTF-8. None
                when the market carries no `description` key.
  Gemini        sha256 of canonical JSON of
                [contract.description, event.description,
                 contract.termsAndConditionsUrl] where canonical JSON is
                sort_keys, separators (",", ":"), ensure_ascii False, UTF-8.
                contract.description is the rich-text object as served. The
                terms PDF behind the URL is not fetched, so a change inside
                the PDF with the same URL is not seen. None when the contract
                carries no `description` key.

Verified on saved responses 2026-10-26 (tests/fixtures).
"""

from __future__ import annotations

import hashlib
import json


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def polymarket_us_rules_sha256(m: dict) -> str | None:
    if "description" not in m:
        return None
    return _sha(m.get("description") or "")


def gemini_rules_sha256(event: dict, contract: dict) -> str | None:
    if "description" not in contract:
        return None
    parts = [contract.get("description"), event.get("description"), contract.get("termsAndConditionsUrl")]
    return _sha(json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
