from typing import Tuple, Dict

from fastapi import status
from src.fraud_rules.repository import get_rule_all_results, get_rules
from src.transactions.models import Transaction, TransactionStatus
from src.stats.schemes import (
    MerchantRiskRow,
    RiskMerchantIn,
    RuleMatchRow,
    RulesStatsIn,
)

from src.transactions.repository import (
    get_all_transactions_stats,
    get_transaction_by_id,
)


async def get_transactions_sum(trs: list[Transaction]) -> float:
    return sum([i.amount for i in trs])


async def get_rates(trs: list[Transaction]) -> Tuple[float, float]:
    if len(trs) == 0:
        return (0, 0)
    apr_c = len([i for i in trs if i.status == TransactionStatus.approved])
    apr = apr_c / len(trs)
    return (apr, 1 - apr)


async def get_merchants(trs: list[Transaction]) -> list[MerchantRiskRow]:
    mats: dict[str, list[Transaction]] = {}
    for t in trs:
        if t.merchant_id is None:
            continue
        if t.merchant_id in mats:
            mats[t.merchant_id].append(t)
        else:
            mats[t.merchant_id] = [t]

    res: list[MerchantRiskRow] = []
    for i, ts in mats.items():
        gmv = await get_transactions_sum(ts)
        apr, der = await get_rates(ts)
        res.append(
            MerchantRiskRow(merchantId=i, txCount=len(ts), gmv=gmv, declineRate=der)
        )

    return res


async def get_rules_stats(filter_d: RulesStatsIn) -> list[RuleMatchRow]:
    rules = await get_rules()
    transactions = await get_all_transactions_stats(filter_d)
    transactions = list(
        filter(lambda a: a.status == TransactionStatus.declined, transactions)
    )
    items: list[RuleMatchRow] = []
    for r in rules:
        ress = await get_rule_all_results(r)
        if not ress:
            continue
        users = set()
        merchants = set()
        matched = 0
        for res in ress:
            tr = await get_transaction_by_id(res.transaction_id)
            if tr is None:
                continue
            if filter_d.from_time is None:
                continue
            if not (filter_d.from_time <= tr.timestamp < filter_d.to):
                continue
            if res.matched:
                matched += 1
                users.add(tr.user_id)
                merchants.add(tr.merchant_id)

        items.append(
            RuleMatchRow(
                ruleId=r.id,
                ruleName=r.name,
                matches=matched,
                uniqueUsers=len(users),
                uniqueMerchants=len(merchants),
                shareOfDeclines=(matched / len(transactions)),
            )
        )
    return sorted(items, key=lambda x: -x.matches)[: filter_d.top]


async def merchant_get_risk(filter: RiskMerchantIn) -> list[MerchantRiskRow]:
    trans = await get_all_transactions_stats(filter)
    d: Dict[str, MerchantRiskRow] = {}
    for t in trans:
        if t.merchant_id not in d:
            d[t.merchant_id] = MerchantRiskRow(
                merchantId=t.merchant_id,
                txCount=1,
                gmv=t.amount,
                merchantCategoryCode=t.merchant_category_code,
                declineRate=(1 if t.status == TransactionStatus.declined else 0),
            )
        else:
            d[t.merchant_id].txCount += 1
            d[t.merchant_id].gmv += t.amount
            d[t.merchant_id].declineRate = (
                d[t.merchant_id].declineRate * d[t.merchant_id].txCount
                - 1
                + (1 if t.status == TransactionStatus.declined else 0)
            ) / d[t.merchant_id].txCount

    v = list(d.values())
    return v[:filter.top]
