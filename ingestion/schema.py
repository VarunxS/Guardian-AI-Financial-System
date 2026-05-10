"""
Transaction schema — Pydantic v2 models for parsed transactions and statement uploads.
"""

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    """A single parsed financial transaction."""

    date: datetime
    description: str  # raw merchant string
    amount: float  # positive = debit, negative = credit
    currency: str = "INR"
    category: str  # auto-assigned by parser
    merchant_name: str  # cleaned merchant name
    is_recurring: bool = False
    transaction_id: str = Field(default_factory=lambda: str(uuid4()))


class StatementUpload(BaseModel):
    """A batch of transactions from a single statement upload."""

    user_id: str
    source: Literal["bank_csv", "credit_card_pdf", "upi_pdf"]
    transactions: list[Transaction]
    upload_timestamp: datetime = Field(default_factory=datetime.now)
