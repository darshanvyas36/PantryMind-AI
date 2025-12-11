# app/utils/exceptions.py
class OCRServiceError(Exception):
    def __init__(self, error_code: str, message: str, debug_info: str = None):
        self.error_code = error_code
        self.message = message
        self.debug_info = debug_info
        super().__init__(message)

class LLMError(OCRServiceError):
    pass

class OCRError(OCRServiceError):
    pass

class ValidationError(OCRServiceError):
    pass

class ImageProcessingError(OCRServiceError):
    pass
