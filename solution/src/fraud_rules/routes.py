from os import pread
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from src.exceptions import ApiError, ErrorCode
from src.fraud_rules.service import validate_rule
from src.fraud_rules.models import FraudRule

from src.fraud_rules.repository import get_rule_by_name, get_rules, to_scheme, create_rule
from src.fraud_rules.schemes import CreateRule, RuleScheme
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
    validate_rule(rule_data.dsl_expression)
    rule: FraudRule = await create_rule(rule_data)
    return to_scheme(rule)
    



