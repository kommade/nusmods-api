from unittest.mock import Mock

import pytest
import requests
from datetime import datetime

from nusmods_api import (
    NUSModsClient,
    NUSModsHTTPError,
    NUSModsInvalidResponseError,
    NUSModsNotFoundError,
    NUSModsRequestError,
)
from nusmods_api.models import Lesson, Module, SemesterData


SHARED_TIMETABLE_URL = (
    "https://nusmods.com/timetable/sem-1/share?"
    "CS1231S=TUT:25B,LEC:1&"
    "CS2030S=REC:04,LAB:10B,LEC:1&"
    "GES1034=LEC:1,TUT:E2&"
    "IS1108=TUT:14,LEC:2&"
    "MA1522=LEC:1"
)


def make_client(tmp_path, **kwargs):
    kwargs.setdefault("cache_directory", tmp_path / "cache")
    return NUSModsClient(
        academic_year="2025-2026",
        **kwargs,
    )


def make_response(status_code=200, json_data=None, json_error=None):
    response = Mock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    if json_error is not None:
        response.json.side_effect = json_error
    else:
        response.json.return_value = json_data
    return response


def make_lesson(
    class_no,
    lesson_type,
    day,
    start_time,
    end_time,
    venue,
):
    return Lesson(
        classNo=class_no,
        startTime=start_time,
        endTime=end_time,
        weeks=[1, 2],
        venue=venue,
        day=day,
        lessonType=lesson_type,
        size=50,
    )


def make_module(module_code, lessons, exam_date):
    return Module(
        moduleCode=module_code,
        title=f"{module_code} title",
        semesters=[1],
        acadYear="2025-2026",
        semesterData=[
            SemesterData(
                semester=1,
                examDate=exam_date,
                examDuration=120,
                timetable=lessons,
            ),
        ],
    )


def shared_timetable_modules():
    return {
        "CS1231S": make_module(
            "CS1231S",
            [
                make_lesson("25B", "Tutorial", "Friday", "1600", "1800", "COM1-0203"),
                make_lesson("1", "Lecture", "Thursday", "1200", "1400", "UT-AUD1"),
                make_lesson("1", "Lecture", "Friday", "1200", "1300", "UT-AUD1"),
            ],
            datetime(2026, 11, 26),
        ),
        "CS2030S": make_module(
            "CS2030S",
            [
                make_lesson("04", "Recitation", "Wednesday", "1300", "1400", "COM1-0203"),
                make_lesson("10B", "Laboratory", "Thursday", "1000", "1200", "COM1-0203"),
                make_lesson("1", "Lecture", "Monday", "1200", "1400", "LT19"),
            ],
            datetime(2026, 11, 30),
        ),
        "GES1034": make_module(
            "GES1034",
            [
                make_lesson("1", "Lecture", "Monday", "1000", "1200", "LT1"),
                make_lesson("E2", "Tutorial", "Tuesday", "1200", "1400", "COM1-0203"),
            ],
            datetime(2026, 12, 1),
        ),
        "IS1108": make_module(
            "IS1108",
            [
                make_lesson("14", "Tutorial", "Thursday", "0800", "1000", "COM1-0203"),
                make_lesson("2", "Lecture", "Thursday", "1200", "1400", "LT2"),
            ],
            datetime(2026, 11, 28),
        ),
        "MA1522": make_module(
            "MA1522",
            [
                make_lesson("1", "Lecture", "Friday", "0800", "1000", "LT3"),
            ],
            datetime(2026, 11, 24),
        ),
    }


def test_client_configures_api_headers(tmp_path):
    client = make_client(tmp_path)

    assert client.session.headers["Accept"] == "application/json"
    assert client.session.headers["User-Agent"] == "nusmods-api-python/0.1.0)"


def test_invalid_academic_year_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Invalid academic year format"):
        NUSModsClient("2025", cache_directory=tmp_path / "cache")


def test_build_url_uses_academic_year(tmp_path):
    client = make_client(tmp_path)

    assert (
        client._build_url("modules.json")
        == "https://api.nusmods.com/v2/2025-2026/modules.json"
    )


def test_get_returns_json_and_caches_response(tmp_path):
    client = make_client(tmp_path)
    client.session.get = Mock(
        return_value=make_response(json_data={"moduleCode": "CS1010"})
    )

    assert client._get("modules/CS1010.json") == {"moduleCode": "CS1010"}
    assert client._get("modules/CS1010.json") == {"moduleCode": "CS1010"}
    client.session.get.assert_called_once_with(
        "https://api.nusmods.com/v2/2025-2026/modules/CS1010.json",
        timeout=10.0,
    )


