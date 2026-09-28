import json
import os

import chromadb


COLLECTION = "papertrail_documents"


def collection():
    if os.getenv("CHROMA_API_KEY"):
        client = chromadb.CloudClient(
            api_key=os.environ["CHROMA_API_KEY"],
            tenant=os.environ["CHROMA_TENANT"],
            database=os.environ["CHROMA_DATABASE"],
        )
    else:
        if os.getenv("VERCEL"):
            raise RuntimeError("Chroma Cloud credentials are required on Vercel.")
        client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "./chroma_data"))
    return client.get_or_create_collection(name=COLLECTION, configuration={"hnsw": {"space": "cosine"}})


def documents(space: str) -> list[dict]:
    result = collection().get(ids=[f"{space}:manifest"], include=["documents"])
    return json.loads(result["documents"][0]) if result["ids"] else []


def save_document(space: str, document: dict, chunks: list[dict], vectors: list[list[float]]) -> None:
    db = collection()
    old = documents(space)
    for offset in range(0, len(chunks), 40):
        batch = chunks[offset:offset + 40]
        db.upsert(
            ids=[f"{space}:{c['id']}" for c in batch],
            embeddings=vectors[offset:offset + 40],
            documents=[c["text"] for c in batch],
            metadatas=[{"workspace": space, "kind": "passage", "filename": c["filename"], "page": c["page"], "chunk_id": c["id"]} for c in batch],
        )
    db.upsert(
        ids=[f"{space}:manifest"],
        embeddings=[[1.0] + [0.0] * (len(vectors[0]) - 1)],
        documents=[json.dumps(old + [document])],
        metadatas=[{"workspace": space, "kind": "manifest"}],
    )


def search(space: str, vector: list[float]) -> list[dict]:
    result = collection().query(
        query_embeddings=[vector],
        n_results=8,
        where={"$and": [{"workspace": space}, {"kind": "passage"}]},
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"id": ident, "filename": meta["filename"], "page": meta["page"], "text": text, "score": 1 - distance}
        for ident, meta, text, distance in zip(result["ids"][0], result["metadatas"][0], result["documents"][0], result["distances"][0])
        if text
    ]


def clear(space: str) -> None:
    collection().delete(where={"workspace": space})
