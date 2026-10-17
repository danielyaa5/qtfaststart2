class FastStartException(Exception):
    """
    Raised when something bad happens during processing.
    """
    pass

class FastStartSetupError(FastStartException):
    """
    Raised when processing can't be set up, for example when the input
    and output are the same file
    """
    pass

class MalformedFileError(FastStartException):
    """
    Raised when the input file is setup in an unexpected way
    """
    pass

class UnsupportedFormatError(FastStartException):
    """
    Raised when a movie file is recognized as a format not supported.
    """
    pass