def test_get_skips_cache_when_cache_is_disabled(tmp_path):
    client = make_client(tmp_path, cache_directory=None)
    client.session.get = Mock(return_value=make_response(json_data={"value": 1}))

    assert client._get("resource.json") == {"value": 1}
    assert client._get("resource.json") == {"value": 1}
    assert client.session.get.call_count == 2


def test_get_raises_not_found(tmp_path):
    client = make_client(tmp_path)
    client.session.get = Mock(return_value=make_response(status_code=404))

    with pytest.raises(NUSModsNotFoundError) as error:
        client._get("modules/MISSING.json")

    assert error.value.status_code == 404


def test_get_raises_http_error(tmp_path):
    client = make_client(tmp_path)
    client.session.get = Mock(return_value=make_response(status_code=500))

    with pytest.raises(NUSModsHTTPError) as error:
        client._get("modules/CS1010.json")

    assert error.value.status_code == 500


def test_get_raises_invalid_response_error(tmp_path):
    client = make_client(tmp_path)
    client.session.get = Mock(
        return_value=make_response(json_error=ValueError("not JSON"))
    )

    with pytest.raises(NUSModsInvalidResponseError):
        client._get("modules/CS1010.json")


def test_get_wraps_request_errors(tmp_path):
    client = make_client(tmp_path)
    client.session.get = Mock(side_effect=requests.ConnectionError("offline"))

    with pytest.raises(NUSModsRequestError) as error:
        client._get("modules/CS1010.json")

    assert "Could not connect" in str(error.value)


def test_get_module_normalizes_module_code(tmp_path):
    client = make_client(tmp_path)
    client._get = Mock(
        return_value={
            "moduleCode": "CS1010",
            "title": "Programming Methodology",
            "semesters": [1, 2],
            "acadYear": "2025-2026",
        }
    )

    module = client.get_module(" cs1010 ")

    assert module.moduleCode == "CS1010"
    client._get.assert_called_once_with("modules/CS1010.json")


def test_get_module_list_maps_condensed_modules(tmp_path):
    client = make_client(tmp_path)
    client._get = Mock(
        return_value=[
            {"moduleCode": "CS1010", "title": "Programming", "semesters": [1]},
        ]
    )

    modules = client.get_module_list()

    assert modules[0].moduleCode == "CS1010"
    assert modules[0].semesters == [1]
    client._get.assert_called_once_with("modules.json")


def test_get_module_information_maps_detailed_modules(tmp_path):
    client = make_client(tmp_path)
    client._get = Mock(
        return_value=[
            {
                "moduleCode": "CS1010",
                "title": "Programming",
                "semesters": [1],
                "acadYear": "2025-2026",
            },
        ]
    )

    modules = client.get_module_information()

    assert modules[0].acadYear == "2025-2026"
    client._get.assert_called_once_with("moduleInformation.json")


@pytest.mark.parametrize("semester", [0, 3, -1])
def test_get_venues_rejects_invalid_semester(tmp_path, semester):
    client = make_client(tmp_path)

    with pytest.raises(ValueError, match="Semester must be 1 or 2"):
        client.get_venues(semester)


def test_get_venues_returns_api_data(tmp_path):
    client = make_client(tmp_path)
    client._get = Mock(return_value=["COM1-01-01", "COM2-02-02"])

    assert client.get_venues(2) == ["COM1-01-01", "COM2-02-02"]
    client._get.assert_called_once_with("semesters/2/venues.json")


def test_get_venue_information_groups_lessons_by_venue(tmp_path):
    client = make_client(tmp_path)
    client._get = Mock(
        return_value=[
            {
                "venue": "COM1-01-01",
                "classes": [
                    {
                        "day": "Monday",
                        "classes": [
                            {
                                "moduleCode": "CS1010",
                                "classNo": "1",
                                "startTime": "1000",
                                "endTime": "1200",
                                "weeks": [1],
                                "venue": "COM1-01-01",
                                "day": "Monday",
                                "lessonType": "Lecture",
                                "size": 50,
                            },
                        ],
                    },
                ],
            },
        ]
    )

    result = client.get_venue_information(1)

    assert len(result["COM1-01-01"]) == 1
    assert result["COM1-01-01"][0].day == "Monday"
    assert result["COM1-01-01"][0].classes[0]["moduleCode"] == "CS1010"
    client._get.assert_called_once_with("semesters/1/venues.json")


