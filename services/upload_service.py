import os
import uuid
from werkzeug.utils import secure_filename
from config import Config
from db import execute
from services.rag_service import embed_text
from vector_store import offerings_col, case_studies_col

# Document folder
UPLOAD_FOLDER = os.path.join(Config.BASE_DIR, "uploads")

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def save_uploaded_file(file):
    filename = secure_filename(file.filename)
    new_name = f"{uuid.uuid4()}_{filename}"
    path = os.path.join(UPLOAD_FOLDER, new_name)
    file.save(path)
    return path
