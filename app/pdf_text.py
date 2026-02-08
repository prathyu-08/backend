from pypdf import PdfReader

def extract_text_from_pdf(file_obj) -> str:
    reader = PdfReader(file_obj)
    text = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)

    return "\n".join(text).strip()