def test_get_venue_information_rejects_invalid_semester(tmp_path):
    client = make_client(tmp_path)

    with pytest.raises(ValueError, match="Semester must be 1 or 2"):
        client.get_venue_information(4)


def test_get_shared_timetable_matches_shared_url_schedule(tmp_path):
    client = make_client(tmp_path)
    modules = shared_timetable_modules()
    client.get_module = Mock(side_effect=modules.__getitem__)

    timetable = client.get_shared_timetable(SHARED_TIMETABLE_URL)

    assert timetable.semester == 1
    assert len(timetable.weekly) == 11
    assert len(timetable.exams) == 5
    assert {lesson.moduleCode for lesson in timetable.weekly} == set(modules)
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

    assert [
        (lesson.day, lesson.startTime, lesson.moduleCode)
        for lesson in timetable.weekly
    ] == [
        ("Monday", "1000", "GES1034"),
        ("Monday", "1200", "CS2030S"),
        ("Tuesday", "1200", "GES1034"),
        ("Wednesday", "1300", "CS2030S"),
        ("Thursday", "0800", "IS1108"),
        ("Thursday", "1000", "CS2030S"),
        ("Thursday", "1200", "CS1231S"),
        ("Thursday", "1200", "IS1108"),
        ("Friday", "0800", "MA1522"),
        ("Friday", "1200", "CS1231S"),
        ("Friday", "1600", "CS1231S"),
    ]

    assert [
        (exam.moduleCode, exam.examDate)
        for exam in timetable.exams
    ] == [
        ("MA1522", datetime(2026, 11, 24)),
        ("CS1231S", datetime(2026, 11, 26)),
        ("IS1108", datetime(2026, 11, 28)),
        ("CS2030S", datetime(2026, 11, 30)),
        ("GES1034", datetime(2026, 12, 1)),
    ]
    assert [call.args[0] for call in client.get_module.call_args_list] == [
        "CS1231S",
        "CS2030S",
        "GES1034",
        "IS1108",
        "MA1522",
    ]


def test_get_shared_timetable_accepts_www_nusmods_url(tmp_path):
    client = make_client(tmp_path)
    client.get_module = Mock(
        return_value=make_module(
            "CS1231S",
            [make_lesson("1", "Lecture", "Monday", "0800", "1000", "LT1")],
            None,
        )
    )

    timetable = client.get_shared_timetable(
        "https://www.nusmods.com/timetable/sem-1/share?CS1231S=LEC:1"
    )

    assert timetable.semester == 1
    assert len(timetable.weekly) == 1
    assert timetable.exams == []


@pytest.mark.parametrize(
    "url, message",
    [
        ("https://example.com/timetable/sem-1/share?CS1010=LEC:1", "nusmods.com"),
        ("https://nusmods.com/module/CS1010", "form"),
        ("https://nusmods.com/timetable/sem-1/share", "no module selections"),
    ],
)
def test_get_shared_timetable_rejects_invalid_share_urls(tmp_path, url, message):
    client = make_client(tmp_path)

    with pytest.raises(ValueError, match=message):
        client.get_shared_timetable(url)


def test_get_shared_timetable_rejects_unknown_lesson_selection(tmp_path):
    client = make_client(tmp_path)
    client.get_module = Mock(
        return_value=make_module(
            "CS1231S",
            [make_lesson("1", "Lecture", "Monday", "0800", "1000", "LT1")],
            None,
        )
    )

    with pytest.raises(ValueError, match="Could not find selected lessons"):
        client.get_shared_timetable(
            "https://nusmods.com/timetable/sem-1/share?CS1231S=TUT:25B"
        )


def test_get_shared_timetable_rejects_malformed_lesson_selection(tmp_path):
    client = make_client(tmp_path)
    client.get_module = Mock(
        return_value=make_module(
            "CS1231S",
            [make_lesson("1", "Lecture", "Monday", "0800", "1000", "LT1")],
            None,
        )
    )

    with pytest.raises(ValueError, match="Invalid lesson selection"):
        client.get_shared_timetable(
            "https://nusmods.com/timetable/sem-1/share?CS1231S=LEC"
        )


def test_get_shared_timetable_requires_module_data_for_requested_semester(tmp_path):
    client = make_client(tmp_path)
    client.get_module = Mock(
        return_value=Module(
            moduleCode="CS1231S",
            title="CS1231S title",
            semesters=[2],
            acadYear="2025-2026",
            semesterData=[],
        )
    )

    with pytest.raises(ValueError, match="has no data for semester 1"):
        client.get_shared_timetable(
            "https://nusmods.com/timetable/sem-1/share?CS1231S=LEC:1"
        )
