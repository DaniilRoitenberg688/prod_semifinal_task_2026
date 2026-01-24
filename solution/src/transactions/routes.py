from typing import Annotated, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Response, responses, status
from pydantic import ValidationError

from src.exceptions import ApiError, ErrorCode, ValidationError as CustomValidationError
from src.fraud_rules.repository import get_enabled_rules
from src.transactions.schemes import (
    BatchResponse,
    CreateBatchTransactions,
    FilterTransactionsQuery,
    PagedTransactions,
    TransactionBatchResult,
    TransactionResponse,
    CreateTranscation,
    CreateTranscationRequest,
    RuleResult,
    TransactionLocation,
    TransactionScheme,
)
from src.users.models import User, UserRole
from src.users.service import check_token
from src.transactions.service import check_transaction
from src.transactions.models import TransactionStatus
from src.transactions.repository import (
    create_transaction,
    get_all_transactions,
    get_transaction_all_rule_results,
    to_scheme_transaction,
    get_transaction_by_id,
)
from src.users.repository import get_user_by_id
from src.transaction_result.repositiry import (
    create_transaction_result,
    to_scheme_transaction_result,
)
from src.transaction_result.schemes import RuleResult


router = APIRouter(prefix="/api/v1/transactions")


@router.post("", status_code=201)
async def create_transaction_route(
    transaction_data: CreateTranscationRequest,
    current_user: User = Depends(check_token),
) -> TransactionResponse:
    if (
        transaction_data.user_id != current_user.id
        and current_user.user_role != UserRole.admin
    ):
        raise ApiError(
            status_code=403,
            err_code=ErrorCode.forbidden,
            message="cannot create transaction for another user",
        )
    user: Optional[User] = await get_user_by_id(transaction_data.user_id)
    if user is None:
        raise ApiError(
            status_code=404,
            err_code=ErrorCode.not_found,
            message="no such user",
            details={"userId": str(transaction_data.user_id)},
        )

    if not user.is_active:
        raise ApiError(
            status_code=403,
            err_code=ErrorCode.user_inactive,
            message="user is deactivated",
            details={"userId": str(transaction_data.user_id)},
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
        **data_d,
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

    return TransactionResponse(transaction=transaction_out, ruleResults=rules_results)


@router.get("")
async def get_all_transactions_routes(
    filter_params: Annotated[FilterTransactionsQuery, Query()],
    current_user=Depends(check_token),
) -> PagedTransactions:
    if current_user.user_role == UserRole.user:
        filter_params.userId = current_user.user_id
    transactions = await get_all_transactions(filter_params)
    items = [to_scheme_transaction(t) for t in transactions]
    return PagedTransactions(
        items=items,
        total=len(items),
        page=filter_params.page,
        size=filter_params.size
    )


@router.get("/{id}")
async def get_transactions_by_id_route(
    id: uuid.UUID, current_user: User = Depends(check_token)
) -> TransactionResponse:
    transaction = await get_transaction_by_id(id)
    if transaction is None:
        raise ApiError(
            status_code=404,
            err_code=ErrorCode.not_found,
            message="no such trans",
            details={"transactionId": str(id)},
        )
    transaction_data = to_scheme_transaction(transaction)
    if (
        transaction_data.user_id != current_user.id
        and current_user.user_role != UserRole.admin
    ):
        raise ApiError(
            status_code=403,
            err_code=ErrorCode.forbidden,
            message="cannot get transaction for another user",
        )
    user: Optional[User] = await get_user_by_id(transaction_data.user_id)
    if user is None:
        raise ApiError(
            status_code=404,
            err_code=ErrorCode.not_found,
            message="no such user",
            details={"userId": str(transaction_data.user_id)},
        )

    if not user.is_active:
        raise ApiError(
            status_code=403,
            err_code=ErrorCode.user_inactive,
            message="user is deactivated",
            details={"userId": str(transaction_data.user_id)},
        )
    results = await get_transaction_all_rule_results(transaction)
    results_data: list[RuleResult] = []
    for rule_result in results:
        results_data.append(to_scheme_transaction_result(rule_result))

    return TransactionResponse(transaction=transaction_data, ruleResults=results_data)


@router.post("/batch", status_code=201)
async def create_batch(
    batch_data: CreateBatchTransactions,
    response: Response,
    current_user: User = Depends(check_token),
) -> BatchResponse:
    result: list[TransactionBatchResult] = []
    is_error = False
    for index, trans_raw in enumerate(batch_data.items):
        try:
            trans = CreateTranscationRequest.model_validate(trans_raw)
        except ValidationError as e:
            fields = []
            for i in e.errors():
                if i["type"] in ["json_invalid", "model_attributes_type"]:
                    result.append(
                        TransactionBatchResult(
                            index=index,
                            error=ApiError(
                                status_code=400,
                                err_code=ErrorCode.bad_request,
                                message="invalid json",
                            ).to_dict("/api/v1/transactions/batch"),
                        )
                    )

                print(i["loc"])
                fields.append(
                    {
                        "field": ".".join(
                            map(str, ["body", "items", index, *i["loc"]][1:])
                        ),
                        "issue": i["msg"],
                        "rejectedValue": i["input"],
                    }
                )

            is_error = True
            result.append(
                TransactionBatchResult(
                    index=index,
                    error=CustomValidationError(
                        status_code=422,
                        err_code=ErrorCode.validation_failed,
                        message="cannot validate data",
                        field_errors=fields,
                    ).to_dict("/api/v1/transactions/batch"),
                )
            )
            continue

        if current_user.user_role == UserRole.user:
            trans.user_id = current_user.id

        user = await get_user_by_id(trans.user_id)
        if user is None:
            is_error = True
            result.append(
                TransactionBatchResult(
                    index=index,
                    error=ApiError(
                        status_code=404,
                        err_code=ErrorCode.not_found,
                        message="cannot find user",
                        details={"userId": trans.user_id},
                    ).to_dict("/api/v1/transactions/batch"),
                )
            )
            continue

        if not user.is_active:
            is_error = True
            result.append(
                TransactionBatchResult(
                    index=index,
                    error=ApiError(
                        status_code=403,
                        err_code=ErrorCode.user_inactive,
                        message="user is deactivated",
                        details={"userId": trans.user_id},
                    ).to_dict("/api/v1/transactions/batch"),
                )
            )
            continue

        data = {
            "amount": trans.amount,
            "currency": trans.currency,
            "merchantId": trans.merchant_id,
            "ipAddress": trans.ip_address,
            "deviceId": trans.device_id,
            "user": {"age": user.age, "region": user.region},
        }
        rules = await get_enabled_rules()
        rules_results: list[RuleResult] = []
        data_d = trans.model_dump(by_alias=True)
        location_d = data_d.pop("location")
        transaction_data_new = CreateTranscation(
            id=uuid.uuid4(),
            status=TransactionStatus.approved,
            isFraud=False,
            location=TransactionLocation(**location_d),
            **data_d,
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
        result.append(
            TransactionBatchResult(
                index=index,
                decision=TransactionResponse(
                    transaction=transaction_out, ruleResults=rules_results
                ),
            )
        )

    if is_error:
        response.status_code = 207
    return BatchResponse(items=result)
