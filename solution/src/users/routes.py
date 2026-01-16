from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ApiError, ErrorCode
from src.database import get_session
from src.users.repository import create_token, create_user, get_user_by_email
from src.users.schemas import User, RegisterUser, UserOut


auth_router = APIRouter(prefix="/api/v1/auth")


@auth_router.post("/register")
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
    token: str = create_token(user.id)
    return UserOut(token=token, user=user)
