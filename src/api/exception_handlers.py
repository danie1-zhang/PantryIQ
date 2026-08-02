from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.services.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError


def register_exception_handlers(app: FastAPI) -> None:
    """Translate application errors at the HTTP boundary."""

    @app.exception_handler(ResourceNotFoundError)
    def not_found_handler(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(BusinessRuleError)
    def business_rule_handler(request: Request, exc: BusinessRuleError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})
