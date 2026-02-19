from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception."""

    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        success: bool = False,
        error: str = "An error occurred",
    ):
        self.status_code = status_code
        self.detail = {"success": success, "error": error}
        super().__init__(status_code=status_code, detail=self.detail)


class UnauthorizedException(AppException):
    """Unauthorized access exception."""

    def __init__(self, error: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, error=error)


class ForbiddenException(AppException):
    """Forbidden access exception."""

    def __init__(self, error: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, error=error)


class NotFoundException(AppException):
    """Resource not found exception."""

    def __init__(self, error: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, error=error)


class BadRequestException(AppException):
    """Bad request exception."""

    def __init__(self, error: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, error=error)
