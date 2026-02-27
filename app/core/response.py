from typing import Any

from pydantic import BaseModel


class Meta(BaseModel):
    page: int = 1
    total: int = 0


class ApiResponse[T](BaseModel):
    data: T | None = None
    error: str | None = None
    meta: Meta | None = None


def ok(data: Any, page: int = 1, total: int | None = None) -> dict:
    resp: dict[str, Any] = {"data": data, "error": None}
    if total is not None:
        resp["meta"] = {"page": page, "total": total}
    else:
        resp["meta"] = None
    return resp


def err(message: str, status_code: int = 400) -> dict:
    return {"data": None, "error": message, "meta": None}
