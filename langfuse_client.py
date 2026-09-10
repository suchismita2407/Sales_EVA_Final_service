import os

try:
    from langfuse import Langfuse
except Exception:
    Langfuse = None

langfuse = None

if Langfuse and os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
    langfuse = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        base_url=os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
    )
