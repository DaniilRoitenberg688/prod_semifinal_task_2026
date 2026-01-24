from src.fraud_rules.schemes import RuleScheme, CreateRule, UpdateRule
from src.fraud_rules.models import FraudRule
from src.database import async_session_maker
import uuid
from sqlalchemy import select
from src.transaction_result.models import TransactionRuleResult
from src.stats.schemes import StatsOverviewIn


def to_scheme(rule: FraudRule) -> RuleScheme:
    print(rule.__dict__)
    rule_sc= RuleScheme.model_validate(rule.__dict__)
    return rule_sc

async def create_rule(rule_data: CreateRule) -> FraudRule:
    async with async_session_maker() as session:
        rule_dict = rule_data.model_dump()
        rule = FraudRule(**rule_dict)
        rule.id = uuid.uuid4()
        session.add(rule)
        await session.commit()
        await session.refresh(rule)
        return rule


async def get_rule_by_id(id: uuid.UUID) -> FraudRule | None:
    async with async_session_maker() as session:
        q = select(FraudRule).where(FraudRule.id == id)
        res = await session.execute(q)
        rule: FraudRule | None = res.scalars().first()
        if rule is None:
            return None
        return rule
    
async def get_rule_by_name(name: str) -> FraudRule | None:
    async with async_session_maker() as session:
        q = select(FraudRule).where(FraudRule.name == name)
        res = await session.execute(q)
        rule: FraudRule | None = res.scalars().first()
        if rule is None:
            return None
        return rule


async def get_rules() -> list[FraudRule]:
    async with async_session_maker() as session:
        q = select(FraudRule)
        res = await session.scalars(q)
        return list(res.all())

async def get_enabled_rules() -> list[FraudRule]:
    async with async_session_maker() as session:
        q = select(FraudRule).where(FraudRule.enabled).order_by(FraudRule.priority.asc(), FraudRule.id.asc())
        res = await session.scalars(q)
        return list(res.all())


async def update_rule(rule: FraudRule, data: UpdateRule):
    async with async_session_maker() as session:
        rule.name = data.name
        if data.description is not None:
            rule.description = data.description
        rule.enabled = data.enabled
        rule.dsl_expression = data.dsl_expression
        rule.priority = data.priority
        session.add(rule)
        await session.commit()


async def deactivate_rule(rule: FraudRule):
    async with async_session_maker() as session:
        rule.enabled = False
        session.add(rule)
        await session.commit()


async def get_rule_all_results(rule: FraudRule) -> list[TransactionRuleResult]:
    async with async_session_maker() as session:
        q = select(TransactionRuleResult).where(TransactionRuleResult.rule_id==rule.id)
        res = await session.scalars(q)
        return list(res.all())



async def get_all_rule_results_stats(filters: StatsOverviewIn) -> list[TransactionRuleResult]:
    async with async_session_maker() as session:
        q = select(TransactionRuleResult)
        if filters.from_time is not None:
            q = q.where(TransactionRuleResult.created_at >= filters.from_time)
        if filters.to is not None:
            q = q.where(TransactionRuleResult.created_at < filters.to)
        res = await session.scalars(q)
        return list(res.all())


        
