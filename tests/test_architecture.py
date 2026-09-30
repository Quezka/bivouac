"""Enforce the dependency rule: source code dependencies only point inwards."""
import ast
import dataclasses
import enum
import inspect
import typing
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parent.parent / "bivouac"

FORBIDDEN = {
    "domain": ["bivouac.application", "bivouac.infrastructure", "bivouac.presentation",
               "bivouac.bootstrap", "PySide6", "sqlite3", "subprocess"],
    "application": ["bivouac.infrastructure", "bivouac.presentation", "bivouac.bootstrap",
                    "PySide6", "sqlite3", "subprocess"],
    "infrastructure": ["bivouac.presentation", "bivouac.bootstrap", "PySide6"],
    # The UI talks to use cases only; enums come through bivouac.application.types.
    "presentation": ["bivouac.domain", "bivouac.infrastructure", "bivouac.bootstrap", "sqlite3"],
}


def imports_of(path: Path) -> set[str]:
    parts = path.relative_to(PACKAGE.parent).with_suffix("").parts
    package = ".".join(parts[:-1])
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[: len(base) - node.level + 1]
                name = ".".join(base + ([node.module] if node.module else []))
            else:
                name = node.module
            found.add(name)
    return found


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_respects_dependency_rule(layer):
    violations = []
    for path in sorted((PACKAGE / layer).rglob("*.py")):
        for imported in imports_of(path):
            for banned in FORBIDDEN[layer]:
                if imported == banned or imported.startswith(banned + "."):
                    violations.append(f"{path.relative_to(PACKAGE)} imports {imported}")
    assert not violations, "\n".join(violations)


def domain_types_in(hint) -> set[str]:
    found = set()
    if inspect.isclass(hint):
        if hint.__module__.startswith("bivouac.domain") and not issubclass(hint, enum.Enum):
            found.add(hint.__qualname__)
        return found
    for arg in typing.get_args(hint):
        found |= domain_types_in(arg)
    return found


def test_use_cases_neither_take_nor_return_domain_entities():
    from bivouac.application.library import LibraryService
    from bivouac.application.study import StudyService
    leaks = []
    for cls in (LibraryService, StudyService):
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            if name.startswith("_"):
                continue
            for arg, hint in typing.get_type_hints(method).items():
                for leaked in domain_types_in(hint):
                    leaks.append(f"{cls.__name__}.{name} {arg}: {leaked}")
    assert not leaks, "\n".join(leaks)


def test_response_models_hold_no_domain_entities():
    from bivouac.application import inputs, records
    leaks = []
    for module in (inputs, records):
        for name, cls in inspect.getmembers(module, dataclasses.is_dataclass):
            if cls.__module__ != module.__name__:
                continue
            for field, hint in typing.get_type_hints(cls).items():
                for leaked in domain_types_in(hint):
                    leaks.append(f"{module.__name__}.{name}.{field}: {leaked}")
    assert not leaks, "\n".join(leaks)
