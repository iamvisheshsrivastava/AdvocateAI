import pytest
from fastapi import HTTPException

from routers.documents import _validate_upload_type


def test_valid_pdf_and_png():
    _validate_upload_type("a.pdf", "application/pdf", b"%PDF-1.4 x")
    _validate_upload_type("a.PNG", "application/octet-stream", b"\x89PNG\r\n\x1a\nxx")


@pytest.mark.parametrize(
    "name,ctype,data",
    [
        ("a.exe", "application/octet-stream", b"MZ"),
        ("a.pdf", "text/html", b"%PDF-1"),
        ("a.pdf", "application/pdf", b"<html>"),
        ("a.jpg", "image/jpeg", b"notjpeg"),
        ("noext", None, b"%PDF-"),
    ],
)
def test_rejected(name, ctype, data):
    with pytest.raises(HTTPException) as exc:
        _validate_upload_type(name, ctype, data)
    assert exc.value.status_code == 415
