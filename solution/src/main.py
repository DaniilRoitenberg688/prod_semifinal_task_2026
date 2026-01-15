from fastapi import FastAPI


app = FastAPI()

@app.get("/api/v1/ping", tags=["Auth"])
def ping():
    return {
        "status": "ok"
    }
