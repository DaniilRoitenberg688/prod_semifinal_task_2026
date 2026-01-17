from functools import wraps
from typing import Callable, Any, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2AuthorizationCodeBearer
from src.exceptions import ApiError, ErrorCode
from src.users.repository import verify_token
from typing import Annotated

from src.users.models import User, UserRole



sec = HTTPBearer()
async def check_token(token: Annotated[HTTPAuthorizationCredentials, Depends(sec)]):
    user: Optional[User] = await verify_token(token.credentials)
    if user is None:
        raise ApiError(
            status_code=404,
            err_code=ErrorCode.not_found,
            message="no user"
        )
    return user

async def check_token_admin_only(token: Annotated[HTTPAuthorizationCredentials, Depends(sec)]):
    user: Optional[User] = await verify_token(token.credentials)
    if user is None:
        raise ApiError(
            status_code=404,
            err_code=ErrorCode.not_found,
            message="no user"
        )
    if user.user_role != UserRole.admin and user.user_role != "ADMIN":
        raise ApiError(
            status_code=403,
            err_code=ErrorCode.forbidden,
            message="no access"
        )
    return user





