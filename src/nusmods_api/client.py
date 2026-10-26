"""Main client for the NUSMods API."""

from __future__ import annotations

import re
import warnings
from typing import Any

import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .cache import Cache

from .exceptions import (
    NUSModsRequestError,
    NUSModsHTTPError,
    NUSModsInvalidResponseError,
    NUSModsNotFoundError,
)

from .models import (
    WeekRange,
    Lesson,
    LessonWithModule,
    Workload,
    PrerequisiteTree,
    SemesterData,
    ModuleCondensed,
    Module,
    VenueLesson,
    VenueInformation,
    ExamTimetable,
    Timetable,
)

class NUSModsClient:
    BASE_URL = "https://api.nusmods.com/v2"
    
    LESSON_TYPE_NAMES = {
        "LEC": "Lecture",
        "TUT": "Tutorial",
        "LAB": "Laboratory",
        "REC": "Recitation",
        "SEM": "Seminar",
        "SEC": "Sectional Teaching",
        "PRA": "Practical",
    }

    DAY_ORDER = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    
    def __init__(
        self,
        academic_year: str | None = None,
        timeout: float = 10.0,
        cache_directory: str | Path | None = ".nusmods_cache",
        cache_expiration: int | None = 86_400,
    ) -> None:
        if academic_year is not None:
            if re.fullmatch(r"\d{4}-\d{4}", academic_year) is None:
                raise ValueError("Invalid academic year format. Expected 'YYYY-YYYY'.")
            self.academic_year = academic_year
        else:
            this_year = datetime.now().year
            next_year = this_year + 1
            self.academic_year = f"{this_year}-{next_year}"
        self.timeout = timeout
        
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": f"nusmods-api-python/0.1.0)",
        })
        
        self.cache = Cache(
            directory=cache_directory,
            expiration=cache_expiration,
        ) if cache_directory is not None else None
        
    def _build_url(self, endpoint: str) -> str:
        if self.academic_year is None:
            raise ValueError("Academic year is not set")
        return f"{self.BASE_URL}/{self.academic_year}/{endpoint}"
    
    def _get(self, path: str) -> Any:
        url = self._build_url(path)
        
        if self.cache is not None:
            cached_response = self.cache.get(url)
            if cached_response is not None:
                return cached_response
        
        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as e:
            raise NUSModsRequestError(
                f"Could not connect to NUSMods API: {url}"
            ) from e
            
        if response.status_code == 404:
            raise NUSModsNotFoundError(url)
        
        if not response.ok:
            raise NUSModsHTTPError(
                status_code=response.status_code,
                url=url,
                message=f"NUSMods API returned HTTP {response.status_code}",
            )
        try:
            data = response.json()
        except ValueError as e:
            raise NUSModsInvalidResponseError(
                url=url,
                message="Invalid JSON response",
            ) from e
        
        if self.cache is not None:
            self.cache.set(url, data)
            
        return data
            
    def get_module_list(self) -> list[ModuleCondensed]:
        """Get a list of all modules for the academic year."""
        data = self._get("modules.json")
        return [ModuleCondensed(**module) for module in data]
    
    def get_module_information(self) -> list[Module]:
        """Get detailed information for all modules for the academic year."""
        data = self._get("moduleInformation.json")
        return [self._parse_module(module) for module in data]
    
    def get_module(self, module_code: str) -> Module:
        """Get detailed information for a specific module."""
        module_code = module_code.strip().upper()
        data = self._get(f"modules/{module_code}.json")
        return self._parse_module(data)

    def _parse_module(self, data: dict[str, Any]) -> Module:
        module_data = {
            "moduleCode": data["moduleCode"],
            "title": data["title"],
            "semesters": data.get("semesters", []),
            "acadYear": data["acadYear"],
            "preclusion": data.get("preclusion"),
            "description": data.get("description"),
            "department": data.get("department"),
            "faculty": data.get("faculty"),
            "moduleCredit": data.get("moduleCredit"),
            "attributes": data.get("attributes"),
            "prerequisite": data.get("prerequisite"),
            "corequisite": data.get("corequisite"),
            "workload": (
                Workload.from_list(data["workload"])
                if isinstance(data.get("workload"), list)
                else data.get("workload")
            ),
            "fulfill_requirements": data.get("fulfillRequirements"),
            "prerequisite_tree": self._parse_prerequisite_tree(
                data.get("prereqTree")
            ),
            "semesterData": [
                SemesterData(
                    semester=semester["semester"],
                    examDate=semester.get("examDate"),
                    examDuration=semester.get("examDuration"),
                    timetable=[
                        Lesson(**{
                            key: lesson[key]
                            for key in (
                                "classNo",
                                "startTime",
                                "endTime",
                                "weeks",
                                "venue",
                                "day",
                                "lessonType",
                                "size",
                            )
                        })
                        for lesson in semester.get("timetable") or []
                    ],
                )
                for semester in data.get("semesterData") or []
            ],
        }
        return Module(**module_data)

    def _parse_prerequisite_tree(
        self,
        data: dict[str, Any] | None,
    ) -> PrerequisiteTree | None:
        if data is None:
            return None

        def parse_children(
            values: list[str | dict[str, Any]],
        ) -> list[str | PrerequisiteTree]:
            return list(filter(None, (
                self._parse_prerequisite_tree(value)
                if isinstance(value, dict)
                else value
                for value in values
            )))

        return PrerequisiteTree(
            and_=parse_children(data["and"]) if "and" in data else None,
            or_=parse_children(data["or"]) if "or" in data else None,
        )
    
    def get_venues(self, semester: int) -> list[str]:
        """Get a list of all venues for the academic year."""
        if semester not in (1, 2):
            raise ValueError("Semester must be 1 or 2")
        data = self._get(f"semesters/{semester}/venues.json")
        return data
    
    def get_venue_information(self, semester: int) -> dict[str, list[VenueInformation]]:
        """Get timetable information grouped by venue"""
        if semester not in (1, 2):
            raise ValueError("Semester must be 1 or 2")
        data = self._get(f"semesters/{semester}/venues.json")
        venue_info = {}
        for venue in data:
            venue_name = venue["venue"]
            lessons = [VenueInformation(**lesson) for lesson in venue["classes"]]
            venue_info[venue_name] = lessons
        return venue_info
        
    def get_shared_timetable(
        self,
        share_url: str,
    ) -> Timetable:
        parsed_url = urlparse(share_url)

        if parsed_url.netloc not in {
            "nusmods.com",
            "www.nusmods.com",
        }:
            raise ValueError("URL must belong to nusmods.com")

        semester_match = re.search(
            r"/timetable/sem-(\d+)/share",
            parsed_url.path,
        )

        if semester_match is None:
            raise ValueError(
                "URL must have the form /timetable/sem-{n}/share"
            )

        semester = int(semester_match.group(1))
        query = parse_qs(parsed_url.query)

        if not query:
            raise ValueError("Share URL contains no module selections")

        weekly_lessons: list[LessonWithModule] = []
        exams: list[ExamTimetable] = []

        for module_code, selection_groups in query.items():
            try:
                module = self.get_module(module_code)
            except NUSModsNotFoundError:
                warnings.warn(
                    f"Could not find module {module_code}; skipping it",
                    UserWarning,
                    stacklevel=2,
                )
                continue

            semester_data = next(
                (
                    data
                    for data in module.semesterData or []
                    if data.semester == semester
                ),
                None,
            )

            if semester_data is None:
                warnings.warn(
                    f"{module_code} has no data for semester {semester}; "
                    "skipping it",
                    UserWarning,
                    stacklevel=2,
                )
                continue

            selected_lessons = self._select_lessons(
                module_code=module_code,
                lessons=semester_data.timetable or [],
                selection_groups=selection_groups,
            )

            weekly_lessons.extend(selected_lessons)

            if semester_data.examDate is not None:
                exams.append(
                    ExamTimetable(
                        moduleCode=module_code,
                        examDate=semester_data.examDate,
                        examDuration=semester_data.examDuration,
                    )
                )

        weekly_lessons.sort(key=self._lesson_sort_key)
        exams.sort(key=self._exam_sort_key)

        return Timetable(
            semester=semester,
            weekly=weekly_lessons,
            exams=exams,
        )
    
    def _select_lessons(
        self,
        module_code: str,
        lessons: list[Lesson],
        selection_groups: list[str],
    ) -> list[LessonWithModule]:
        requested: set[tuple[str, str]] = set()

        for selection_group in selection_groups:
            for selection in selection_group.split(","):
                try:
                    lesson_type_code, class_no = selection.split(":", 1)
                except ValueError as error:
                    raise ValueError(
                        f"Invalid lesson selection for {module_code}: "
                        f"{selection!r}"
                    ) from error

                lesson_type = self.LESSON_TYPE_NAMES.get(
                    lesson_type_code.upper(),
                    lesson_type_code,
                )

                requested.add((lesson_type, class_no))

        selected = [
            LessonWithModule(
                moduleCode=module_code,
                classNo=lesson.classNo,
                startTime=lesson.startTime,
                endTime=lesson.endTime,
                weeks=lesson.weeks,
                venue=lesson.venue,
                day=lesson.day,
                lessonType=lesson.lessonType,
                size=lesson.size,
            )
            for lesson in lessons
            if (lesson.lessonType, lesson.classNo) in requested
        ]

        found = {
            (lesson.lessonType, lesson.classNo)
            for lesson in selected
        }

        missing = requested - found

        if missing:
            warnings.warn(
                f"Could not find selected lessons for {module_code}: "
                f"{sorted(missing)}; returning the lessons that were found",
                UserWarning,
                stacklevel=2,
            )

        return selected
    
    def _lesson_sort_key(
        self,
        lesson: LessonWithModule,
    ) -> tuple[int, int, str, str]:
        try:
            start_minutes = (
                int(lesson.startTime[:2]) * 60
                + int(lesson.startTime[2:])
            )
        except ValueError:
            start_minutes = 0

        return (
            self.DAY_ORDER.get(lesson.day, len(self.DAY_ORDER)),
            start_minutes,
            lesson.moduleCode,
            lesson.lessonType,
        )
        
    def _exam_sort_key(
        self,
        exam: ExamTimetable,
    ) -> tuple[datetime, str]:
        return (
            exam.examDate or datetime.max,
            exam.moduleCode,
        )