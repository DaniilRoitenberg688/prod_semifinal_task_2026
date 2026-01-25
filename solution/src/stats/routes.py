from typing import Annotated
import uuid
import datetime

from fastapi import APIRouter, Depends, Query
from src.exceptions import ApiError, ErrorCode
from src.stats.schemes import (
    GroupByEnum,
    RiskMerchantIn,
    RiskMerchantOut,
    RulesStatsIn,
    RuleStatsOut,
    StatsGroupBy,
    StatsOverviewIn,
    StatsOverviewOut,
    TimePoint,
    TimePointsOut,
    UserRiskProfile,
)
from src.stats.service import (
    get_merchants,
    get_rates,
    get_transactions_sum,
    get_rules_stats,
    merchant_get_risk,
)
from src.transactions.repository import (
    get_all_transactions_grouped_by_merchant,
    get_all_transactions_stats,
    get_transcations_by_user_id,
)
from src.users.models import User, UserRole
from src.users.service import check_token_admin_only
from src.transactions.models import TransactionStatus
from src.users.repository import get_user_by_id

router = APIRouter(prefix="/api/v1/stats")


@router.get("/overview")
async def get_overview(
    filter_params: Annotated[StatsOverviewIn, Query()],
    current_user: User = Depends(check_token_admin_only),
) -> StatsOverviewOut:
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
        topRiskMerchants=merchs[:10],
    )


@router.get("/transactions/timeseries")
async def timeseries(
    filter_params: Annotated[StatsGroupBy, Query()],
    current_user: User = Depends(check_token_admin_only),
) -> TimePointsOut:
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
                    declineRate=der,
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
                declineRate=der,
            )
        )

    return TimePointsOut(points=points)


@router.get("/rules/matches")
async def rule_stats(
    filter: Annotated[RulesStatsIn, Query()],
    current_user: User = Depends(check_token_admin_only),
) -> RuleStatsOut:
    items = await get_rules_stats(filter)
    return RuleStatsOut(items=items)


@router.get("/merchants/risk")
async def risk_merchants(
    filter: Annotated[RiskMerchantIn, Query()],
    current_user: User = Depends(check_token_admin_only),
) -> RiskMerchantOut:
    d = await merchant_get_risk(filter)
    return RiskMerchantOut(items=d)


@router.get("/users/{id}/risk-profile")
async def user_rist(
    id: uuid.UUID, current_user: User = Depends(check_token_admin_only)
) -> UserRiskProfile:
    user = current_user
    if current_user.user_role == UserRole.admin:
        user = await get_user_by_id(id)
    if user is None:
        raise ApiError(
            status_code=404,
            err_code=ErrorCode.not_found,
            message="user not found",
            details={
            }
        )
    ts = await get_transcations_by_user_id(user.id)
    if not ts:
        return UserRiskProfile(
            txCount_24h=0,
            gmv_24h=0,
            userId=user.id,
            distinctCities_24h=0,
            distinctDevices_24h=0,
            distinctIps_24h=0,
            declineRate_30d=0,
        ) 
    ts = sorted(ts, key=lambda x: x.timestamp, reverse=True)
    thts = list(
        filter(
            lambda x: datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(hours=24)
            <= x.timestamp
            < datetime.datetime.now(datetime.timezone.utc),
            ts,
        )
    )

    tdts = list(
        filter(
            lambda x: datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=30)
            <= x.timestamp
            < datetime.datetime.now(datetime.timezone.utc),
            ts,
        )
    )

    if not tdts:
        return UserRiskProfile(
            txCount_24h=0,
            gmv_24h=0,
            userId=user.id,
            distinctCities_24h=0,
            distinctDevices_24h=0,
            distinctIps_24h=0,
            declineRate_30d=0,
            lastSeenAt=ts[0].timestamp
        ) 
    devs = set()
    ips = set()
    cit = set()
    gmv = 0
    for i in thts:
        gmv += i.amount
        devs.add(i.device_id)
        ips.add(i.ip_address)
        cit.add(i.city)

    dec = len([i for i in tdts if i.status == TransactionStatus.declined])

    return UserRiskProfile(
        txCount_24h=len(thts),
        gmv_24h=gmv,
        userId=user.id,
        distinctCities_24h=len(cit),
        distinctDevices_24h=len(devs),
        distinctIps_24h=len(ips),
        declineRate_30d=dec/len(tdts),
        lastSeenAt=ts[0].timestamp
    ) 
    




