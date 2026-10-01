# Papertrail

A PDF research assistant. Upload PDFs, ask questions in plain English, and get answers that cite the exact file and page they came from.

**Built with:** FastAPI · PyMuPDF · Gemini · ChromaDB · plain HTML/CSS/JavaScript

## Table of contents

- [How it works](#how-it-works)
- [Project structure](#project-structure)
- [Requirements](#requirements)
- [Run locally](#run-locally)
- [Environment variables](#environment-variables)
- [Deploy to GitHub and Vercel](#deploy-to-github-and-vercel)
- [Verify your setup](#verify-your-setup)
- [Limits](#limits)

## How it works

```text
PDF upload
   ↓  PyMuPDF extracts the text of each page
Chunking          → paragraph-aware passages, tagged with file and page
   ↓  Gemini turns each passage into a 768-dimension vector (an "embedding")
ChromaDB          → stores the vectors and page metadata
   ↓  your question is embedded the same way and matched to similar passages
Gemini            → writes an answer using only those passages, with [1], [2] citations
```

- **Workspaces.** Each browser gets a random cookie (`papertrail_space`). Everything it uploads is stored under that ID, so browsers do not see each other's documents.
- **Storage.** The list of uploaded documents (the "manifest") and all passages live in one Chroma collection.
  - Locally, Chroma saves to a folder (`./chroma_data`) using `chromadb.PersistentClient`.
  - On Vercel, it connects to Chroma Cloud using `chromadb.CloudClient`, because serverless functions cannot keep local files.
- **Chat history** stays in the browser's memory and is sent along with each question. It is lost on reload.
- **Original PDFs are not kept.** Citations name the file and page, but cannot open the original.
- **Reset** deletes every record in the current workspace.
- **Embedding models must match.** Never mix vectors from different embedding models in one collection. If you change models, create a new Chroma database or collection and re-upload your PDFs.

## Project structure

| Path | Purpose |
| --- | --- |
| `app.py` | FastAPI server: routes for upload, chat, listing and clearing documents |
| `rag/pdf_loader.py` | Reads a PDF and returns the text of each page |
| `rag/chunker.py` | Splits page text into passages of a useful size |
| `rag/ai.py` | Talks to Gemini: creates embeddings and writes answers |
| `rag/vector_store.py` | Talks to ChromaDB: saves, searches and deletes passages |
| `static/` | The web page (`index.html`, `styles.css`, `app.js`) |
| `vercel.json` | Tells Vercel to run `app.py` as a Python function |
| `requirements.txt` | Python dependencies |

## Requirements

- Python 3.11 or newer
- A Gemini API key with embedding and text-generation access
- Chroma Cloud credentials (deployment only; local use needs no Chroma account)

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
# edit .env and set GEMINI_API_KEY
uvicorn app:app --reload
```

Open <http://localhost:8000>, upload a text-based PDF, and ask a question.

> Gemini (and Chroma Cloud, when deployed) may charge for usage.

## Environment variables

Set these in `.env` locally, or in your Vercel project settings.

| Variable | Required | Description |
| --- | --- | --- |
| `GEMINI_API_KEY` | Always | Your Gemini API key |
| `GEMINI_CHAT_MODEL` | No | Model used for answers. Defaults to `gemini-3.8-flash` |
| `CHROMA_API_KEY` | Vercel | Chroma Cloud API key |
| `CHROMA_TENANT` | Vercel | Chroma Cloud tenant ID |
| `CHROMA_DATABASE` | Vercel | Chroma Cloud database name |
| `CHROMA_PATH` | No | Local storage folder. Defaults to `./chroma_data`. Local development only |

Never commit `.env` to Git (it is already in `.gitignore`).

## Deploy to GitHub and Vercel

1. Create an **empty** repository on GitHub, then push the project:

   ```bash
   git init
   git add .
   git commit -m "Build Papertrail PDF assistant"
   git branch -M main
   git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
   git push -u origin main
   ```

2. Create a Chroma Cloud database.
3. Import the GitHub repository in Vercel. The root directory is the project root (use `pdf-rag-chatbot` if it is committed inside a parent repository).
4. Add `GEMINI_API_KEY`, `CHROMA_API_KEY`, `CHROMA_TENANT` and `CHROMA_DATABASE` (and optionally `GEMINI_CHAT_MODEL`) under **Environment Variables**. Chroma Cloud is required on Vercel.
5. Deploy. `vercel.json` runs FastAPI as a Python function, and that app also serves the web page.

## Verify your setup

1. Upload two small PDFs. Both should appear with readable page counts.
2. Ask a question answered on a known page. The citation should name that PDF and page.
3. Ask a follow-up using "that" or "it". New claims should still cite uploaded pages.
4. Ask about something not in the documents. Expect an explicit "I couldn't find enough information" reply.
5. Reload the page. The document list should remain. Click **Clear workspace** and the list should disappear.
6. Try an invalid file, a password-protected PDF and a scanned PDF. Each should give a clear error.

## Limits

**Upload limits**

- Up to 5 PDFs per request, 4 MB combined (Vercel caps request bodies at 4.5 MB; 4 MB leaves room for overhead)
- Up to 400 pages and 300 passages per PDF
- Large files can exceed Vercel's 60-second function limit. Use smaller documents, or add a background worker or direct-upload design later.

**Not included in this MVP**

- OCR for scanned documents
- Chat history across reloads
- Storing original PDFs
- User accounts and robust abuse prevention

**Things to know**

- Random cookies separate workspaces but are **not authentication**. Put the app behind access control for sensitive PDFs or public traffic.
- Clearing browser cookies loses access to your previous workspace. Stored data remains until cleared or removed by your database retention settings.
- Upload one batch at a time. Concurrent uploads to the same workspace can race when updating the manifest.
- Do not upload documents that your Gemini or Chroma data policies prohibit.
- Before opening this to the public, review service quotas and add authentication, rate limits, retention rules and background ingestion.
