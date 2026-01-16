import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.models import User
from src.users.schemas import RegisterUser, User as UserSchema
import datetime
import jwt
from src.config import config


def create_token(id: uuid.UUID):
    payload = {
        "user_id": str(id),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),  # срок действия
        "iat": datetime.datetime.utcnow(),  # время выпуска
    }
    token = jwt.encode(payload, config.RANDOM_SECRET, "HS256")
    return token


def to_scheme(user: User) -> UserSchema:
    user_sc = UserSchema.model_validate(user)
    return user_sc

async def create_user(sesssion: AsyncSession, user_data: RegisterUser) -> User:
    user_dict = user_data.model_dump()
    password = user_dict.pop("password")
    user = User(**user_dict)
    user.id = uuid.uuid4()
    user.set_password(password)
    sesssion.add(user)
    await sesssion.commit()
    await sesssion.refresh(user)
    return user


async def get_user_by_id(sesssion: AsyncSession, id: uuid.UUID) -> User | None:
    q = select(User).where(User.id == id)
    res = await sesssion.execute(q)
    user: User | None = res.scalars().first()
    if user is None:
        return None
    return user
    
async def get_user_by_email(sesssion: AsyncSession, email: str) -> User | None:
    q = select(User).where(User.email == email)
    res = await sesssion.execute(q)
    user: User | None = res.scalars().first()
    if user is None:
        return None
    return user

    
