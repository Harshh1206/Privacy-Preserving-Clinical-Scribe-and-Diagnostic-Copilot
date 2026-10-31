from __future__ import annotations

from fastapi import HTTPException, status


class AppError(HTTPException):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)


def not_found(entity: str, ident: str) -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, f"{entity} {ident} not found")


def conflict(detail: str) -> AppError:
    return AppError(status.HTTP_409_CONFLICT, detail)


def bad_request(detail: str) -> AppError:
    return AppError(status.HTTP_400_BAD_REQUEST, detail)
