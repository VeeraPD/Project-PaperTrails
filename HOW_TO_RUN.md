# How to Run Papertrail

Papertrail is a PDF research assistant. It lets you upload PDFs, ask questions about them, and receive answers with file and page citations.

## Requirements

- Python 3.11 or newer
- A Gemini API key
- The project dependencies from `requirements.txt`

## Windows PowerShell setup

Open PowerShell in the project folder:

```powershell
cd "C:\Users\Veera\Documents\AIPIA\Project PaperTrial"
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Configure the API key

Create a file named `.env` in the project folder and add your Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Do not commit `.env` or share the API key.

## Start the application

Run the FastAPI server with Uvicorn:

```powershell
python -m uvicorn app:app --reload
```

The `--reload` option automatically restarts the server when Python files change.

Open this address in a browser:

<http://127.0.0.1:8000>

## Use the application

1. Upload one or more text-based PDF files.
2. Wait for the documents to finish processing.
3. Ask a question about the uploaded documents.
4. Review the answer and its file/page citations.

Scanned PDFs require OCR and are not supported by the current version.

## Stop the application

Return to the PowerShell window running the server and press `Ctrl+C`.

## Troubleshooting

- **Missing API key:** Check that `.env` exists in the same folder as `app.py` and contains `GEMINI_API_KEY`.
- **Port already in use:** Start on another port with `python -m uvicorn app:app --reload --port 8001`, then open `http://127.0.0.1:8001`.
- **Dependency errors:** Activate `.venv` and run `python -m pip install -r requirements.txt` again.
- **Local document storage:** ChromaDB stores local data in the `chroma_data` folder.