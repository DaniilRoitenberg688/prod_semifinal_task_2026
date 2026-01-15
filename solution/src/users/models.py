from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base
import uuid
from enum import Enum
import datetime


class Gender(Enum):
    male = "MALE"
    female = "FEMALE"


class MaritalStatus(Enum):
    single = "SINGLE"
    married = "MARRIED"
    divorced = "DIVORCED"
    widowed = "WIDOWED"


class UserRole(Enum):
    admin = "ADMIN"
    user = "USER"


class User(Base):
    __tablename__="users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    fullname: Mapped[str] = mapped_column(unique=True, nullable=False)
    region: Mapped[str] = mapped_column()
    gender: Mapped[Gender]
    marital_status: Mapped[MaritalStatus]
    age: Mapped[int]
    user_role: Mapped[UserRole] = mapped_column(default=UserRole.user, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, default=datetime.datetime.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        default=datetime.datetime.now(),
        onupdate=datetime.datetime.now(),
    )
