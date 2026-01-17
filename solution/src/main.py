from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer

from src.config import config
from src.exceptions import ApiError, ErrorCode
from src.exceptions import ValidationError as CustomValidationError
from src.users.routes import auth_router, user_router
from src.users.schemas import CreateUser, RegisterUser
from src.users.repository import create_user, get_user_by_email
from src.database import async_session_maker
from src.users.models import UserRole


@asynccontextmanager
async def init(app: FastAPI) -> AsyncGenerator[None, None]:
    user = await get_user_by_email(str(config.ADMIN_EMAIL))
    if user is None:
        user_data = {}
        user_data["email"] = config.ADMIN_EMAIL
        user_data["fullName"] = config.ADMIN_FULLNAME
        user_data["password"] = config.ADMIN_PASSWORD
        user_data["userRole"] = UserRole.admin
        user = await create_user(CreateUser(**user_data))
        print(user.user_role)

    yield


app = FastAPI(lifespan=init)



@app.exception_handler(RequestValidationError)
async def validation_error(r: Request, e: ResponseValidationError):
    fields = []
    for i in e.errors():
        if i["type"] in ["json_invalid", "model_attributes_type"]:
            err = ApiError(
                status_code=400,
                err_code=ErrorCode.bad_request,
                message="invalid json",
            )
            errd = err.__dict__
            errd.pop("status_code")
            errd["path"] = r.url.path
            return JSONResponse(content=errd, status_code=400)

        fields.append(
            {
                "field": i["loc"][1],
                "issue": i["msg"],
                "rejected_value": None
                if i["loc"][1] == "password" or i["loc"][1] == "hashed_password"
                else i["input"],
            }
        )
    err = CustomValidationError(
        status_code=422,
        err_code=ErrorCode.validation_failed,
        message="cannot validate data",
        field_errors=fields,
    )
    errd = err.__dict__
    errd.pop("status_code")
    errd["path"] = r.url.path
    errd["fieldErrors"] = errd.pop("field_errors")
    errd["code"] = errd.pop("err_code")
    return JSONResponse(content=errd, status_code=422)


# @app.exception_handler(ValueError)
# async def value_error(r: Request, e: ValueError):
#     print("sjifghehdg")
#     err = e.__dict__
#     fields = [
#         {"field": err["loc"][1], "issue": err["msg"], "rejected_value": err["input"]}
#     ]
#     err = CustomValidationError(
#         status_code=422,
#         err_code=ErrorCode.validation_failed,
#         message="cannot validate data",
#         field_errors=fields,
#     )
#     errd = err.__dict__
#     errd["path"] = r.url.path
#     errd["fieldErrors"] = errd.pop("field_errors")
#     return JSONResponse(content=errd, status_code=422)


@app.exception_handler(ApiError)
async def handle_api_error(r: Request, e: ApiError):
    err = e.__dict__
    sc = err.pop("status_code")
    err["path"] = r.url.path
    err["code"] = err.pop("err_code")
    return JSONResponse(status_code=sc, content=err)


@app.get("/api/v1/ping", tags=["Auth"])
def ping():
    return {"status": "ok"}


app.include_router(auth_router, tags=["Auth"])
app.include_router(user_router, tags=["Users"])
