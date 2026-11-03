"""
The MQTT course. Each lesson is a module named NN_topic.py with a matching
NN_topic.md explanation. A lesson module has:

    TITLE   one line shown in the index
    run()   run(settings) -> result; prints what happens and returns what it
            observed, so tests/ can check the same run with assertions
"""
from __future__ import annotations

import importlib
import pkgutil
import re
from dataclasses import dataclass
from types import ModuleType
from typing import Any

_LESSON_MODULE = re.compile(r"^(\d\d)_\w+$")


@dataclass(frozen=True)
class LessonModule:
    number: int
    module_name: str
    module: ModuleType

    @property
    def title(self) -> str:
        return self.module.TITLE

    def run(self, settings: Any) -> Any:
        return self.module.run(settings)


def discover() -> list[LessonModule]:
    """All lessons in this package, in order."""
    found = []
    for info in pkgutil.iter_modules(__path__):
        match = _LESSON_MODULE.match(info.name)
        if match:
            module = importlib.import_module(f"{__name__}.{info.name}")
            found.append(LessonModule(int(match.group(1)), info.name, module))
    return sorted(found, key=lambda lesson: lesson.number)


def load(number: int) -> LessonModule:
    """One lesson by number, e.g. load(3)."""
    for lesson in discover():
        if lesson.number == number:
            return lesson
    raise LookupError(f"no lesson {number}")
