import uuid
from pydantic import BaseModel, Field, ConfigDict, field_validator, EmailStr
from pydantic.aliases import AliasChoices
from src.users.models import Gender, MaritalStatus, UserRole
import datetime
import regex


class BaseUser(BaseModel):
    email: EmailStr = Field(max_length=254)
    full_name: str = Field(min_length=2, max_length=200, alias="fullName", validation_alias=AliasChoices("full_name", "fullName"), )
    region: str | None = None
    gender: Gender | None = None
    age: int | None = Field(default=18, ge=18, le=120)
    marital_status: MaritalStatus | None = Field(default=None, validation_alias=AliasChoices("maritalStatus", "marital_status"), alias="maritalStatus")
    model_config = ConfigDict(from_attributes=True)

class UserScheme(BaseUser):
    id: uuid.UUID
    is_active: bool = Field(validation_alias=AliasChoices("isActive", "is_active"), alias="isActive")
    user_role: UserRole = Field(default=UserRole.user, validation_alias=AliasChoices("userRole", "userRole"), alias="userRole")
    created_at: datetime.datetime = Field(validation_alias=AliasChoices("created_at"), alias="createdAt")
    updated_at: datetime.datetime = Field(validation_alias=AliasChoices("updated_at"), alias="updatedAt")


class PagedUsers(BaseModel):
    users: list[UserScheme]
    total: int
    page: int
    size: int

class RegisterUser(BaseUser):
    password: str = Field(min_length=8, max_length=72)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        pattern = r'^(?=.*[A-Za-z])(?=.*\d).+$'
        
        if not regex.match(pattern, v):
            raise ValueError(
                "Пароль должен содержать минимум одну букву и одну цифру"
            )
        
        return v

class CreateUser(BaseUser):
    hashed_password: str


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    token: str = Field(validation_alias=AliasChoices("token", "accessToken"), alias="accessToken")
    user: UserScheme

class UserOutWithExp(UserOut):
    exps: int = Field(alias="expiresIn", default=3600, validation_alias=AliasChoices("exp", "expiresIn"))
