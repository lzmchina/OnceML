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