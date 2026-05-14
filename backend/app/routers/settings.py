"""Settings status and runtime updates."""
from __future__ import annotations

from fastapi import APIRouter

from ..config import settings
from ..schemas import SettingsStatus, SettingsUpdate
from ..services import embedding_service, llm_service, ocr_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/status", response_model=SettingsStatus)
def status() -> SettingsStatus:
    emb_status = embedding_service.status()
    return SettingsStatus(
        llm_enabled=llm_service.is_enabled(),
        embedding_enabled=emb_status["api_enabled"],
        embedding_local_available=emb_status["local_available"],
        ocr_local_available=ocr_service.is_available(),
        deepseek_ocr_enabled=bool(settings.deepseek_ocr_url and settings.deepseek_ocr_key),
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        llm_api_base_url=settings.llm_api_base_url,
    )


@router.post("/test-llm")
def test_llm():
    return llm_service.chat_test()


@router.put("")
def update_settings(payload: SettingsUpdate):
    if payload.llm_api_base_url is not None or payload.llm_api_key is not None or payload.llm_model is not None:
        settings.update_llm(
            base_url=payload.llm_api_base_url
            if payload.llm_api_base_url is not None
            else settings.llm_api_base_url,
            api_key=payload.llm_api_key
            if payload.llm_api_key is not None
            else settings.llm_api_key,
            model=payload.llm_model
            if payload.llm_model is not None
            else settings.llm_model,
        )
    if (
        payload.embedding_api_base_url is not None
        or payload.embedding_api_key is not None
        or payload.embedding_model is not None
    ):
        settings.update_embedding(
            base_url=payload.embedding_api_base_url
            if payload.embedding_api_base_url is not None
            else settings.embedding_api_base_url,
            api_key=payload.embedding_api_key
            if payload.embedding_api_key is not None
            else settings.embedding_api_key,
            model=payload.embedding_model
            if payload.embedding_model is not None
            else settings.embedding_model,
        )
    return status()
