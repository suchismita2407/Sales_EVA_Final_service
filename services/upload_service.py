import os
import uuid

from werkzeug.utils import secure_filename

from config import Config

UPLOAD_FOLDER = os.path.join(Config.BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILENAME_LENGTH = 255

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def save_uploaded_file(file):
    filename = secure_filename((file.filename or "").strip())
    extension = os.path.splitext(filename)[1].lower()
    if not filename or len(filename) > MAX_FILENAME_LENGTH:
        raise ValueError("A valid filename is required")
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF, DOCX, and TXT files are supported")

    new_name = f"{uuid.uuid4()}_{filename}"
    path = os.path.join(UPLOAD_FOLDER, new_name)
    file.save(path)
    return path
