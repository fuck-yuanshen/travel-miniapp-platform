class ApiError(Exception):
    def __init__(self, message, code=4000, status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
