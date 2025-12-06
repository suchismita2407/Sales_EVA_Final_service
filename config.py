import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DATABASE_PATH = os.path.join(BASE_DIR, "sales_eva.db")

    # LLM / embeddings config (adapt to TCS GenAI Lab etc.)
    LLM_API_KEY = os.getenv("LLM_API_KEY", "REMOVED_LLM_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://genailab.tcs.in")
    LLM_MODEL = os.getenv("LLM_MODEL", "azure_ai/genailab-maas-DeepSeek-V3-0324")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "azure/genailab-maas-text-embedding-3-large")

    # Chroma config
    CHROMA_DIR = os.path.join(BASE_DIR, "chroma_data")
