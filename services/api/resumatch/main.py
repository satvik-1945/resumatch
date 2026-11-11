from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from resumatch.auth import router as auth_router
from resumatch.briefs import router as brief_router
from resumatch.config import get_settings
from resumatch.routes import router
from resumatch.workflows import router as workflow_router

get_settings()
app = FastAPI(title="Outreach sessions", version="0.2.0")
# Extension credentials are separately bound to the exact extension Origin on the server.
app.add_middleware(CORSMiddleware, allow_origin_regex=r"chrome-extension://[a-p]{32}",
                   allow_methods=["GET", "POST"],
                   allow_headers=["Authorization", "Content-Type", "X-Extension-ID"])
app.include_router(auth_router)
app.include_router(router)
app.include_router(workflow_router)
app.include_router(brief_router)


@app.middleware("http")
async def private_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    return JSONResponse(status_code=503, content={
        "detail": "Database unavailable; check container health and run migrations"
    })
