import re


def chunks(pages: list[tuple[int, str]], filename: str, document_id: str):
    """Pack paragraphs within each page; overlap the previous paragraph."""
    for page, text in pages:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        units = []
        for paragraph in paragraphs:
            if len(paragraph) <= 1300:
                units.append(paragraph)
            else:
                sentences = re.split(r"(?<=[.!?])\s+", paragraph)
                current = ""
                for sentence in sentences:
                    if len(current) + len(sentence) > 1100 and current:
                        units.append(current)
                        current = ""
                    while len(sentence) > 1100:
                        units.append(sentence[:1100])
                        sentence = sentence[1100:]
                    current = (current + " " + sentence).strip()
                if current:
                    units.append(current)
        buffer = []
        part = 0
        for unit in units:
            if sum(map(len, buffer)) + len(unit) > 2200 and buffer:
                yield {"id": f"{document_id}:{page}:{part}", "page": page, "filename": filename, "text": "\n\n".join(buffer)}
                part += 1
                buffer = buffer[-1:] if len(buffer[-1]) < 350 else []
            buffer.append(unit)
        if buffer:
            yield {"id": f"{document_id}:{page}:{part}", "page": page, "filename": filename, "text": "\n\n".join(buffer)}
