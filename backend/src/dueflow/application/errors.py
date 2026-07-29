class ApplicationError(Exception):
    status_code = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ResourceNotFoundError(ApplicationError):
    status_code = 404


class InvalidStateError(ApplicationError):
    status_code = 409

