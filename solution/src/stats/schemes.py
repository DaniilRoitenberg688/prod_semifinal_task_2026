from enum import Enum
from typing import Literal, Optional
import datetime

from pydantic import AliasChoices, BaseModel, model_validator, Field
import uuid

class StatsOverviewIn(BaseModel):
    from_time: Optional[datetime.datetime] = Field(default=None, alias="from", validation_alias=AliasChoices("from", "from_time"),)
    to: datetime.datetime = datetime.datetime.now(datetime.timezone.utc) 

    @model_validator(mode="after")
    def validate_time(self) -> 'StatsOverviewIn':
        if self.from_time is None:
            self.from_time = self.to - datetime.timedelta(days=30)
            return self
        if self.to - self.from_time > datetime.timedelta(days=90):
            raise ValueError("from is too far from to")
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


class GroupByEnum(Enum):
    day = datetime.timedelta(days=1)
    hour = datetime.timedelta(hours=1)
    week = datetime.timedelta(weeks=1)

class StatsGroupBy(StatsOverviewIn):
    groupBy: Literal["day", "hour", "week"] = "day"
    @model_validator(mode="after")
    def validate_time(self) -> 'StatsGroupBy':
        if self.from_time is None:
            self.from_time = self.to - datetime.timedelta(days=7)
        if self.groupBy == "hour" and self.to - self.from_time > datetime.timedelta(days=7):
            raise ValueError("cannot use hour for such a long field")
        if self.groupBy == "day" and self.to - self.from_time > datetime.timedelta(days=90):
            raise ValueError("cannot use day for such a long field")
        if self.groupBy == "week" and self.to - self.from_time > datetime.timedelta(days=365):
            raise ValueError("cannot use week for such a long field")
        return self

class TimePoint(BaseModel):
    bucketStart: datetime.datetime
    txCount: int
    gmv: float
    approvalRate: float
    declineRate: float


class TimePointsOut(BaseModel):
    points: list[TimePoint]


class RuleMatchRow(BaseModel):
    ruleId: uuid.UUID
    ruleName: str
    matches: int
    uniqueUsers: int
    uniqueMerchants: Optional[int] = None
    shareOfDeclines: float



class RulesStatsIn(StatsOverviewIn):
    top: int = 20


class RuleStatsOut(BaseModel):
    items: list[RuleMatchRow]
