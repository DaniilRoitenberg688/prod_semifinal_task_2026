from src.database import async_session_maker
import uuid
from typing import Optional
from sqlalchemy import func, select
from src.transactions.schemes import (
    FilterTransactionsQuery,
    TransactionScheme,
    CreateTranscation,
    TransactionLocation,
)
from src.transactions.models import Transaction
from src.transaction_result.models import TransactionRuleResult
from src.stats.schemes import MerchantRiskRow, RiskMerchantIn, StatsOverviewIn


def to_scheme_transaction(transaction: Transaction) -> TransactionScheme:
    loc = TransactionLocation(
        country=transaction.country,
        city=transaction.city,
        longitude=transaction.longitude,
        latitude=transaction.latitude,
    )
    d = transaction.__dict__
    md = d.pop("tr_metadata")
    d["metadata"] = md
    transaction_sc = TransactionScheme.model_validate(d, by_name=True)
    transaction_sc.location = loc
    return transaction_sc


async def create_transaction(transaction_data: CreateTranscation) -> Transaction:
    async with async_session_maker() as session:
        di = transaction_data.model_dump(by_alias=False)
        location = di.pop("location")
        di.update(location)
        md = di.pop("metadata")
        di["tr_metadata"] = md
        transaction = Transaction(**di)
        session.add(transaction)
        await session.commit()
        await session.refresh(transaction)
        return transaction


async def get_transaction_all_rule_results(
    transaction: Transaction,
) -> list[TransactionRuleResult]:
    async with async_session_maker() as session:
        q = select(TransactionRuleResult).where(
            TransactionRuleResult.transaction_id == transaction.id
        )
        res = await session.scalars(q)
        return list(res.all())


async def get_transaction_by_id(id: uuid.UUID) -> Optional[Transaction]:
    async with async_session_maker() as session:
        q = select(Transaction).where(Transaction.id == id)
        res = await session.execute(q)
        rule: Optional[Transaction] = res.scalars().first()
        if rule is None:
            return None
        return rule


async def get_transactions() -> list[Transaction]:
    async with async_session_maker() as session:
        q = select(Transaction)
        res = await session.scalars(q)
        return list(res.all())


async def get_transcations_by_user_id(user_id: uuid.UUID) -> list[Transaction]:
    async with async_session_maker() as session:
        q = select(Transaction).where(Transaction.user_id == user_id)
        res = await session.scalars(q)
        return list(res.all())


async def get_all_transactions(filters: FilterTransactionsQuery) -> list[Transaction]:
    async with async_session_maker() as session:
        q = select(Transaction)
        if filters.userId is not None:
            q = q.where(Transaction.user_id == filters.userId)
        if filters.status is not None:
            q = q.where(Transaction.status == filters.status)
        if filters.isFraud is not None:
            q = q.where(Transaction.is_fraud == filters.isFraud)
        if filters.from_time is not None:
            q = q.where(Transaction.timestamp >= filters.from_time)
        if filters.to is not None:
            q = q.where(Transaction.timestamp < filters.to)
        q = (
            q.order_by(Transaction.timestamp.desc())
            .offset(filters.page * filters.size)
            .limit(filters.size)
        )
        res = await session.scalars(q)
        return list(res.all())


async def get_all_transactions_stats(filters: StatsOverviewIn) -> list[Transaction]:
    async with async_session_maker() as session:
        q = select(Transaction)
        if filters.from_time is not None:
            q = q.where(Transaction.timestamp >= filters.from_time)
        if filters.to is not None:
            q = q.where(Transaction.timestamp < filters.to)
        q = q.order_by(Transaction.timestamp.desc())
        res = await session.scalars(q)
        return list(res.all())


async def get_all_transactions_grouped_by_merchant(filters: RiskMerchantIn):
    async with async_session_maker() as session:
        q = (
            select(
                func.sum(Transaction.amount),
                Transaction.merchant_id,
                Transaction.merchant_category_code,
                func.count(Transaction.status),
            )
            .group_by(Transaction.merchant_id, Transaction.merchant_category_code)
            .where(filters.from_time <= Transaction.timestamp).where(Transaction.timestamp < filters.to)
        )
        r = await session.execute(q)
        return r.all()
