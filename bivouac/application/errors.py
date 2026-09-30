"""Errors the use cases raise. Their messages are shown to the user."""


class ApplicationError(Exception):
    """Something the user can understand and act on."""


class NotFound(ApplicationError):
    pass


class FileFormatError(ApplicationError):
    """The file isn't a study pack or a manual Bivouac can read."""


class FileAccessError(ApplicationError):
    """The file couldn't be read or written."""


class InvalidInput(ApplicationError):
    pass


class UpdateError(ApplicationError):
    """Checking for, downloading or installing a new version didn't work."""
