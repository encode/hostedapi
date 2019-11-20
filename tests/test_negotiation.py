from source.negotiation import negotiate, MediaType
from starlette.exceptions import HTTPException
import pytest


def test_media_types():
    media_type = MediaType("*/*")
    assert media_type.precedence == 0
    assert str(media_type) == "*/*"

    media_type = MediaType("text/*")
    assert media_type.precedence == 1
    assert str(media_type) == "text/*"

    media_type = MediaType("text/html")
    assert media_type.precedence == 2
    assert str(media_type) == "text/html"

    media_type = MediaType("text/html; q=0.9")
    assert media_type.precedence == 2
    assert str(media_type) == "text/html; q=0.9"


def test_negotiate():
    media_type = negotiate("*/*", ["application/json", "text/html"])
    assert media_type == "application/json"

    media_type = negotiate("application/json, */*", ["application/json", "text/html"])
    assert media_type == "application/json"

    media_type = negotiate("text/html, */*", ["application/json", "text/html"])
    assert media_type == "text/html"

    media_type = negotiate("text/*, */*", ["application/json", "text/html"])
    assert media_type == "text/html"


def test_failed_negotiate():
    with pytest.raises(HTTPException):
        negotiate("text/csv", ["application/json", "text/html"])
