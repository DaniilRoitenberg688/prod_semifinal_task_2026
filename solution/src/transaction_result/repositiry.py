from src.database import async_session_maker
import uuid
from typing import Optional
from src.transaction_result.schemes import RuleResult
from src.transaction_result.models import TransactionRuleResult



def to_scheme_transaction_result(res: TransactionRuleResult) -> RuleResult:
    return RuleResult.model_validate(res.to_dict(), by_alias=True)


async def create_transaction_result(d: RuleResult, transaction_id: uuid.UUID) -> TransactionRuleResult:
    async with async_session_maker() as session:
        trr =  TransactionRuleResult(
            transaction_id=transaction_id,
            rule_id=d.rule_id,
            id=uuid.uuid4(),
            description=d.description,
            matched=d.matched,
            rule_name=d.rule_name,
            rule_priority=d.priority
        )
        session.add(trr)
        await session.commit()
        return trr

    

