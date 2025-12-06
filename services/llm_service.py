from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from config import Config
import httpx
import os
import tiktoken
import ssl

# Disable SSL verification everywhere (corporate proxy fix)
ssl._create_default_https_context = ssl._create_unverified_context
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["CURL_CA_BUNDLE"] = ""

_llm = None
_embeddings = None

# HTTP client for TCS MaaS
client = httpx.Client(verify=False)

def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            base_url=Config.LLM_BASE_URL,
            model=Config.LLM_MODEL,
            api_key=Config.LLM_API_KEY,
            temperature=0.1,
            http_client=client
        )
    return _llm

import os
from langfuse import observe
from services.llm_service import get_llm

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
            print(">>> Using LOCAL tokenizer file")

            # Monkey patch 'read_file' so no HTTPS download happens
            import tiktoken.load

            def local_read_file(path):
                return open(local_tokenizer_path, "rb").read()

            tiktoken.load.read_file = local_read_file

        else:
            print("⚠ Local tokenizer NOT found — tokenizer download will FAIL!")
            print("👉 You MUST place this file:")
            print(local_tokenizer_path)

        _embeddings = OpenAIEmbeddings(
            base_url=Config.LLM_BASE_URL,
            api_key=Config.LLM_API_KEY,
            model=Config.EMBEDDING_MODEL,
            http_client=client,
            request_timeout=60,
        )

    return _embeddings
