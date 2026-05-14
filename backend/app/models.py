"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    Float,
)
from sqlalchemy.orm import relationship

from .database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    file_name = Column(String(512), nullable=False)
    stored_path = Column(String(1024), nullable=False)
    title = Column(String(512), nullable=True)
    author = Column(String(512), nullable=True)
    year = Column(String(32), nullable=True)
    page_count = Column(Integer, default=0)
    processed_pages = Column(Integer, default=0)
    status = Column(String(32), default="pending")  # pending|processing|completed|failed
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    occurrences = relationship(
        "Occurrence", back_populates="document", cascade="all, delete-orphan"
    )
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    page_label = Column(String(64), nullable=True)
    text = Column(Text, default="")
    ocr_used = Column(Integer, default=0)  # 0/1
    text_length = Column(Integer, default=0)
    image_path = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="pages")
    occurrences = relationship("Occurrence", back_populates="page", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="page", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_pages_doc_page", "document_id", "page_number"),)


class Occurrence(Base):
    __tablename__ = "occurrences"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    term = Column(String(512), nullable=False)
    term_type = Column(String(64), nullable=False)
    # term_type: scientific_name | scientific_name_abbrev | chinese_name |
    #            location | keyword | taxonomy_term
    start_char = Column(Integer, default=-1)
    end_char = Column(Integer, default=-1)
    context = Column(Text, default="")
    confidence = Column(Float, default=1.0)
    extractor = Column(String(32), default="rule")  # rule|llm
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="occurrences")
    page = relationship("Page", back_populates="occurrences")

    __table_args__ = (
        Index("ix_occurrences_term", "term"),
        Index("ix_occurrences_type", "term_type"),
        Index("ix_occurrences_doc_page", "document_id", "page_id"),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, default=0)
    text = Column(Text, default="")
    token_count = Column(Integer, default=0)
    embedding = Column(LargeBinary, nullable=True)  # numpy float32 bytes
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")
    page = relationship("Page", back_populates="chunks")


class SearchLog(Base):
    __tablename__ = "search_logs"

    id = Column(Integer, primary_key=True)
    query = Column(String(1024), nullable=False)
    mode = Column(String(32), default="exact")
    result_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
