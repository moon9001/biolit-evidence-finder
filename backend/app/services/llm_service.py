"""LLM service for optional page-level extraction. OpenAI-compatible API."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


_PROMPT = (
    "你是生物多样性文献证据抽取助手。"
    "请只基于输入的单页 OCR/文本内容，"
    "抽取该页明确出现的拉丁学名、中文物种名、地名、主题关键词和可能的证据类型。"
    "不得补充页面中没有出现的信息。没有证据返回空数组。"
    "请输出 JSON，字段包括 scientific_names, chinese_names, locations, "
    "keywords, evidence_type, notes。"
)


def is_enabled() -> bool:
    return settings.llm_enabled


def _strip_json(content: str) -> str:
    """Remove markdown fences / common prefixes that some models add."""
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```\s*$", "", content)
    return content.strip()


def chat_test() -> Dict[str, Any]:
    """Simple ping to confirm the LLM API is reachable. Returns status dict."""
    if not is_enabled():
        return {"ok": False, "reason": "not_configured"}
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.post(
                f"{settings.llm_api_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 4,
                },
            )
            return {"ok": r.status_code == 200, "status": r.status_code,
                    "snippet": r.text[:200]}
    except Exception as e:  # pragma: no cover
        return {"ok": False, "error": str(e)}


def extract_from_page(page_text: str) -> Optional[Dict[str, List[str]]]:
    """Call the LLM to extract structured info from a single page.

    Returns None if disabled or on failure (caller should fall back to rules).
    """
    if not is_enabled():
        return None

    text = page_text.strip()
    if len(text) < 20:
        return None

    # Cap input length to keep the request small.
    if len(text) > 4000:
        text = text[:4000]

    body = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": _PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.0,
        "max_tokens": 800,
    }
    try:
        with httpx.Client(timeout=60.0) as client:
            r = client.post(
                f"{settings.llm_api_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            if r.status_code != 200:
                logger.warning("LLM error %s: %s", r.status_code, r.text[:200])
                return None
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            content = _strip_json(content)
            try:
                parsed = json.loads(content)
            except Exception:
                # Try to find a JSON object inside
                m = re.search(r"\{.*\}", content, flags=re.S)
                if not m:
                    return None
                parsed = json.loads(m.group(0))
            # Normalise lists
            out: Dict[str, List[str]] = {}
            for k in ["scientific_names", "chinese_names", "locations",
                      "keywords", "evidence_type", "notes"]:
                v = parsed.get(k, [])
                if isinstance(v, str):
                    v = [v]
                if not isinstance(v, list):
                    v = []
                out[k] = [str(x).strip() for x in v if str(x).strip()]
            return out
    except Exception as e:  # pragma: no cover - network dependent
        logger.warning("LLM extraction failed: %s", e)
        return None
