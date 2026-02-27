import os
import chromadb
from openai import OpenAI

BASE_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"

def get_openai_client():
    return OpenAI(
        base_url=BASE_URL,
        api_key="any value",
        default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")},
    )

def embed_text(client, text: str):
    text = text.replace("\n", " ")
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=[text]
    )
    return resp.data[0].embedding

def get_collection(path="05_src/assignment_chat/chroma_store", name="course_kb"):
    chroma = chromadb.PersistentClient(path=path)
    return chroma.get_or_create_collection(name=name)

def build_kb_if_empty(kb_path="05_src/assignment_chat/data/kb.txt"):
    client = get_openai_client()
    col = get_collection()

    try:
        if col.count() > 0:
            return
    except Exception:
        pass

    with open(kb_path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]

    embeddings = [embed_text(client, c) for c in chunks]
    ids = [f"kb{i}" for i in range(len(chunks))]

    col.add(documents=chunks, embeddings=embeddings, ids=ids)

def semantic_search(query: str, k: int = 3):
    client = get_openai_client()
    col = get_collection()

    q_emb = embed_text(client, query)
    res = col.query(query_embeddings=[q_emb], n_results=k)

    docs = res.get("documents", [[]])[0]
    return docs