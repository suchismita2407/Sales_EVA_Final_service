import logging
import os

import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from config import Config

logger = logging.getLogger(__name__)

try:
    from langfuse import observe
except (ImportError, RuntimeError, TypeError):
    def observe(**_kwargs):
        def decorator(function):
            return function
        return decorator

_llm = None
_embeddings = None

client = httpx.Client()

def get_llm():
    global _llm
    if _llm is None:
        if not Config.LLM_API_KEY:
            raise RuntimeError("LLM_API_KEY is required for LLM features")
        _llm = ChatOpenAI(
            base_url=Config.LLM_BASE_URL,
            model=Config.LLM_MODEL,
            api_key=Config.LLM_API_KEY,
            temperature=0.1,
            http_client=client
        )
    return _llm

@observe(name="eva-llm-response", as_type="generation")
def tracked_llm_call(prompt: str):
    """
    Tracks the LLM invocation automatically using Langfuse decorator.
    The return value becomes Langfuse output.
    """
    llm = get_llm()
    reply = llm.invoke(prompt)

    answer = getattr(reply, "content", str(reply))
    return answer




def get_embeddings():
    global _embeddings
    if _embeddings is None:

        # Patch: Use local tokenizer file instead of downloading from Azure Blob
        local_tokenizer_path = os.path.join(
            Config.BASE_DIR,
            "tokenizer_files",
            "cl100k_base.tiktoken"
        )

        if os.path.exists(local_tokenizer_path):
            logger.info("Using local tokenizer file")

            # Monkey patch 'read_file' so no HTTPS download happens
            import tiktoken.load

            def local_read_file(path):
                return open(local_tokenizer_path, "rb").read()

            tiktoken.load.read_file = local_read_file

        else:
            logger.warning(
                "Local tokenizer not found; tokenizer download may fail: %s",
                local_tokenizer_path,
            )

        _embeddings = OpenAIEmbeddings(
            base_url=Config.LLM_BASE_URL,
            api_key=Config.LLM_API_KEY,
            model=Config.EMBEDDING_MODEL,
            http_client=client,
            request_timeout=60,
        )

    return _embeddings
