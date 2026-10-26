from datetime import date

import pytest

from nusmods_api import NUSModsClient


SHARED_TIMETABLE_URL = (
    "https://nusmods.com/timetable/sem-1/share?"
    "CS1231S=TUT:25B,LEC:1&"
    "CS2030S=REC:04,LAB:10B,LEC:1&"
    "GES1034=LEC:1,TUT:E2&"
    "IS1108=TUT:14,LEC:2&"
    "MA1522=LEC:1"
)


@pytest.mark.live
def test_get_shared_timetable_against_live_nusmods_api():
    client = NUSModsClient(timeout=20)

    timetable = client.get_shared_timetable(SHARED_TIMETABLE_URL)

    assert timetable.semester == 1
    assert len(timetable.weekly) == 12
    assert {lesson.moduleCode for lesson in timetable.weekly} == {
        "CS1231S",
        "CS2030S",
        "GES1034",
        "IS1108",
        "MA1522",
    }
    assert {
        (lesson.moduleCode, lesson.lessonType, lesson.classNo)
        for lesson in timetable.weekly
    } == {
        ("CS1231S", "Tutorial", "25B"),
        ("CS1231S", "Lecture", "1"),
        ("CS2030S", "Recitation", "04"),
        ("CS2030S", "Laboratory", "10B"),
        ("CS2030S", "Lecture", "1"),
        ("GES1034", "Lecture", "1"),
        ("GES1034", "Tutorial", "E2"),
        ("IS1108", "Tutorial", "14"),
        ("IS1108", "Lecture", "2"),
        ("MA1522", "Lecture", "1"),
    }
    assert sum(
        lesson.moduleCode == "CS1231S" and lesson.lessonType == "Lecture"
        for lesson in timetable.weekly
    ) == 2
    assert sum(
        lesson.moduleCode == "MA1522" and lesson.lessonType == "Lecture"
        for lesson in timetable.weekly
    ) == 2
    assert [
        (exam.moduleCode, exam.examDate)
        for exam in timetable.exams
    ] == [
        ("MA1522", date(2026, 11, 24)),
        ("CS1231S", date(2026, 11, 26)),
        ("IS1108", date(2026, 11, 28)),
        ("CS2030S", date(2026, 11, 30)),
        ("GES1034", date(2026, 12, 1)),
    ]
