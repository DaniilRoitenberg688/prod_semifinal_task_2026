from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base
import uuid
from enum import Enum
import datetime
from werkzeug.security import check_password_hash, generate_password_hash


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
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    full_name: Mapped[str] = mapped_column(nullable=False)
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
    
    def set_password(self, p: str):
        self.hashed_password = generate_password_hash(p)

    def check_password(self, p: str) -> bool:
        return check_password_hash(self.hashed_password, p)

