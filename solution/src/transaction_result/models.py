from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base
import uuid


class TransactionRuleResult(Base):
    __tablename__="transactions_rule_result"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    transaction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transactions.id"))
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fraud_rules.id"))
    rule_name: Mapped[str] = mapped_column()
    rule_priority: Mapped[int] = mapped_column()
    description: Mapped[str] = mapped_column()
    matched: Mapped[bool] = mapped_column(default=False)


    def to_dict(self) -> dict:
        d = {
            "ruleId": self.rule_id,
            "ruleName": self.rule_name,
            "priority": self.rule_priority,
            "matched": self.matched,
            "description": self.description
        }
        return d




