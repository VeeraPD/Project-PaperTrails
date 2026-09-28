import hashlib
import os
import re
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rag.ai import answer, embed
from rag.chunker import chunks
from rag.pdf_loader import PDFProblem, extract_pages
from rag.vector_store import clear, documents, save_document, search

load_dotenv()
ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Papertrail")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
MAX_FILE = 4 * 1024 * 1024


class Message(BaseModel):
    role: str
    content: str = Field(max_length=2500)


class Question(BaseModel):
    question: str = Field(min_length=2, max_length=2500)
    history: list[Message] = Field(default_factory=list, max_length=12)


def workspace(request: Request, response: Response) -> str:
    value = request.cookies.get("papertrail_space", "")
    if not re.fullmatch(r"[a-f0-9]{32}", value):
        value = secrets.token_hex(16)
        response.set_cookie("papertrail_space", value, httponly=True, secure=request.url.scheme == "https", samesite="lax", max_age=60 * 60 * 24 * 30)
    return value


def same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Cross-origin requests are blocked.")


@app.get("/")
def home():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/documents")
def list_documents(request: Request, response: Response):
    try:
        return {"documents": documents(workspace(request, response))}
    except Exception as exc:
        raise HTTPException(503, "Document storage is unavailable. Check server configuration.") from exc


@app.post("/api/upload")
async def upload(request: Request, response: Response, files: list[UploadFile] = File(...)):
    same_origin(request)
    if not 1 <= len(files) <= 5:
        raise HTTPException(400, "Upload 1 to 5 PDFs at a time.")
    if int(request.headers.get("content-length", "0")) > MAX_FILE + 128 * 1024:
        raise HTTPException(413, "Total upload exceeds 4 MB. Upload fewer PDFs at once.")
    space = workspace(request, response)
    results = []
    for file in files:
        name = Path(file.filename or "").name[:120]
        if not name.lower().endswith(".pdf"):
            results.append({"name": name, "error": "Choose a PDF file."})
            continue
        data = await file.read(MAX_FILE + 1)
        await file.close()
        if len(data) > MAX_FILE:
            results.append({"name": name, "error": "File exceeds the 4 MB limit."})
            continue
        if not data.startswith(b"%PDF-"):
            results.append({"name": name, "error": "This file is not a valid PDF."})
            continue
        try:
            pages = extract_pages(data)
            doc_id = hashlib.sha256(data).hexdigest()[:24]
            if any(d["id"] == doc_id for d in documents(space)):
                results.append({"name": name, "error": "This PDF is already in your workspace."})
                continue
            passages = list(chunks(pages, name, doc_id))
            if len(passages) > 300:
                raise PDFProblem("This document is too long for the initial version (300 passages maximum).")
            vectors = embed([p["text"] for p in passages])
            record = {"id": doc_id, "name": name, "pages": len(pages)}
            save_document(space, record, passages, vectors)
            results.append({"name": name, "document": record})
        except PDFProblem as exc:
            results.append({"name": name, "error": str(exc)})
        except Exception:
            results.append({"name": name, "error": "Processing failed. Check service configuration or retry."})
    return {"results": results, "documents": documents(space)}


@app.post("/api/chat")
def chat(payload: Question, request: Request, response: Response):
    same_origin(request)
    space = workspace(request, response)
    try:
        if not documents(space):
            raise HTTPException(400, "Upload a PDF first.")
        history = [m.model_dump() for m in payload.history if m.role in ("user", "assistant")]
        recent_users = [m["content"] for m in history if m["role"] == "user"][-2:]
        query = " ".join(recent_users + [payload.question])[:4000]
        passages = search(space, embed([query], query=True)[0])
        if not passages:
            return {"answer": "I couldn't find enough information in the uploaded documents to answer this confidently.", "sources": []}
        response_text = answer(payload.question, history, passages)
        cited = {int(n) for n in re.findall(r"\[(\d+)\]", response_text)}
        cited = {n for n in cited if 1 <= n <= len(passages)}
        response_text = re.sub(r"\[(\d+)\]", lambda m: m.group(0) if int(m.group(1)) in cited else "", response_text)
        if not cited and "couldn't find enough information" not in response_text.lower():
            response_text = "I couldn't find enough information in the uploaded documents to answer this confidently."
        sources = [{"number": i, "filename": passages[i - 1]["filename"], "page": passages[i - 1]["page"]} for i in sorted(cited)]
        return {"answer": response_text, "sources": sources}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "Could not answer right now. Please retry.") from exc


@app.delete("/api/workspace")
def reset(request: Request, response: Response):
    same_origin(request)
    try:
        clear(workspace(request, response))
    except Exception as exc:
        raise HTTPException(503, "Could not clear the workspace. Please retry.") from exc
    response.delete_cookie("papertrail_space")
    return {"ok": True}
