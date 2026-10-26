# nusmods-api

A typed Python wrapper for the [NUSMods API](https://api.nusmods.com/).

The client provides access to module lists, detailed module information, venue
data, and shared timetable URLs from [nusmods.com](https://nusmods.com/).
Responses are converted into immutable Python dataclasses.

## Requirements

- Python 3.15 or newer
- Internet access when making API requests

## Installation

### With uv

```powershell
uv add nusmods-api
```

For local development:

```powershell
uv sync
```

### With pip

```powershell
pip install nusmods-api
```

## Quick start

```python
from nusmods_api import NUSModsClient

client = NUSModsClient(academic_year="2026-2027")

modules = client.get_module_list()
for module in modules[:5]:
    print(module.moduleCode, module.title)

module = client.get_module("CS2030S")
print(module.title)
print(module.description)
```

If no academic year is supplied, the client uses the current calendar year and
the following year. For example, a client created in 2026 uses `2026-2027`.

## Client configuration

```python
from nusmods_api import NUSModsClient

client = NUSModsClient(
    academic_year="2026-2027",
    timeout=20.0,
    cache_directory=".nusmods_cache",
    cache_expiration=86_400,
)
```

| Argument | Default | Description |
| --- | --- | --- |
| `academic_year` | Current year and next year | Academic year in `YYYY-YYYY` format |
| `timeout` | `10.0` | HTTP timeout in seconds |
| `cache_directory` | `.nusmods_cache` | Directory for cached JSON responses |
| `cache_expiration` | `86400` | Cache lifetime in seconds; use `None` for no expiration |

Set `cache_directory=None` to disable caching:

```python
client = NUSModsClient(cache_directory=None)
```

## API usage

### Module list

```python
modules = client.get_module_list()

for module in modules:
    print(module.moduleCode, module.title, module.semesters)
```

### Detailed module information

```python
modules = client.get_module_information()
module = client.get_module(" cs2030s ")

print(module.moduleCode)  # CS2030S
print(module.acadYear)
print(module.semesterData)
```

Module codes are stripped and normalized to uppercase by `get_module`.

### Venues

```python
venues = client.get_venues(semester=1)
print(venues)

venue_information = client.get_venue_information(semester=1)
for venue, entries in venue_information.items():
    print(venue, entries)
```

`semester` must be `1` or `2`.

### Shared timetables

Pass a NUSMods share URL to `get_shared_timetable`:

```python
share_url = (
    "https://nusmods.com/timetable/sem-1/share?"
    "CS1231S=TUT:25B,LEC:1&"
    "CS2030S=REC:04,LAB:10B,LEC:1&"
    "GES1034=LEC:1,TUT:E2&"
    "IS1108=TUT:14,LEC:2&"
    "MA1522=LEC:1"
)

timetable = client.get_shared_timetable(share_url)

for lesson in timetable.weekly:
    print(
        lesson.moduleCode,
        lesson.lessonType,
        lesson.classNo,
        lesson.day,
        lesson.startTime,
        lesson.endTime,
        lesson.venue,
    )

for exam in timetable.exams:
    print(exam.moduleCode, exam.examDate, exam.examDuration)
```

The client parses the module selections from the URL and retrieves the
corresponding module data from the NUSMods API. Lesson type codes such as
`LEC`, `TUT`, `LAB`, and `REC` are mapped to their full names.

`Timetable` also provides convenience methods:

```python
monday = timetable.get_day_schedule("Monday")
exam = timetable.get_exam_for_module("CS2030S")
```

## Data models

The package exposes frozen dataclasses for common API response types:

- `ModuleCondensed` — module code, title, and offered semesters
- `Module` — detailed module information
- `Lesson` — class schedule information
- `LessonWithModule` — a lesson including its module code
- `VenueLesson` and `VenueInformation` — venue timetable data
- `WeekRange` — date-based lesson ranges
- `Workload` — workload components
- `PrerequisiteTree` — nested prerequisite expressions
- `ExamTimetable` — exam information
- `Timetable` — selected weekly lessons and exams

Some model fields retain the NUSMods API naming convention, such as
`moduleCode`, `classNo`, `startTime`, `lessonType`, and `examDate`.
`ExamTimetable.examDate` is represented as a `datetime` and preserves the
time and timezone supplied by the API.

## Error handling

The client raises package-specific exceptions:

```python
from nusmods_api import (
    NUSModsHTTPError,
    NUSModsInvalidResponseError,
    NUSModsNotFoundError,
    NUSModsRequestError,
)

try:
    module = client.get_module("CS2030S")
except NUSModsNotFoundError:
    print("The module or academic year was not found")
except NUSModsHTTPError as error:
    print(error.status_code, error.url)
except NUSModsInvalidResponseError:
    print("The API returned invalid JSON")
except NUSModsRequestError:
    print("The API could not be reached")
```

Invalid client arguments, malformed share URLs, invalid semesters, and
unmatched lesson selections raise `ValueError`.

## Testing

Run the default unit test suite:

```powershell
uv run pytest
```

The live integration test makes real requests to the NUSMods API:

```powershell
uv run pytest tests/test_live_client.py -m live -q
```

The live test requires internet access and may need its expected timetable
dates updated when NUSMods publishes a new academic-year dataset.

## License

No license has been specified yet.