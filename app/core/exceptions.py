from typing import Any

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base domain exception — always produces the standard API error envelope."""

    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        message: str = "An error occurred",
        detail: Any | None = None,
    ):
        super().__init__(
            status_code=status_code,
            detail={"success": False, "message": message, "error": detail or message},
        )


class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request", detail: Any | None = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            detail=detail,
        )


class NotFoundException(AppException):
    def __init__(self, resource: str = "Resource", id_val: Any | None = None):
        msg = f"{resource} not found" if id_val is None else f"{resource} with ID '{id_val}' not found"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, message=msg)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Invalid authentication credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
        )


class ForbiddenException(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
        )


class ConflictException(AppException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            message=message,
        )
