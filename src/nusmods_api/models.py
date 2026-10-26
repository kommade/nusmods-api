"""Typed models for responses from the NUSMods v2 API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, TypeAlias


@dataclass(frozen=True)
class WeekRange:
    """A date-based lesson range used for special classes."""

    start: date
    end: date
    weeks: list[int] | None = None
    week_interval: int | None = None


LessonWeeks: TypeAlias = list[int] | WeekRange


@dataclass(frozen=True)
class Lesson:
    class_no: str
    lesson_type: str
    weeks: LessonWeeks
    day: str
    start_time: str
    end_time: str
    venue: str | None = None


@dataclass(frozen=True)
class Workload:
    """Estimated weekly workload, in API order."""

    lecture: float | None = None
    tutorial: float | None = None
    laboratory: float | None = None
    project: float | None = None
    preparation: float | None = None
    raw: str | None = None


@dataclass(frozen=True)
class PrerequisiteTree:
    """Recursive prerequisite expression.

    A node normally contains either ``and`` or ``or``. Leaf values are
    module codes represented as strings.
    """

    and_: list[str | PrerequisiteTree] | None = None
    or_: list[str | PrerequisiteTree] | None = None


@dataclass(frozen=True)
class ModuleCondensed:
    module_code: str
    title: str
    description: str | None = None
    module_credit: float | None = None
    department: str | None = None
    faculty: str | None = None


@dataclass(frozen=True)
class Module(ModuleCondensed):
    prerequisite: str | None = None
    corequisite: str | None = None
    preclusion: str | None = None
    prerequisite_tree: PrerequisiteTree | None = None
    fulfill_requirements: list[str] | None = None
    workload: Workload | None = None
    timetable: list[Lesson] | None = None
    attributes: list[str] | None = None
    aliases: list[str] | None = None


@dataclass(frozen=True)
class VenueLesson(Lesson):
    module_code: str = ""


@dataclass(frozen=True)
class VenueInformation:
    venue: str
    classes: list[VenueLesson]


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def parse_weeks(value: list[int] | dict[str, Any]) -> LessonWeeks:
    if isinstance(value, list):
        return value

    return WeekRange(
        start=parse_date(value["start"]),
        end=parse_date(value["end"]),
        weeks=value.get("weeks"),
        week_interval=value.get("weekInterval"),
    )
