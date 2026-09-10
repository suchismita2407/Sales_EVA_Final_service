from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from services.upload_service import save_uploaded_file


def test_upload_rejects_unsupported_extension():
    upload = FileStorage(stream=BytesIO(b"not an executable"), filename="payload.exe")

    with pytest.raises(ValueError, match="Only PDF"):
        save_uploaded_file(upload)


def test_upload_sanitizes_supported_filename(tmp_path, monkeypatch):
    from services import upload_service

    monkeypatch.setattr(upload_service, "UPLOAD_FOLDER", str(tmp_path))
    upload = FileStorage(stream=BytesIO(b"plain text"), filename="client notes.txt")

    path = save_uploaded_file(upload)

    assert path.startswith(str(tmp_path))
    assert path.endswith("_client_notes.txt")