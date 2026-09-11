import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SECRET_KEY = os.getenv("SECRET_KEY")
    DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "sales_eva.db"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    TESTING = os.getenv("TESTING", "false").lower() == "true"

    # LLM / embeddings config (adapt to TCS GenAI Lab etc.)
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://genailab.tcs.in")
    LLM_MODEL = os.getenv("LLM_MODEL", "azure_ai/genailab-maas-DeepSeek-V3-0324")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "azure/genailab-maas-text-embedding-3-large")

    # Chroma config
    CHROMA_DIR = os.path.join(BASE_DIR, "chroma_data")
