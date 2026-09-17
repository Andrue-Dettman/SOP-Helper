import asyncio

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.assistant.evidence import source_uri
from app.contracts.models import (
    AssembliesResponse, ChatRequest, ChatResponse, Error, HealthResponse, ReadyResponse,
    SourceSection, ValidationErrorResponse,
)
from app.contracts.services import DependencyFailure

router = APIRouter(prefix="/api")
ERROR_RESPONSES = {code: {"model": ChatResponse} for code in (500, 503, 504)}
ERROR_RESPONSES[422] = {"model": ValidationErrorResponse}


@router.post("/chat", response_model=ChatResponse, responses=ERROR_RESPONSES)
async def chat(payload: ChatRequest, request: Request):
    response, status = await request.app.state.assistant.run(payload)
    return JSONResponse(response.model_dump(mode="json"), status_code=status)


@router.get("/sops/{document_id}/sections/{section_id}", response_model=SourceSection,
            responses={**ERROR_RESPONSES, 404: {"model": ValidationErrorResponse}})
async def section(document_id: str, section_id: str, request: Request,
                  version: str = Query(min_length=1, max_length=200)):
    async with asyncio.timeout(10):
        result = await request.app.state.services.section(document_id, version, section_id)
    if result is None:
        body = ValidationErrorResponse(error=Error(code="source_not_found", message="That exact source version was not found.", retryable=False))
        return JSONResponse(body.model_dump(mode="json"), status_code=404)
    result = SourceSection.model_validate(result)
    if (result.document_id, result.version, result.section_id) != (document_id, version, section_id):
        raise DependencyFailure("invalid_dependency_response")
    return result.model_copy(update={"source_uri": source_uri(document_id, version, section_id)})


@router.get("/assemblies", response_model=AssembliesResponse, responses=ERROR_RESPONSES)
async def assemblies(request: Request, query: str = Query(default="", max_length=1000),
                     limit: int = Query(default=20, ge=1, le=20)):
    async with asyncio.timeout(10):
        items = await request.app.state.services.assemblies(query.strip(), limit)
    result = AssembliesResponse(items=items)
    if len(result.items) > limit:
        raise DependencyFailure("invalid_dependency_response")
    return result


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@router.get("/ready", response_model=ReadyResponse, responses={503: {"model": ReadyResponse}})
async def ready(request: Request):
    try:
        async with asyncio.timeout(10):
            database, corpus = await request.app.state.services.readiness()
    except Exception:
        database, corpus = False, False
    configured = request.app.state.assistant.provider.configured
    result = ReadyResponse(status="ready" if database and corpus and configured else "not_ready",
                           database="ready" if database else "unavailable",
                           corpus="ready" if corpus else "missing",
                           provider="configured" if configured else "missing")
    return JSONResponse(result.model_dump(), status_code=200 if result.status == "ready" else 503)
