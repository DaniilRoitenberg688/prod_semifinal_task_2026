from os import pread
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from src.exceptions import ApiError, ErrorCode
from src.fraud_rules.service import normalize_rule, validate_rule
from src.fraud_rules.models import FraudRule

from src.fraud_rules.repository import deactivate_rule, get_rule_by_id, get_rule_by_name, get_rules, to_scheme, create_rule, update_rule
from src.fraud_rules.schemes import CreateRule, RuleScheme, UpdateRule, ValidateDSLRequet, ValidateDSLResponse
from src.users.service import check_token_admin_only
from src.users.models import User


router = APIRouter(prefix="/api/v1/fraud-rules")


@router.get("", status_code=200)
async def get_all_rules(current_user:User=Depends(check_token_admin_only)) -> list[RuleScheme]:
    rules = await get_rules()
    rules_d = [to_scheme(i) for i in rules]
    return rules_d

@router.post("", status_code=201)
async def create_rule_route(rule_data: CreateRule, current_user:User=Depends(check_token_admin_only) ) -> RuleScheme:
    f_rule: Optional[FraudRule] = await get_rule_by_name(rule_data.name)
    if f_rule is not None:
        raise ApiError(
            status_code=409,
            err_code=ErrorCode.rule_name_already_exists,
            message="exists"
        )
    valid, errors, _ = validate_rule(rule_data.dsl_expression)
#    if not valid:
#        raise errors[0]
    rule: FraudRule = await create_rule(rule_data)
    return to_scheme(rule)


@router.post("/validate", status_code=200)
async def validate_dsl_route(exp: ValidateDSLRequet, current_user:User=Depends(check_token_admin_only) ) -> ValidateDSLResponse:
    print(exp.dslExpression)
    valid, errors, _ = validate_rule(exp.dslExpression)
    if not valid:
        errs = [i.to_dict() for i in errors]
        return ValidateDSLResponse(
            isValid=False,
            normalizedExpression="",
            errors=errs
        )
    normis = normalize_rule(exp.dslExpression)
    return ValidateDSLResponse(
        isValid=True,
        normalizedExpression=normis,
        errors=[]
    )

@router.get("/{id}", status_code=200)
async def get_rule_route(id: uuid.UUID, current_user:User=Depends(check_token_admin_only) ) -> RuleScheme:
    rule = await get_rule_by_id(id)
    if rule is None:
        raise ApiError(
            status_code=404,
            err_code=ErrorCode.not_found,
            message="cannot find such rule"
        )
    rule_d = to_scheme(rule)
    return rule_d



@router.delete("/{id}", status_code=204)
async def delete_rule_route(id: uuid.UUID, current_user:User=Depends(check_token_admin_only) ) :
    rule = await get_rule_by_id(id)
    if rule is None:
        raise ApiError(
            status_code=404,
            err_code=ErrorCode.not_found,
            message="cannot find such rule"
        )
    await deactivate_rule(rule)


@router.put("/{id}", status_code=200)
async def update_rule_route(id: uuid.UUID, data: UpdateRule, current_user:User=Depends(check_token_admin_only) ) -> RuleScheme:
    rule = await get_rule_by_id(id)
    if rule is None:
        raise ApiError(
            status_code=404,
            err_code=ErrorCode.not_found,
            message="cannot find rule with this id"
        )
#    rule_with_name = await get_rule_by_name(data.name)
#    if rule_with_name is not None:
#        raise ApiError(
#            status_code=409,
#            err_code=ErrorCode.rule_name_already_exists,
#            message="exists"
#        )

    await update_rule(rule, data)
    rule_d = to_scheme(rule)
    return rule_d
    







    


