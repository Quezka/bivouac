"""The enums the UI needs, re-exported so it never imports the domain."""
from ..domain.model import CardKind  # noqa: F401
from ..domain.srs import Grade  # noqa: F401

# Practice scopes: every card, the glossary only, or one chapter ("ch:<id>").
SCOPE_ALL = "all"
SCOPE_GLOSSARY = "glossary"
SCOPE_CHAPTER = "ch:"
