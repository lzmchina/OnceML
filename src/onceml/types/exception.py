class PipelineNotFoundError(Exception):
    pass


class ComponentNotFoundError(Exception):
    pass


class DeployTypeError(Exception):
    pass


class DBOpTypeError(Exception):
    pass


class FileNotFoundError(Exception):
    pass


class NFCNotFoundError(Exception):
    pass
class TypeNotAllowedError(Exception):
    pass
class SendChannelError(Exception):
    pass

class CustomError(Exception):
    def __init__(self, message, error_code=408):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

    def __str__(self):
        return "{message} : {error_code}".format(message=self.message, error_code=self.error_code)