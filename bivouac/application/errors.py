"""Errors the use cases raise. Their messages are shown to the user."""


class ApplicationError(Exception):
    """Something the user can understand and act on.

    The message is English text with named placeholders, and the values go in as keywords:
    `NotFound("There's no chapter {id}.", id=chapter_id)`. The UI translates `template`
    and fills it in with `values`; `str(error)` is the English sentence."""

    def __init__(self, message: str, **values):
        super().__init__(message.format(**values) if values else message)
        self.template = message
        self.values = values


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
