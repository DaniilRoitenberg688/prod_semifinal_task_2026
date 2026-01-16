import uuid
from pydantic import BaseModel, Field, ConfigDict, field_validator, EmailStr
from pydantic.aliases import AliasChoices
from src.users.models import Gender, MaritalStatus, UserRole
import datetime
import regex


class BaseUser(BaseModel):
    email: EmailStr = Field(max_length=254)
    full_name: str = Field(min_length=2, max_length=200, alias="fullName", validation_alias=AliasChoices("full_name", "fullName"), )
    region: str | None
    gender: Gender | None
    age: int | None = Field(ge=18, le=120)
    marital_status: MaritalStatus | None = Field(validation_alias=AliasChoices("maritalStatus", "marital_status"), alias="maritalStatus")
    user_role: UserRole = Field(default=UserRole.user, validation_alias=AliasChoices("userRole", "isActive"), alias="isActive")
    model_config = ConfigDict(from_attributes=True)

class User(BaseUser):
    id: uuid.UUID
    is_active: bool = Field(validation_alias=AliasChoices("isActive", "is_active"), alias="isActive")
    created_at: datetime.datetime = Field(validation_alias=AliasChoices("created_at"), alias="createdAt")
    updated_at: datetime.datetime = Field(validation_alias=AliasChoices("updated_at"), alias="updatedAt")

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
    token: str
    user: User
