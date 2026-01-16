from datetime import datetime
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import fastapi
from pydantic import ValidationError

from src.exceptions import ApiError, ErrorCode, FieldError
from src.exceptions import ValidationError as CustomValidationError
from src.users.routes import auth_router




app = FastAPI()


@app.exception_handler(ValidationError)
async def validation_error(r: Request, e: ValidationError):
    print(e.errors())
    fields = [{"field": i["loc"][0], "issue": i["msg"], "rejected_value": None} for i in e.errors()]
    err = CustomValidationError(
        status_code=422,
        err_code=ErrorCode.validation_failed,
        message="cannot validate data",
        field_errors=fields
    )
    errd = err.__dict__
    errd["path"]=r.url.path
    errd["fieldErrors"] = errd.pop("field_errors")
    return JSONResponse(content=errd, status_code=422)

@app.exception_handler(ApiError)
async def handle_api_error(r: Request, e: ApiError):
    err = e.__dict__
    sc = err.pop("status_code")
    err["path"] = r.url.path
    return JSONResponse(
        status_code=sc,
        content=err
    )



@app.get("/api/v1/ping", tags=["Auth"])
def ping():
    return {
        "status": "ok"
    }

app.include_router(auth_router, tags=["Auth"])
