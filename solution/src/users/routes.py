from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ApiError, ErrorCode
from src.database import get_session
from src.users.models import User
from src.users.repository import create_token, create_user, get_user_by_email, to_scheme
from src.users.schemas import LoginRequest, User as UserScheme, RegisterUser, UserOut, UserOutWithExp


auth_router = APIRouter(prefix="/api/v1/auth")


@auth_router.post("/register", status_code=201)
async def register_user(
    user_data: RegisterUser, session: AsyncSession = Depends(get_session)
) -> UserOut:
    u = await get_user_by_email(session, user_data.email)
    print(u)
    if u is not None:
        raise ApiError(
            status_code=409,
            err_code=ErrorCode.email_already_exists,
            message="user already exists",
        )

    user: User = await create_user(session, user_data)
    user_out: UserScheme = to_scheme(user)
    token: str = create_token(user.id)
    return UserOut(accessToken=token, user=user_out)


@auth_router.post("/login", status_code=200)
async def login_user(data: LoginRequest, session: AsyncSession = Depends(get_session)):
    user: User | None = await get_user_by_email(session, data.email)
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

    token = create_token(user.id)
    user_out = to_scheme(user)
    return UserOutWithExp(accessToken=token, user=user_out)


