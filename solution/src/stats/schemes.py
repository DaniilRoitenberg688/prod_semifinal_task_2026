from typing import Optional
import datetime

from pydantic import BaseModel, model_validator, Field

class StatsOverviewIn(BaseModel):
    from_time: Optional[datetime.datetime] = Field(default=None, )
    to: datetime.datetime = datetime.datetime.now(datetime.timezone.utc) 

    @model_validator(mode="after")
    def validate_time(self) -> 'StatsOverviewIn':
        if self.from_time is None:
            self.from_time = self.to - datetime.timedelta(days=30)
            return self
        if self.to - self.from_time > datetime.timedelta(days=90):
            raise ValueError
        return self


class MerchantRiskRow(BaseModel):
    merchantId: str
    merchantCategoryCode: Optional[str] = None
    txCount: int
    gmv: float
    declineRate: float


class StatsOverviewOut(BaseModel):
    from_time: datetime.datetime = Field(serialization_alias="from")
    to: datetime.datetime = datetime.datetime.now(datetime.timezone.utc) 
    volume: int
    gmv: float
    approvalRate: float
    declineRate: float
    topRiskMerchants: list[MerchantRiskRow]

