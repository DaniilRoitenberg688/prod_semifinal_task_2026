from enum import Enum
from typing import Any
import uuid
from fastapi import HTTPException
import datetime

from pydantic import BaseModel, Field



class ErrorCode(Enum):
    bad_request = "BAD_REQUEST"
    validation_failed = "VALIDATION_FAILED"
    unauthorized = "UNAUTHORIZED"
    forbidden = "FORBIDDEN"
    not_found = "NOT_FOUND"
    user_not_found = "USER_NOT_FOUND"
    email_already_exists = "EMAIL_ALREADY_EXISTS"
    user_inactive = "USER_INACTIVE"
    dsl_parse_error = "DSL_PARSE_ERROR"
    dsl_invalid_field = "DSL_INVALID_FIELD"
    dsl_invalid_operator = "DSL_INVALID_OPERATOR"
    rule_name_already_exists = "RULE_NAME_ALREADY_EXISTS"
    internal_server_error = "INTERNAL_SERVER_ERROR"

class ApiError(Exception):
    status_code: int
    err_code: str
    message: str
    trace_id: str
    time_stamp: str
    path: str

    def __init__(self, status_code, err_code: ErrorCode, message):
        self.status_code = status_code
        self.err_code = err_code.value
        self.message = message
        self.time_stamp = str(datetime.datetime.now())
        self.trace_id = str(uuid.uuid4())

class FieldError(BaseModel):
    field: Any
    issue: str
    rejected_Value: Any | None

class ValidationError(ApiError):
    field_errors: list[dict]
    def __init__(self, status_code, err_code, message, field_errors):
        super().__init__(status_code, err_code, message)
        self.field_errors = field_errors

