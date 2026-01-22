from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from src.exceptions import ApiError, ErrorCode
from src.database import get_session
from src.users.models import User, UserRole
from src.users.repository import (
    create_token,
    create_user,
    deactivate_user,
    get_user_by_email,
    get_user_by_id,
    get_users,
    to_scheme,
    update_user,
)
from src.users.schemas import (
    CreateUser,
    LoginRequest,
    UserScheme,
    RegisterUser,
    UserOut,
    UserOutWithExp,
    PagedUsers,
    UpdateUser,
)
from src.users.service import check_token, check_token_admin_only


auth_router = APIRouter(prefix="/api/v1/auth")


@auth_router.post("/register", status_code=201)
async def register_user(user_data: RegisterUser) -> UserOut:
    u = await get_user_by_email(user_data.email)
    print(u)
    if u is not None:
        raise ApiError(
            status_code=409,
            err_code=ErrorCode.email_already_exists,
            message="user already exists",
        )

    user_data_cr = CreateUser(**user_data.model_dump())
    user: User = await create_user(user_data_cr)
    user_out: UserScheme = to_scheme(user)
    token: str = create_token(user)
    return UserOut(accessToken=token, user=user_out)


@auth_router.post("/login", status_code=200)
async def login_user(data: LoginRequest):
    user: User | None = await get_user_by_email(data.email)
    if user is None:
        raise ApiError(
            status_code=401, err_code=ErrorCode.unauthorized, message="wrong creds"
        )

    res: bool = user.check_password(data.password)
    if not res:
        raise ApiError(
            status_code=401, err_code=ErrorCode.unauthorized, message="wrong creds"
        )

    if not user.is_active:
        raise ApiError(
            status_code=423, err_code=ErrorCode.user_inactive, message="inactive user"
        )

    token = create_token(user)
    user_out = to_scheme(user)
    return UserOutWithExp(accessToken=token, user=user_out)


user_router = APIRouter(prefix="/api/v1/users")


@user_router.get("", status_code=200)
async def get_all_users(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(check_token_admin_only),
) -> PagedUsers:
    users = await get_users(page, size)
    users_data = [to_scheme(i) for i in users]
    return PagedUsers(users=users_data, page=page, total=len(users_data), size=size)


@user_router.post("", status_code=201)
async def create_user_admin(
    user_data: CreateUser, current_user: User = Depends(check_token_admin_only)
) -> UserScheme:
    u = await get_user_by_email(user_data.email)
    if u is not None:
        raise ApiError(
            status_code=409,
            err_code=ErrorCode.email_already_exists,
            message="user already exists",
        )
    user: User = await create_user(user_data)
    user_out: UserScheme = to_scheme(user)
    return user_out


@user_router.get("/me", status_code=200)
async def get_my_user(current_user: User = Depends(check_token)) -> UserScheme:
    return to_scheme(current_user)


@user_router.put("/me", status_code=200)
async def update_my_user(
    data: UpdateUser, current_user: User = Depends(check_token)
) -> UserScheme:
    if (
        current_user.user_role != UserRole.admin
        and data.user_role is not None
        and current_user.user_role != data.user_role
    ):
        raise ApiError(
            status_code=403, err_code=ErrorCode.forbidden, message="forbidden"
        )
    if (
        current_user.user_role != UserRole.admin
        and data.user_role is not None
        and current_user.is_active != data.is_active
    ):
        raise ApiError(
            status_code=403, err_code=ErrorCode.forbidden, message="forbidden"
        )
    await update_user(current_user, data)

    return to_scheme(current_user)


@user_router.get("/{id}", status_code=200)
async def get_user_by_id_route(
    id: uuid.UUID, current_user: User = Depends(check_token)
) -> UserScheme:
    if id != current_user.id and current_user.user_role != UserRole.admin:
        raise ApiError(
            status_code=403, err_code=ErrorCode.forbidden, message="forbidden"
        )

    user: Optional[User] = await get_user_by_id(id)
    if user is None:
        raise ApiError(
            status_code=404, err_code=ErrorCode.not_found, message="user not found"
        )

    return to_scheme(user)


@user_router.put("/{id}", status_code=200)
async def update_user_by_id_route(
    id: uuid.UUID, data: UpdateUser, current_user: User = Depends(check_token)
) -> UserScheme:
    if id != current_user.id and current_user.user_role != UserRole.admin:
        raise ApiError(
            status_code=403, err_code=ErrorCode.forbidden, message="forbidden"
        )

    user: Optional[User] = await get_user_by_id(id)
    if user is None:
        raise ApiError(
            status_code=404, err_code=ErrorCode.not_found, message="user not found"
        )

    if (
        current_user.user_role != UserRole.admin
        and data.user_role is not None
        and current_user.user_role != data.user_role
    ):
        raise ApiError(
            status_code=403, err_code=ErrorCode.forbidden, message="forbidden"
        )
    if (
        current_user.user_role != UserRole.admin
        and data.user_role is not None
        and current_user.is_active != data.is_active
    ):
        raise ApiError(
            status_code=403, err_code=ErrorCode.forbidden, message="forbidden"
        )
    await update_user(user, data)

    return to_scheme(user)



@user_router.delete("/{id}", status_code=204)
async def delete_user_by_id_route(
    id: uuid.UUID, current_user: User = Depends(check_token)
):


    if id != current_user.id and current_user.user_role != UserRole.admin:
        raise ApiError(
            status_code=403, err_code=ErrorCode.forbidden, message="forbidden"
        )

    user: Optional[User] = await get_user_by_id(id)
    if user is None:
        raise ApiError(
            status_code=404, err_code=ErrorCode.not_found, message="user not found"
        )

    await deactivate_user(user)

