from nusmods_api.exceptions import (
    NUSModsHTTPError,
    NUSModsInvalidResponseError,
    NUSModsNotFoundError,
)


def test_http_error_exposes_status_and_url():
    error = NUSModsHTTPError(503, "https://example.test/resource")

    assert error.status_code == 503
    assert error.url == "https://example.test/resource"
    assert "503" in str(error)


def test_not_found_error_is_http_error():
    error = NUSModsNotFoundError("https://example.test/missing")

    assert isinstance(error, NUSModsHTTPError)
    assert error.status_code == 404
    assert "resource not found" in str(error)


def test_invalid_response_error_exposes_url_and_message():
    error = NUSModsInvalidResponseError(
        "https://example.test/resource",
        "Malformed payload",
    )

    assert error.url == "https://example.test/resource"
    assert error.message == "Malformed payload"
    assert "Malformed payload" in str(error)
