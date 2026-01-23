from pydantic import BaseModel, Field
from pydantic.aliases import AliasChoices
import uuid

class RuleResult(BaseModel):
    rule_id: uuid.UUID = Field(validation_alias=AliasChoices("rule_id", "ruleId"), alias="ruleId")
    rule_name: str = Field(validation_alias=AliasChoices("rule_name", "ruleName"), alias="ruleName")
    priority: int
    matched: bool
    description: str
