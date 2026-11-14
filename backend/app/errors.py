class ApiError(Exception):
    def __init__(self, status: int, message: str, fields: dict | None = None):
        self.status, self.message, self.fields = status, message, fields
