"""Pydantic schemas for API IO."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[str] = None
    page_count: int = 0
    processed_pages: int = 0
    status: str = "pending"
    error: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    items: List[DocumentOut]
    total: int
    page: int
    page_size: int
    status_counts: dict


class PageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    page_number: int
    page_label: Optional[str] = None
    text: str = ""
    ocr_used: int = 0
    text_length: int = 0
    image_path: Optional[str] = None


class OccurrenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    page_id: int
    term: str
    term_type: str
    context: str = ""
    confidence: float = 1.0
    extractor: str = "rule"


class SearchResultItem(BaseModel):
    document_id: int
    document_title: Optional[str] = None
    file_name: str
    page_number: int
    matched_term: str
    context: str
    score: float
    match_type: str
    viewer_url: str


class SearchResponse(BaseModel):
    query: str
    mode: str
    result_count: int
    results: List[SearchResultItem] = Field(default_factory=list)
    notes: Optional[str] = None


class StatsOut(BaseModel):
    document_count: int
    page_count: int
    indexed_pages: int
    occurrence_count: int
    chunk_count: int
    embedded_chunks: int


class SettingsStatus(BaseModel):
    llm_enabled: bool
    embedding_enabled: bool
    embedding_local_available: bool
    ocr_local_available: bool
    deepseek_ocr_enabled: bool
    llm_model: str
    embedding_model: str
    llm_api_base_url: str


class SettingsUpdate(BaseModel):
    llm_api_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    embedding_api_base_url: Optional[str] = None
    embedding_api_key: Optional[str] = None
    embedding_model: Optional[str] = None
