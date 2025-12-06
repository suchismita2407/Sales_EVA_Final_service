import os

def extract_text_from_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        return extract_pdf(filepath)
    elif ext in [".doc", ".docx"]:
        return extract_doc(filepath)
    elif ext in [".txt"]:
        return open(filepath, "r", encoding="utf-8").read()
    else:
        return None


def extract_pdf(filepath):
    import pypdf
    reader = pypdf.PdfReader(open(filepath, 'rb'))
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def extract_doc(filepath):
    import docx
    doc = docx.Document(filepath)
    return "\n".join(p.text for p in doc.paragraphs)
