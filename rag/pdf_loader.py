import re
import fitz


class PDFProblem(ValueError):
    pass


def extract_pages(data: bytes) -> list[tuple[int, str]]:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise PDFProblem("This file is not a readable PDF.") from exc
    try:
        if doc.needs_pass:
            raise PDFProblem("Password-protected PDFs are not supported.")
        if len(doc) > 400:
            raise PDFProblem("This PDF exceeds the 400-page limit.")
        pages = []
        for number, page in enumerate(doc, 1):
            text = page.get_text("text", sort=True)
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            if len(text) >= 40:
                pages.append((number, text))
        if sum(len(text) for _, text in pages) < 100:
            raise PDFProblem("Little or no selectable text found. This PDF may be scanned and needs OCR.")
        return pages
    finally:
        doc.close()
