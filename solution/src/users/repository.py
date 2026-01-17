import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.exceptions import ApiError, ErrorCode
from src.users.models import User
from src.users.schemas import CreateUser, RegisterUser, UpdateUser, UserScheme
from src.database import async_session_maker
import datetime
import jwt
from src.config import config


def create_token(user: User):
    payload = {
        "sub": str(user.id),
        "role": str(user.user_role.value),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),  # срок действия
        "iat": datetime.datetime.utcnow(),  # время выпуска
    }
    token = jwt.encode(payload, config.RANDOM_SECRET, "HS256")
    return token


async def verify_token(token: str) -> tuple[Optional[User], dict]:
    try:
        payload = jwt.decode(
            token, 
            config.RANDOM_SECRET,
            algorithms=["HS256"]
        )
        if payload["exp"] <= datetime.datetime.utcnow().microsecond:
            raise ApiError(
                status_code=401,
                err_code=ErrorCode.unauthorized,
                message="expired"
            )
        user = await get_user_by_id(payload["sub"])
        print(user)
        if user is None:
            raise ApiError(
                status_code=404,
                err_code=ErrorCode.not_found,
                message="cannot find user"
            )

        return user, payload
    except jwt.ExpiredSignatureError:
        raise ApiError(
            status_code=401,
            err_code=ErrorCode.unauthorized,
            message="expired"
        )
    except jwt.InvalidTokenError:
        raise ApiError(
            status_code=401,
            err_code=ErrorCode.unauthorized,
            message="invalid"
        )
    except Exception as e:
        raise ApiError(
            status_code=401,
            err_code=ErrorCode.unauthorized,
            message=f"dont know {e}"
        )

def to_scheme(user: User) -> UserScheme:
    user_sc = UserScheme.model_validate(user)
    return user_sc

async def create_user(user_data: CreateUser) -> User:
    async with async_session_maker() as session:
        user_dict = user_data.model_dump()
        password = user_dict.pop("password")
        user = User(**user_dict)
        user.id = uuid.uuid4()
        user.set_password(password)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def get_user_by_id(id: uuid.UUID) -> User | None:
    async with async_session_maker() as session:
        q = select(User).where(User.id == id)
        res = await session.execute(q)
        user: User | None = res.scalars().first()
        if user is None:
            return None
        return user
    
async def get_user_by_email(email: str) -> User | None:
    async with async_session_maker() as session:
        q = select(User).where(User.email == email)
        res = await session.execute(q)
        user: User | None = res.scalars().first()
        if user is None:
            return None
        return user

async def get_users(page: int, size: int) -> list[User]:
    async with async_session_maker() as session:
        q = select(User).limit(size).offset((page-1) * size)
        res = await session.scalars(q)
        return list(res.all())

async def update_user(user: User, data: UpdateUser):
    async with async_session_maker() as session:
        user.full_name = data.full_name
        if data.user_role is not None:
            user.user_role = data.user_role
        if data.is_active is not None:
            user.is_active = data.is_active
        user.age = data.age
        user.gender = data.gender
        user.region = data.region
        session.add(user)
        await session.commit()

    
