"""Built-in and explicitly supplied Python subtitle styles."""
from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import uuid4

from ..ass import StyleConfig

_BUILTINS = ("shorts", "classic", "word", "karaoke", "typewriter", "pop")


def list_styles() -> list[ModuleType]:
    """Return the built-in style modules in stable display order."""
    return [importlib.import_module(f"{__name__}.{name}") for name in _BUILTINS]


def _validate(module: ModuleType) -> ModuleType:
    required = ("NAME", "DESCRIPTION", "CONFIG", "REQUIRES_WORDS", "generate")
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise ValueError(f"style module is missing required attributes: {', '.join(missing)}")
    if not isinstance(module.NAME, str) or not module.NAME.strip():
        raise ValueError("style NAME must be a non-empty string")
    if not isinstance(module.DESCRIPTION, str):
        raise ValueError("style DESCRIPTION must be a string")
    if not isinstance(module.CONFIG, StyleConfig):
        raise ValueError("style CONFIG must be a StyleConfig instance")
    if not isinstance(module.REQUIRES_WORDS, bool) or not callable(module.generate):
        raise ValueError("style REQUIRES_WORDS must be bool and generate must be callable")
    return module


def load_style(name_or_path: str | Path) -> ModuleType:
    """Load a built-in by name or execute a caller-supplied trusted Python file.

    A path is only loaded when explicitly passed. Python style files execute code
    during import and therefore must come from a trusted source.
    """
    value = str(name_or_path)
    if value in _BUILTINS:
        return _validate(importlib.import_module(f"{__name__}.{value}"))
    path = Path(value).expanduser()
    if not path.is_file() or path.suffix.lower() != ".py":
        raise ValueError(f"unknown built-in style or Python style file: {value}")
    module_name = f"subtitle_forge_external_style_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"could not load style file: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return _validate(module)


__all__ = ["list_styles", "load_style"]
