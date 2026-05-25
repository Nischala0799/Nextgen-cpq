"""
repository.py
-------------
QuoteRepository — thin persistence layer over SQLAlchemy.

Quotes are serialized to JSON on save and deserialized on load.
All business logic lives in the domain layer; this module only handles
read/write to the database.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from cpq_domain.models import Quote
from api.database import QuoteRecord


class QuoteRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, quote: Quote) -> None:
        """Insert or update a quote record."""
        record = (
            self._session.query(QuoteRecord)
            .filter(QuoteRecord.quote_id == quote.quote_id)
            .first()
        )
        serialized = quote.model_dump_json()
        if record:
            record.data = serialized
        else:
            self._session.add(QuoteRecord(quote_id=quote.quote_id, data=serialized))
        self._session.commit()

    def get(self, quote_id: str) -> Optional[Quote]:
        """Return a Quote by ID, or None if not found."""
        record = (
            self._session.query(QuoteRecord)
            .filter(QuoteRecord.quote_id == quote_id)
            .first()
        )
        if not record:
            return None
        return Quote.model_validate_json(record.data)

    def close(self) -> None:
        self._session.close()
