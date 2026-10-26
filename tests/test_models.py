from datetime import date, datetime, timezone

import pytest

from nusmods_api.models import (
    Lesson,
    Module,
    ModuleCondensed,
    SemesterData,
    VenueLesson,
    WeekRange,
    Workload,
    parse_date,
    parse_datetime,
    parse_weeks,
)


def test_parse_date_returns_date():
    assert parse_date("2025-08-11") == date(2025, 8, 11)


def test_parse_date_rejects_invalid_date():
    with pytest.raises(ValueError):
        parse_date("not-a-date")


def test_parse_datetime_preserves_time_and_timezone():
    assert parse_datetime("2025-12-01T09:30:00Z") == datetime(
        2025,
        12,
        1,
        9,
        30,
        tzinfo=timezone.utc,
    )


def test_parse_weeks_preserves_week_numbers():
    weeks = [1, 3, 5]

    assert parse_weeks(weeks) == weeks


def test_parse_weeks_converts_date_range():
    result = parse_weeks(
        {
            "start": "2025-08-11",
            "end": "2025-11-14",
            "weekInterval": 2,
            "weeks": [1, 3, 5],
        }
    )

    assert result == WeekRange(
        start=date(2025, 8, 11),
        end=date(2025, 11, 14),
        week_interval=2,
        weeks=[1, 3, 5],
    )


def test_lesson_converts_mapping_weeks_to_week_range():
    lesson = Lesson(
        classNo="1",
        startTime="10:00",
        endTime="12:00",
        weeks={
            "start": "2025-08-11",
            "end": "2025-11-14",
            "weekInterval": 1,
        },
        venue="COM1-01-01",
        day="Monday",
        lessonType="Lecture",
        size=50,
    )

    assert isinstance(lesson.weeks, WeekRange)
    assert lesson.weeks.week_interval == 1


def test_lesson_accepts_week_number_list():
    lesson = Lesson(
        classNo="1",
        startTime="10:00",
        endTime="12:00",
        weeks=[1, 2],
        venue="COM1-01-01",
        day="Monday",
        lessonType="Lecture",
        size=50,
    )

    assert lesson.weeks == [1, 2]


def test_workload_from_string():
    workload = Workload.from_string("2:Lecture")

    assert workload.string == "2:Lecture"


def test_workload_from_list_maps_components_in_order():
    workload = Workload.from_list(["2", "1", "3", "4", "5"])

    assert workload.lecture == "2"
    assert workload.tutorial == "1"
    assert workload.lab == "3"
    assert workload.project == "4"
    assert workload.preparation == "5"


def test_workload_from_list_requires_five_items():
    with pytest.raises(ValueError, match="exactly 5"):
        Workload.from_list(["2", "1"])


def test_semester_data_converts_exam_date():
    semester = SemesterData(semester=1, examDate="2025-12-01T09:30:00Z")

    assert semester.examDate == datetime(
        2025,
        12,
        1,
        9,
        30,
        tzinfo=timezone.utc,
    )


def test_models_are_frozen():
    module = ModuleCondensed(
        moduleCode="CS1010",
        title="Programming Methodology",
        semesters=[1, 2],
    )

    with pytest.raises(AttributeError):
        module.title = "Changed"


def test_module_and_venue_lesson_are_constructible():
    module = Module(
        moduleCode="CS1010",
        title="Programming Methodology",
        semesters=[1],
        acadYear="2025-2026",
    )
    lesson = VenueLesson(
        classNo="1",
        startTime="10:00",
        endTime="12:00",
        weeks=[1],
        venue="COM1-01-01",
        day="Monday",
        lessonType="Lecture",
        size=50,
        moduleCode="CS1010",
    )

    assert module.acadYear == "2025-2026"
    assert lesson.moduleCode == "CS1010"
