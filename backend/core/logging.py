import logging
from fastapi import FastAPI, Request


def setup_logging() -> None:
    """Configure root logger; call once on startup."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def add_logging_middleware(app: FastAPI) -> None:
    """Attach request/response logging to the FastAPI app."""
    setup_logging()
    logger = logging.getLogger("backend")

    @app.middleware("http")
    async def _log_requests(request: Request, call_next):  # type: ignore[override]
        logger.info("%s %s", request.method, request.url.path)
        response = await call_next(request)
        logger.info("Completed %s", response.status_code)
        return response
