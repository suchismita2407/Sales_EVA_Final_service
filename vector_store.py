import chromadb
from chromadb.config import Settings
from config import Config

# You can have multiple collections: offerings, case_studies, opportunities
client = chromadb.PersistentClient(path=Config.CHROMA_DIR, settings=Settings(allow_reset=True))

def get_collection(name: str):
    return client.get_or_create_collection(name=name)

offerings_col = get_collection("offerings_embeddings")
case_studies_col = get_collection("case_studies_embeddings")
opportunities_col = get_collection("opportunities_embeddings")
