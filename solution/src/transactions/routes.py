from typing import Optional
import uuid
from fastapi import APIRouter, Depends

from src.exceptions import ApiError, ErrorCode
from src.fraud_rules.repository import get_enabled_rules
from src.transactions.schemes import TransactionResponse, CreateTranscation, CreateTranscationRequest, RuleResult, TransactionLocation
from src.users.models import User, UserRole
from src.users.service import check_token
from src.transactions.service import check_transaction
from src.transactions.models import TransactionStatus
from src.transactions.repository import create_transaction, get_transaction_all_rule_results, to_scheme_transaction, get_transaction_by_id
from src.users.repository import get_user_by_id
from src.transaction_result.repositiry import create_transaction_result, to_scheme_transaction_result
from src.transaction_result.schemes import RuleResult


router = APIRouter(prefix="/api/v1/transactions")

@router.post("", status_code=201)
async def create_transaction_route(transaction_data: CreateTranscationRequest, current_user: User = Depends(check_token)) -> TransactionResponse:
    if transaction_data.user_id != current_user.id and current_user.user_role != UserRole.admin:
        raise ApiError(
            status_code=403,
            err_code=ErrorCode.forbidden,
            message="cannot create transaction for another user"
        )
    user: Optional[User] = await get_user_by_id(transaction_data.user_id)
    if user is None:
        raise ApiError(
            status_code=404,
            err_code=ErrorCode.not_found,
            message="no such user",
            details={
                "userId": str(transaction_data.user_id)
            }
        )

    if not user.is_active:
        raise ApiError(
            status_code=403,
            err_code=ErrorCode.forbidden,
            message="user is deactivated",
            details={
                "userId": str(transaction_data.user_id)
            }
        )

    data = {
        "amount": transaction_data.amount,
        "currency": transaction_data.currency,
        "merchantId": transaction_data.merchant_id,
        "ipAddress": transaction_data.ip_address,
        "deviceId": transaction_data.device_id,
        "user": {"age": user.age, "region": user.region},
    }
    rules = await get_enabled_rules()
    rules_results: list[RuleResult] = []
    data_d = transaction_data.model_dump(by_alias=True)
    location_d = data_d.pop("location")
    transaction_data_new = CreateTranscation(
        id=uuid.uuid4(),
        status=TransactionStatus.approved,
        isFraud=False,
        location=TransactionLocation(**location_d),
        **data_d

    )
    for rule in rules:
        res = check_transaction(data, rule)
        if res.matched:
            transaction_data_new.status = TransactionStatus.declined
            transaction_data_new.is_fraud = True
        rules_results.append(res)

    transaction = await create_transaction(transaction_data_new)

    for rule_result in rules_results:
        _ = await create_transaction_result(rule_result, transaction.id)



    transaction_out = to_scheme_transaction(transaction)

    return TransactionResponse(
        transaction=transaction_out,
        ruleResults=rules_results
    )


@router.get('/{id}')
async def get_transactions_by_id_route(id: uuid.UUID, current_user: User = Depends(check_token)) -> TransactionResponse:
    transaction = await get_transaction_by_id(id)
    if transaction is None:
        raise ApiError(
            status_code=404,
            err_code=ErrorCode.not_found,
            message="no such trans",
            details={
                "transactionId": str(id)
            }
        )
    transaction_data = to_scheme_transaction(transaction)
    if transaction_data.user_id != current_user.id and current_user.user_role != UserRole.admin:
        raise ApiError(
            status_code=403,
            err_code=ErrorCode.forbidden,
            message="cannot get transaction for another user"
        )
    user: Optional[User] = await get_user_by_id(transaction_data.user_id)
    if user is None:
        raise ApiError(
            status_code=404,
            err_code=ErrorCode.not_found,
            message="no such user",
            details={
                "userId": str(transaction_data.user_id)
            }
        )

    if not user.is_active:
        raise ApiError(
            status_code=403,
            err_code=ErrorCode.forbidden,
            message="user is deactivated",
            details={
                "userId": str(transaction_data.user_id)
            }
        )
    results = await get_transaction_all_rule_results(transaction)
    results_data: list[RuleResult] = []
    for rule_result in results:
        results_data.append(to_scheme_transaction_result(rule_result))

    return TransactionResponse(
        transaction=transaction_data,
        ruleResults=results_data
    )


