from __future__ import annotations
from enum import Enum
from sqlalchemy import JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base
import uuid
import datetime
from typing import List, Dict, Any, TYPE_CHECKING


from src.transaction_result.models import TransactionRuleResult



class TransactionStatus(Enum):
    approved = "APPROVED"
    declined = "DECLINED"

class TransactionChannel(Enum):
    web = "WEB"
    mobile = "MOBILE"
    pos = "POS"
    other = "OTHER"

class Transaction(Base):
    __tablename__="transactions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    # user = relationship(back_populates="transactions")
    amount: Mapped[float] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(nullable=False)
    merchant_id: Mapped[str] = mapped_column(nullable=True)
    merchant_category_code:  Mapped[str] = mapped_column(nullable=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False )
    ip_address:  Mapped[str] = mapped_column(nullable=True)
    device_id:  Mapped[str] = mapped_column(nullable=True)
    channel: Mapped[TransactionChannel] = mapped_column(nullable=False)
    country:  Mapped[str] = mapped_column(nullable=True)
    city:  Mapped[str] = mapped_column(nullable=True)
    latitude:  Mapped[float] = mapped_column(nullable=True)
    longitude:  Mapped[float] = mapped_column(nullable=True)
    is_fraud: Mapped[bool] = mapped_column(nullable=False )
    tr_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, default=datetime.datetime.now()
    )


