from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator
import datetime
import uuid
from src.transaction_result.schemes import RuleResult

from src.transactions.models import TransactionChannel, TransactionStatus


class TransactionLocation(BaseModel):
    country: Optional[str] = Field(default=None, min_length=2, max_length=2, pattern="^[A-Z]{2}$")
    city: Optional[str] = Field(default=None, max_length=128)
    longitude: Optional[float] = Field(ge=-90, le=90, default=None)
    latitude: Optional[float] = Field(None,ge=-90, le=90)

    @model_validator(mode="after")
    def validate_coords(self) -> 'TransactionLocation':
        latitude = self.latitude
        longitude = self.longitude
        if latitude is None and longitude is not None:
            raise ValueError
        if latitude is not None and longitude is None:
            raise ValueError
        return self


class BaseTransaction(BaseModel):
    user_id: uuid.UUID = Field(alias="userId")
    amount: float = Field(ge=0.01, le=999999999.99)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    merchant_id: Optional[str] = Field(default=None, alias="merchantId")
    merchant_category_code: Optional[str] = Field(default=None, pattern=r"^\d{4}$", alias="merchantCategoryCode")
    timestamp: datetime.datetime
    ip_address: Optional[str] = Field(default=None, max_length=64, alias="ipAddress")
    device_id: Optional[str] = Field(default=None, max_length=128, alias="deviceId")
    channel: Optional[TransactionChannel] = None
    location: Optional[TransactionLocation] = TransactionLocation(
        country=None,
        city=None,
        latitude=None,
        longitude=None
    )
    metadata: Optional[Any] = None

    @field_validator("amount")
    def set_amount_to_two_signs(cls, a):
        return round(a, 2)

    @field_validator("timestamp")
    def validate_timestamp(cls, t: datetime.datetime):
        t = t.replace(tzinfo=datetime.timezone.utc)

        if t - datetime.datetime.now(datetime.timezone.utc) > datetime.timedelta(minutes=5):
            raise ValueError
        return t


class TransactionScheme(BaseTransaction):
    id: uuid.UUID
    status: TransactionStatus
    is_fraud: bool = Field(alias="isFraud")
    created_at: datetime.datetime = Field(alias="createdAt")


class CreateTranscation(BaseTransaction):
    id: uuid.UUID
    status: TransactionStatus
    is_fraud: bool = Field(alias="isFraud")

class CreateTranscationRequest(BaseTransaction):
    pass


class TransactionResponse(BaseModel):
    transaction: TransactionScheme
    ruleResults: list[RuleResult]
