"""OCR service. Tries pytesseract; gracefully degrades when unavailable."""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_pytesseract = None
_pytesseract_checked = False
_pil_image = None


def _load_pytesseract():
    global _pytesseract, _pytesseract_checked, _pil_image
    if _pytesseract_checked:
        return _pytesseract
    _pytesseract_checked = True
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore

        # Probe binary availability.
        pytesseract.get_tesseract_version()
        _pytesseract = pytesseract
        _pil_image = Image
    except Exception as e:  # pragma: no cover - environment dependent
        logger.warning("pytesseract not available, OCR disabled: %s", e)
        _pytesseract = None
        _pil_image = None
    return _pytesseract


def is_available() -> bool:
    return _load_pytesseract() is not None


def ocr_image_bytes(png_bytes: bytes, lang: str = "chi_sim+eng") -> str:
    """OCR a PNG image. Returns empty string on any failure."""
    pyt = _load_pytesseract()
    if pyt is None or _pil_image is None:
        return ""
    try:
        import io

        img = _pil_image.open(io.BytesIO(png_bytes))
        try:
            return pyt.image_to_string(img, lang=lang) or ""
        except Exception:
            # Lang pack might be missing, retry with eng only.
            try:
                return pyt.image_to_string(img, lang="eng") or ""
            except Exception:
                return ""
    except Exception as e:
        logger.warning("OCR failed: %s", e)
        return ""
