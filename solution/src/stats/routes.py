from typing import Annotated
from fastapi import APIRouter, Depends, Query
from src.users.models import User
from src.users.service import check_token_admin_only

from src.stats.schemes import StatsOverviewIn, StatsOverviewOut
from src.transactions.repository import get_all_transactions_stats
from src.stats.service import get_merchants, get_rates, get_transactions_sum


router = APIRouter(prefix="/api/v1/stats")


@router.get("/overview")
async def get_overview(filter_params: Annotated[StatsOverviewIn, Query()], current_user: User = Depends(check_token_admin_only)) -> StatsOverviewOut:
    transactions = await get_all_transactions_stats(filter_params)
    gmv = await get_transactions_sum(transactions)
    apr, der = await get_rates(transactions)
    merchs = await get_merchants(transactions)
    return StatsOverviewOut(
        from_time=filter_params.from_time,
        to=filter_params.to,
        volume=len(transactions),
        gmv=gmv,
        approvalRate=apr,
        declineRate=der,
        topRiskMerchants=merchs
    )
    
