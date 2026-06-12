from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from starlette.applications import Starlette
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route


class HTTPException(StarletteHTTPException):
    def __init__(self, status_code: int, detail: str = "") -> None:
        super().__init__(status_code=status_code, detail=detail)


class status:
    HTTP_200_OK = 200
    HTTP_201_CREATED = 201
    HTTP_202_ACCEPTED = 202
    HTTP_204_NO_CONTENT = 204
    HTTP_302_FOUND = 302
    HTTP_400_BAD_REQUEST = 400
    HTTP_401_UNAUTHORIZED = 401
    HTTP_403_FORBIDDEN = 403
    HTTP_404_NOT_FOUND = 404
    HTTP_409_CONFLICT = 409
    HTTP_422_UNPROCESSABLE_ENTITY = 422
    HTTP_500_INTERNAL_SERVER_ERROR = 500


def File(default: Any = None, **_: Any) -> Any:
    return default


def Form(default: Any = None, **_: Any) -> Any:
    return default


def Depends(dependency: Callable[..., Any]) -> Callable[..., Any]:
    return dependency


class APIRouter:
    def __init__(self, prefix: str = "", tags: list[str] | None = None) -> None:
        self.prefix = prefix.rstrip("/")
        self.tags = tags or []
        self.routes: list[Route] = []

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        methods: Iterable[str] | None = None,
        name: str | None = None,
        **_: Any,
    ) -> Callable[..., Any]:
        normalized = path if path.startswith("/") else f"/{path}"
        full_path = f"{self.prefix}{normalized}" if self.prefix else normalized
        self.routes.append(Route(full_path, endpoint, methods=list(methods or ["GET"]), name=name))
        return endpoint

    def api_route(self, path: str, methods: Iterable[str] | None = None, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(path, endpoint, methods=methods, **kwargs)
            return endpoint

        return decorator

    def get(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.api_route(path, methods=["GET"], **kwargs)

    def post(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.api_route(path, methods=["POST"], **kwargs)

    def put(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.api_route(path, methods=["PUT"], **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.api_route(path, methods=["PATCH"], **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.api_route(path, methods=["DELETE"], **kwargs)


class FastAPI(Starlette):
    def __init__(self, *args: Any, title: str = "FastAPI", **kwargs: Any) -> None:
        routes = kwargs.pop("routes", None)
        super().__init__(*args, routes=routes or [], **kwargs)
        self.title = title

    def include_router(self, router: APIRouter) -> None:
        self.routes.extend(router.routes)

    def on_event(self, event_type: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_event_handler(event_type, func)
            return func

        return decorator

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        methods: Iterable[str] | None = None,
        name: str | None = None,
        **_: Any,
    ) -> Callable[..., Any]:
        normalized = path if path.startswith("/") else f"/{path}"
        self.routes.append(Route(normalized, endpoint, methods=list(methods or ["GET"]), name=name))
        return endpoint

    def api_route(self, path: str, methods: Iterable[str] | None = None, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(path, endpoint, methods=methods, **kwargs)
            return endpoint

        return decorator

    def get(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.api_route(path, methods=["GET"], **kwargs)

    def post(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.api_route(path, methods=["POST"], **kwargs)

    def put(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.api_route(path, methods=["PUT"], **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.api_route(path, methods=["PATCH"], **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.api_route(path, methods=["DELETE"], **kwargs)


__all__ = [
    "APIRouter",
    "Depends",
    "FastAPI",
    "File",
    "Form",
    "HTTPException",
    "Request",
    "UploadFile",
    "Response",
    "status",
]
