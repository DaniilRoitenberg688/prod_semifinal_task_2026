from typing import Tuple
from src.transactions.models import Transaction, TransactionStatus
from src.stats.schemes import MerchantRiskRow
import uuid


async def get_transactions_sum(trs: list[Transaction]) -> float:
    return sum([i.amount for i in trs])

async def get_rates(trs: list[Transaction]) -> Tuple[float, float]:
    if len(trs) == 0:
        return (0, 0)
    apr_c = len([i for i in trs if i.status == TransactionStatus.approved])
    apr = apr_c / len(trs)
    return (apr, 1-apr)



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
            MerchantRiskRow(
                merchantId=i,
                txCount=len(ts),
                gmv=gmv,
                declineRate=der
            )
        )

    return res


    
