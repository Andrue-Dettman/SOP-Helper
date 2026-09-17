"""Run: uvicorn app.main:app --app-dir backend --port 8101.

Integration injects C1/G2's Services implementation through create_app. Missing
services or provider settings remain visibly unavailable; no fixture fallback.
"""
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.routes import router
from app.assistant.engine import Assistant, Limits
from app.contracts.models import ChatResponse, Error, ValidationErrorResponse
from app.contracts.services import DependencyFailure, UnavailableServices
from app.providers.openai import OpenAIChatProvider


def create_app(*, services=None, provider=None, limits=Limits()) -> FastAPI:
    app = FastAPI(title="Fictional Warehouse Assistant", version="1.0.0")
    app.state.services = services if services is not None else UnavailableServices()
    provider = provider if provider is not None else OpenAIChatProvider(
        os.environ.get("OPENAI_API_KEY", ""), os.environ.get("OPENAI_CHAT_MODEL", ""))
    app.state.assistant = Assistant(app.state.services, provider, limits=limits)
    app.include_router(router)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        # Never echo invalid request contents, URLs with credentials, or Pydantic ctx.
        response = ValidationErrorResponse(error=Error(code="invalid_request", message="The request does not match the API schema.", retryable=False))
        return JSONResponse(response.model_dump(mode="json"), status_code=422)

    async def failure(code, status, retryable=False):
        response = ChatResponse(answer="The requested operation could not be completed.",
                                status="temporarily_unavailable", error=Error(
                                    code=code, message="A required service is unavailable.", retryable=retryable))
        return JSONResponse(response.model_dump(mode="json"), status_code=status)

    @app.exception_handler(DependencyFailure)
    async def dependency_failure(request: Request, exc: DependencyFailure):
        return await failure(exc.code, 503, exc.retryable)

    @app.exception_handler(TimeoutError)
    async def timeout(request: Request, exc: TimeoutError):
        return await failure("request_timeout", 504, True)

    @app.exception_handler(ValidationError)
    async def invalid_dependency(request: Request, exc: ValidationError):
        return await failure("invalid_dependency_response", 503)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        return await failure("internal_error", 500)

    return app


app = create_app()
