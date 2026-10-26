"""Typed models for responses from the NUSMods v2 API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, TypeAlias


@dataclass(frozen=True)
class WeekRange:
    """A date-based lesson range used for special classes."""

    start: date
    end: date
    week_interval: int | None = None
    weeks: list[int] | None = None


LessonWeeks: TypeAlias = list[int] | WeekRange


@dataclass(frozen=True)
class Lesson:
    classNo: str
    startTime: str
    endTime: str
    weeks: LessonWeeks
    venue: str
    day: str
    lessonType: str
    size: int

    def __post_init__(self) -> None:
        if not isinstance(self.weeks, (list, WeekRange)):
            object.__setattr__(self, "weeks", parse_weeks(self.weeks))

@dataclass(frozen=True)
class LessonWithModule(Lesson):
    moduleCode: str

@dataclass(frozen=True)
class Workload:
    """Workload for a module.

    The workload is represented as a list of strings, where each string
    represents a workload component in the format ``<hours>:<component>``.
    For example, ``"2:Lecture"`` means 2 hours of lecture per week.
    """

    lecture: int | None = None
    tutorial: int | None = None
    lab: int | None = None
    project: int | None = None
    preparation: int | None = None
    string: str | None = None
    
    @staticmethod
    def from_string(workload_str: str) -> Workload:
        return Workload(string=workload_str)
    
    @staticmethod
    def from_list(workload_list: list[str]) -> Workload:
        if len(workload_list) != 5:
            raise ValueError("Workload list must have exactly 5 elements.")
        order = ["lecture", "tutorial", "lab", "project", "preparation"]
        d = {}
        for i in range(5):
            d[order[i]] = workload_list[i]
        return Workload(**d)


@dataclass(frozen=True)
class PrerequisiteTree:
    """Recursive prerequisite expression.

    A node normally contains either ``and`` or ``or``. Leaf values are
    module codes represented as strings.
    """

    and_: list[str | PrerequisiteTree] | None = None
    or_: list[str | PrerequisiteTree] | None = None



@dataclass(frozen=True)
class SemesterData:
    """Semester data for a module."""

    semester: int
    examDate: date | None = None
    examDuration: int | None = None
    timetable: list[Lesson] | None = None
    
    def __post_init__(self) -> None:
        if self.examDate is not None and not isinstance(self.examDate, date):
            object.__setattr__(self, "examDate", parse_date(self.examDate))

@dataclass(frozen=True)
class ModuleCondensed:
    moduleCode: str
    title: str
    semesters: list[int]


@dataclass(frozen=True)
class Module(ModuleCondensed):
    acadYear: str
    preclusion: str | None = None
    description: str | None = None
    department: str | None = None
    faculty: str | None = None
    workload: Workload | None = None
    moduleCredit: int | None = None
    attributes: dict[str, Any] | None = None
    semesterData: list[SemesterData] | None = None
    prerequisite: str | None = None
    fulfill_requirements: list[str] | None = None
    corequisite: str | None = None
    prerequisite_tree: PrerequisiteTree | None = None


@dataclass(frozen=True)
class VenueLesson(Lesson):
    moduleCode: str = ""


@dataclass(frozen=True)
class VenueInformation:
    """Information about a venue and its lessons."""

    day: str
    classes: list[VenueLesson]
    availability: dict[str, str] | None = None

@dataclass(frozen=True)
class ExamTimetable:
    """Exam timetable for a module."""

    moduleCode: str
    examDate: date | None = None
    examDuration: int | None = None

@dataclass(frozen=True)
class Timetable:
    """Timetable for a semester."""
    semester: int
    weekly: list[LessonWithModule]
    exams: list[ExamTimetable]
    
    def get_day_schedule(self, day: str) -> list[Lesson]:
        """Get the lessons for a specific day of the week."""
        if day not in {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}:
            raise ValueError("Day must be one of Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday")
        return [lesson for lesson in self.weekly if lesson.day == day]
    
    def get_exam_for_module(self, module_code: str) -> ExamTimetable | None:
        """Get the exam timetable for a specific module."""
        for exam in self.exams:
            if exam.moduleCode == module_code:
                return exam
        return None

def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def parse_weeks(value: list[int] | dict[str, Any]) -> LessonWeeks:
    if isinstance(value, list):
        return value

    return WeekRange(
        start=parse_date(value["start"]),
        end=parse_date(value["end"]),
        weeks=value.get("weeks"),
        week_interval=value.get("weekInterval"),
    )
