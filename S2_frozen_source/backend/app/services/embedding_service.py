"""Embedding service. API-first, with optional local sentence-transformers fallback."""
from __future__ import annotations

import logging
from typing import List, Optional

import httpx
import numpy as np

from ..config import settings

logger = logging.getLogger(__name__)


_local_model = None
_local_checked = False


def _load_local():
    global _local_model, _local_checked
    if _local_checked:
        return _local_model
    _local_checked = True
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        _local_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        logger.info("Local sentence-transformers model loaded.")
    except Exception as e:
        logger.info("Local sentence-transformers unavailable: %s", e)
        _local_model = None
    return _local_model


def local_available() -> bool:
    return _load_local() is not None


def api_enabled() -> bool:
    return settings.embedding_enabled


def _api_embed(texts: List[str]) -> Optional[List[List[float]]]:
    if not api_enabled():
        return None
    try:
        with httpx.Client(timeout=120.0) as client:
            r = client.post(
                f"{settings.embedding_api_base_url.rstrip('/')}/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.embedding_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.embedding_model,
                    "input": texts,
                },
            )
            if r.status_code != 200:
                logger.warning("Embedding API error %s: %s", r.status_code, r.text[:200])
                return None
            data = r.json()
            return [d["embedding"] for d in data.get("data", [])]
    except Exception as e:  # pragma: no cover
        logger.warning("Embedding API call failed: %s", e)
        return None


def embed_texts(texts: List[str]) -> Optional[np.ndarray]:
    """Embed a list of strings. Returns None if no provider is available."""
    if not texts:
        return None
    # Try API first
    if api_enabled():
        embs = _api_embed(texts)
        if embs is not None and len(embs) == len(texts):
            return np.asarray(embs, dtype=np.float32)
    # Fall back to local
    model = _load_local()
    if model is None:
        return None
    try:
        vecs = model.encode(texts, normalize_embeddings=False, convert_to_numpy=True)
        return np.asarray(vecs, dtype=np.float32)
    except Exception as e:
        logger.warning("Local embedding failed: %s", e)
        return None


def embed_query(text: str) -> Optional[np.ndarray]:
    arr = embed_texts([text])
    if arr is None:
        return None
    return arr[0]


def cosine_topk(query_vec: np.ndarray, matrix: np.ndarray, k: int = 20):
    if matrix.size == 0:
        return np.array([], dtype=np.int64), np.array([], dtype=np.float32)
    a = query_vec.astype(np.float32)
    b = matrix.astype(np.float32)
    a_norm = np.linalg.norm(a)
    b_norms = np.linalg.norm(b, axis=1)
    denom = (a_norm * b_norms) + 1e-12
    sims = (b @ a) / denom
    k = min(k, sims.shape[0])
    idx = np.argpartition(-sims, k - 1)[:k] if k > 0 else np.array([], dtype=np.int64)
    idx = idx[np.argsort(-sims[idx])]
    return idx, sims[idx]


def status() -> dict:
    return {
        "api_enabled": api_enabled(),
        "local_available": local_available(),
        "model": settings.embedding_model if api_enabled() else "paraphrase-multilingual-MiniLM-L12-v2",
    }
