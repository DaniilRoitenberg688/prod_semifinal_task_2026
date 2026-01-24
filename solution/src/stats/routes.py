from typing import Annotated

from fastapi import APIRouter, Depends, Query
from src.exceptions import ApiError, ErrorCode
from src.stats.schemes import (
    GroupByEnum,
    RulesStatsIn,
    RuleStatsOut,
    StatsGroupBy,
    StatsOverviewIn,
    StatsOverviewOut,
    TimePoint,
    TimePointsOut,
)
from src.stats.service import get_merchants, get_rates, get_transactions_sum, get_rules_stats
from src.transactions.repository import get_all_transactions_stats
from src.users.models import User
from src.users.service import check_token_admin_only

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
        topRiskMerchants=merchs[:10]
    )


@router.get("/transactions/timeseries")
async def timeseries(filter_params: Annotated[StatsGroupBy, Query()], current_user: User = Depends(check_token_admin_only)) -> TimePointsOut:
    if filter_params.from_time is None:
        raise ApiError(
            status_code=422,
            err_code=ErrorCode.validation_failed,
            message="cannot validate",
        )
    last = filter_params.from_time  
    next = filter_params.from_time + GroupByEnum[filter_params.groupBy].value
    points: list[TimePoint] = []
    while next < filter_params.to:
        f = StatsOverviewIn().model_validate({"from": last, "to": next})

        transactions = await get_all_transactions_stats(f)
        if transactions:
            gmv = await get_transactions_sum(transactions)
            apr, der = await get_rates(transactions)
            points.append(
                TimePoint(
                    bucketStart=last,
                    txCount=len(transactions),
                    gmv=gmv,
                    approvalRate=apr,
                    declineRate=der
                )
            )
        last = next
        next += GroupByEnum[filter_params.groupBy].value


    f = StatsOverviewIn().model_validate({"from": next, "to": filter_params.to})

    transactions = await get_all_transactions_stats(f)
    if transactions:
        gmv = await get_transactions_sum(transactions)
        apr, der = await get_rates(transactions)
        points.append(
            TimePoint(
                bucketStart=last,
                txCount=len(transactions),
                gmv=gmv,
                approvalRate=apr,
                declineRate=der
            )
        )


    return TimePointsOut(points=points)



@router.get("/rules/matches")
async def rule_stats(filter: RulesStatsIn) -> RuleStatsOut:
    items = await get_rules_stats(filter)
    return RuleStatsOut(items=items)
        

    
