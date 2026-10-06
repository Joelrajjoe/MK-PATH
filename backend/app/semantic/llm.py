"""LLM interpretation providers for the semantic layer (Phase 6).

Policy (spec section 4, 7, 11):
- The LLM may PROPOSE business interpretations; it can never finalize them.
  Everything returned here is stored with source="llm_proposed" and
  status="needs_review" by the builder - the provider layer cannot change that.
- Keys come from the environment only (GEMINI_API_KEY); never logged, never
  returned in responses.
- Any failure (missing key, network, malformed reply, parse error) degrades to
  "LLM unavailable" - the caller proceeds deterministic-only. No fabricated
  proposals are ever emitted.
"""
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings

logger = logging.getLogger("mkpath.semantic.llm")

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


class InterpretationProposal(dict):
    """Dictionary with keys: label, description, confidence (0..1).

    Kept as a plain dict so it serializes directly into Mongo documents.
    """
    pass


class LLMUnavailable(Exception):
    """Raised internally when the provider cannot be used (never escapes)."""


class NullProvider:
    """Deterministic-only mode: no LLM configured."""

    name = "null"

    def propose_column_interpretations(
        self,
        *,
        column: str,
        dtype: str,
        values: List[str],
        business_goal: Optional[str],
    ) -> Optional[List[Dict[str, Any]]]:
        return None

    def propose_ambiguities(self, *, context_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []


class GeminiProvider:
    """Gemini REST provider (structured JSON output, short timeout)."""

    name = "gemini"

    def __init__(self, api_key: str, model: Optional[str] = None, timeout: float = 8.0):
        self._api_key = api_key
        self._model = model or settings.GEMINI_MODEL
        self._timeout = timeout

    def _generate(self, prompt: str) -> Optional[Dict[str, Any]]:
        url = _GEMINI_URL.format(model=self._model)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        try:
            resp = httpx.post(
                url,
                params={"key": self._api_key},
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except Exception as exc:  # degrade gracefully; log type only (no key/URI)
            logger.warning("Gemini call failed: %s", type(exc).__name__)
            return None

    def propose_column_interpretations(
        self,
        *,
        column: str,
        dtype: str,
        values: List[str],
        business_goal: Optional[str],
    ) -> Optional[List[Dict[str, Any]]]:
        goal = business_goal or "(not provided)"
        prompt = (
            "You are assisting a data analyst. A dataset column carries coded "
            "business meaning that humans must confirm. Propose the most plausible "
            "business interpretations of the VALUES of this column.\n"
            f"Business goal: {goal}\n"
            f"Column name: {column}\nColumn type: {dtype}\n"
            f"Observed values (sample): {values}\n\n"
            'Respond as JSON: {"proposals": [{"label": str, "description": str, '
            '"confidence": number 0..1}]} with at most 5 proposals. '
            "Labels must be short. If the column looks like a generic status/state/"
            "type code, propose what each distinct value class typically means; do "
            "NOT assert that any interpretation is certain."
        )
        data = self._generate(prompt)
        if not data or "proposals" not in data or not isinstance(data["proposals"], list):
            return None
        out: List[Dict[str, Any]] = []
        for p in data["proposals"][:5]:
            if not isinstance(p, dict) or "label" not in p:
                continue
            try:
                conf = float(p.get("confidence", 0.5))
            except (TypeError, ValueError):
                conf = 0.5
            out.append(
                {
                    "label": str(p["label"])[:80],
                    "description": str(p.get("description", ""))[:300],
                    "confidence": max(0.0, min(1.0, conf)),
                    "source": "llm_proposed",
                }
            )
        return out or None

    def propose_ambiguities(self, *, context_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        prompt = (
            "Review this dataset semantics summary and list any business-meaning "
            "ambiguities that would block reliable analysis and are NOT already "
            "listed. Respond as JSON: {\"ambiguities\": [{\"subject\": str, "
            "\"question\": str}]} with at most 3 items. Return an empty list if none."
            f"\nSummary: {json.dumps(context_summary)[:4000]}"
        )
        data = self._generate(prompt)
        if not data or not isinstance(data.get("ambiguities"), list):
            return []
        out: List[Dict[str, Any]] = []
        for a in data["ambiguities"][:3]:
            if isinstance(a, dict) and a.get("question"):
                out.append(
                    {
                        "subject": str(a.get("subject", "dataset"))[:80],
                        "question": str(a["question"])[:300],
                    }
                )
        return out


_provider: Optional[Any] = None


def get_provider() -> Any:
    """Process-wide provider; Gemini when a key is configured, else Null."""
    global _provider
    if _provider is None:
        if settings.GEMINI_API_KEY:
            _provider = GeminiProvider(settings.GEMINI_API_KEY)
        else:
            _provider = NullProvider()
    return _provider
