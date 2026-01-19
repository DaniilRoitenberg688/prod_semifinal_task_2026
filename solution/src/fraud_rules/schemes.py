from typing import Optional
from pydantic import BaseModel, Field, AliasChoices
import datetime
import uuid



class BaseRule(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: Optional[str] = Field(max_length=500)
    dsl_expression: str = Field(min_length=3, max_length=2000, validation_alias=AliasChoices("dsl_expression", "dslExpression"))
    enabled: bool = Field(default=True)
    priority: int = Field(ge=1, default=100)

class CreateRule(BaseRule):
    pass


class RuleScheme(BaseRule):
    id: uuid.UUID
    created_at: datetime.datetime = Field(
        validation_alias=AliasChoices("created_at"), alias="createdAt"
    )
    updated_at: datetime.datetime = Field(
        validation_alias=AliasChoices("updated_at"), alias="updatedAt"
    )
