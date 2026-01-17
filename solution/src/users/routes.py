from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ApiError, ErrorCode
from src.database import get_session
from src.users.models import User, UserRole
from src.users.repository import create_token, create_user, get_user_by_email, get_users, to_scheme
from src.users.schemas import LoginRequest, UserScheme, RegisterUser, UserOut, UserOutWithExp, PagedUsers
from src.users.service import check_token, check_token_admin_only


auth_router = APIRouter(prefix="/api/v1/auth")



@auth_router.post("/register", status_code=201)
async def register_user(
    user_data: RegisterUser
) -> UserOut:
    u = await get_user_by_email(user_data.email)
    print(u)
    if u is not None:
        raise ApiError(
            status_code=409,
            err_code=ErrorCode.email_already_exists,
            message="user already exists",
        )

    user: User = await create_user(user_data)
    user_out: UserScheme = to_scheme(user)
    token: str = create_token(user)
    return UserOut(accessToken=token, user=user_out)


@auth_router.post("/login", status_code=200)
async def login_user(data: LoginRequest):
    user: User | None = await get_user_by_email(data.email)
    if user is None:
        raise ApiError(
            status_code=401,
            err_code=ErrorCode.unauthorized,
            message="wrong creds"
        )

    res: bool = user.check_password(data.password)
    if not res:
        raise ApiError(
            status_code=401,
            err_code=ErrorCode.unauthorized,
            message="wrong creds"
        )

    if not user.is_active:
        raise ApiError(
            status_code=423,
            err_code=ErrorCode.user_inactive,
            message="inactive user"
        )

    token = create_token(user)
    user_out = to_scheme(user)
    return UserOutWithExp(accessToken=token, user=user_out)


user_router = APIRouter(prefix="/api/v1/users")


@user_router.get("/", status_code=200)
async def get_all_users(page: int=0, size: int=20, user:User=Depends(check_token_admin_only)) -> PagedUsers:
    users = await get_users(page, size)
    users_data = [to_scheme(i) for i in users]
    return PagedUsers(
        users=users_data,
        page=page,
        total=len(users_data),
        size=size
    )



@user_router.post("/", status_code=201)
async def create_user_admin(
    user_data: RegisterUser, current_user:User=Depends(check_token_admin_only)) -> UserScheme:
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
async def get_my_user(current_user:User=Depends(check_token)) -> UserScheme:
    return to_scheme(current_user)
